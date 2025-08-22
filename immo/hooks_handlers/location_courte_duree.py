# Copyright (c) 2024, Frappe Technologies and Contributors
# See license.txt

import frappe
from frappe.utils import nowdate, getdate, date_diff
from datetime import timedelta


def on_update(doc, method):
	"""Actions après mise à jour de la location courte durée"""
	try:
		# Éviter les mises à jour inutiles si le document est en cours de mise à jour automatique
		if getattr(doc, '_updating_payments', False):
			return
		
		# Éviter les mises à jour si le document est en cours de suppression
		if getattr(doc, '_in_delete', False):
			return
		
		# Vérifier si les champs critiques ont changé pour éviter les mises à jour inutiles
		critical_fields = ['montant_total_locataire', 'montant_total_proprietaire', 'date_debut', 'date_fin', 'location_bloc_id']
		has_critical_changes = any(doc.has_value_changed(field) for field in critical_fields)
		
		if has_critical_changes:
			# Mettre à jour le statut des paiements seulement si nécessaire
			doc.calculate_payment_status()
			
			# Mettre à jour les métriques de la location bloc si applicable
			if doc.location_bloc_id:
				doc.update_location_bloc_metrics()
				# Déclencher immédiatement la mise à jour en temps réel
				update_location_bloc_metrics_after_update(doc)
			
	except Exception as e:
		frappe.log_error(f"Erreur dans on_update Location Courte Duree {doc.name}: {str(e)}")


def on_trash(doc, method):
	"""Actions lors de la suppression de la location courte durée"""
	try:
		# Stocker l'ID de la location bloc pour la mise à jour après suppression
		if doc.location_bloc_id:
			# Calculer le nouveau taux d'occupation AVANT la suppression
			location_bloc = frappe.get_doc("Location Bloc", doc.location_bloc_id)
			
			# Calculer manuellement le nouveau taux d'occupation en excluant cette location (basé sur les nuitées)
			if location_bloc.date_debut_bloc and location_bloc.date_fin_bloc:
				# Calculer le nombre total de nuits du bloc
				total_nuits = date_diff(location_bloc.date_fin_bloc, location_bloc.date_debut_bloc)
				if total_nuits <= 0:
					nouveau_taux_occupation = 0
				else:
					# Récupérer toutes les autres sous-locations avec leur nombre de nuits (exclure celle qui va être supprimée)
					autres_sous_locations = frappe.get_all(
						"Location Courte Duree",
						filters={"location_bloc_id": doc.location_bloc_id, "name": ["!=", doc.name]},
						fields=["name", "nombre_nuits"]
					)
					
					# Calculer le total des nuits occupées par les autres locations
					nuits_occupees = sum(sl.nombre_nuits or 0 for sl in autres_sous_locations)
					
					# Calculer le nouveau taux d'occupation basé sur les nuitées
					nouveau_taux_occupation = (nuits_occupees / total_nuits * 100) if total_nuits > 0 else 0
				
				# Stocker temporairement le nouveau taux d'occupation
				frappe.local.nouveau_taux_occupation = nouveau_taux_occupation
				frappe.local.location_bloc_to_update = doc.location_bloc_id
			
	except Exception as e:
		frappe.log_error(f"Erreur dans on_trash Location Courte Duree {doc.name}: {str(e)}")


def after_delete(doc, method):
	"""Actions après suppression effective de la location courte durée"""
	try:
		# Mettre à jour les métriques de la location bloc après suppression effective
		if hasattr(frappe.local, 'location_bloc_to_update') and frappe.local.location_bloc_to_update:
			location_bloc_id = frappe.local.location_bloc_to_update
			
			# Utiliser le nouveau taux d'occupation calculé dans on_trash
			if hasattr(frappe.local, 'nouveau_taux_occupation'):
				nouveau_taux_occupation = frappe.local.nouveau_taux_occupation
				
				# Mettre à jour toutes les métriques en une seule fois
				update_location_bloc_metrics_after_deletion_effective_with_custom_occupation(location_bloc_id, nouveau_taux_occupation)
				
				# Nettoyer les variables locales
				del frappe.local.nouveau_taux_occupation
			else:
				# Si pas de taux pré-calculé, utiliser 0 comme valeur par défaut
				update_location_bloc_metrics_after_deletion_effective_with_custom_occupation(location_bloc_id, 0)
			
			# Nettoyer la variable locale
			del frappe.local.location_bloc_to_update
			
	except Exception as e:
		frappe.log_error(f"Erreur dans after_delete Location Courte Duree: {str(e)}")


def validate(doc, method):
	"""Validation de la location courte durée"""
	try:
		# Les validations sont déjà gérées dans la classe Document
		pass
		
	except Exception as e:
		frappe.log_error(f"Erreur dans validate Location Courte Duree {doc.name}: {str(e)}")


def after_insert(doc, method):
	"""Actions après création de la location courte durée"""
	try:
		# Initialiser le statut des paiements
		doc.calculate_payment_status()
		
		# Sauvegarder les changements de statut de paiement
		doc.save(ignore_permissions=True)
		
		# Mettre à jour les métriques de la location bloc si applicable
		if doc.location_bloc_id:
			doc.update_location_bloc_metrics()
			
	except Exception as e:
		frappe.log_error(f"Erreur dans after_insert Location Courte Duree {doc.name}: {str(e)}")





def check_date_overlap(doc):
	"""Vérifie les chevauchements de dates pour le même appartement"""
	if not doc.date_debut or not doc.date_fin:
		return
	
	# Recherche les réservations existantes qui se chevauchent
	# Modifié pour permettre qu'une date de fin soit égale à une date de début
	overlapping_bookings = frappe.db.sql("""
		SELECT name, date_debut, date_fin, locataire_nom
		FROM `tabLocation Courte Duree`
		WHERE appartement_id = %s
			AND name != %s
			AND (
				(date_debut < %s AND date_fin > %s)
				OR (date_debut < %s AND date_fin > %s)
				OR (date_debut > %s AND date_fin < %s)
			)
	""", (doc.appartement_id, doc.name or '', doc.date_fin, doc.date_debut,
		  doc.date_fin, doc.date_debut, doc.date_debut, doc.date_fin), as_dict=True)
	
	if overlapping_bookings:
		overlap_details = []
		for booking in overlapping_bookings:
			overlap_details.append(f"{booking.locataire_nom} ({booking.date_debut} - {booking.date_fin})")
		
		frappe.throw(
			f"Conflit de dates détecté. Les périodes se chevauchent avec les réservations existantes: {', '.join(overlap_details)}",
			title="Chevauchement de dates"
		)
	
	# Vérifie aussi les conflits avec les locations longue durée
	# Modifié pour permettre qu'une date de fin soit égale à une date de début
	overlapping_long_term = frappe.db.sql("""
		SELECT name, date_debut, date_fin, locataire_nom
		FROM `tabLocation Longue Duree`
		WHERE appartement_id = %s
			AND (
				(date_debut < %s AND date_fin > %s)
				OR (date_debut < %s AND date_fin > %s)
				OR (date_debut > %s AND date_fin < %s)
			)
	""", (doc.appartement_id, doc.date_fin, doc.date_debut,
		  doc.date_fin, doc.date_debut, doc.date_debut, doc.date_fin), as_dict=True)
	
	if overlapping_long_term:
		frappe.throw(
			f"Conflit avec une location longue durée active pour cet appartement",
			title="Appartement non disponible"
		)


def calculate_amounts_and_margins(doc):
	"""Calcule automatiquement les montants et marges"""
	if not doc.date_debut or not doc.date_fin or not doc.prix_journalier_locataire:
		return
	
	# Calcule le nombre de nuits
	nights = date_diff(doc.date_fin, doc.date_debut)
	if nights <= 0:
		frappe.throw("La date de fin doit être postérieure à la date de début")
	
	doc.nombre_nuits = nights
	
	# Calcule le montant total locataire
	doc.montant_total_locataire = doc.prix_journalier_locataire * nights
	
	# Récupère le prix propriétaire par défaut si pas défini
	if not doc.prix_journalier_proprietaire:
		# Récupère le prix par défaut de l'appartement
		appartement = frappe.get_doc("Appartement", doc.appartement_id)
		
		if appartement.prix_journalier_defaut:
			doc.prix_journalier_proprietaire = appartement.prix_journalier_defaut
		else:
			# Par défaut, 80% du prix locataire
			doc.prix_journalier_proprietaire = doc.prix_journalier_locataire * 0.8
	
	# Calcule le montant total propriétaire
	doc.montant_total_proprietaire = doc.prix_journalier_proprietaire * nights
	
	# Calcule la marge
	doc.marge_totale = doc.montant_total_locataire - doc.montant_total_proprietaire


def validate_amounts(doc):
	"""Valide les montants"""
	if doc.prix_journalier_locataire and doc.prix_journalier_locataire <= 0:
		frappe.throw("Le prix journalier locataire doit être positif")
	
	if doc.prix_journalier_proprietaire and doc.prix_journalier_proprietaire <= 0:
		frappe.throw("Le prix journalier propriétaire doit être positif")
	
	if (doc.prix_journalier_locataire and doc.prix_journalier_proprietaire and 
		doc.prix_journalier_locataire < doc.prix_journalier_proprietaire):
		frappe.throw("Le prix locataire ne peut pas être inférieur au prix propriétaire")


def validate_dates(doc):
	"""Valide les dates"""
	if doc.date_debut and doc.date_fin:
		if getdate(doc.date_debut) >= getdate(doc.date_fin):
			frappe.throw("La date de fin doit être postérieure à la date de début")
	
	# Vérifie que les dates ne sont pas trop dans le passé
	if doc.date_debut:
		if getdate(doc.date_debut) < getdate(nowdate()):
			frappe.msgprint(
				"Attention: La date de début est dans le passé",
				title="Date dans le passé",
				indicator="orange"
			)





def update_related_commissions(doc):
	"""Met à jour les commissions associées"""
	# Recherche les commissions liées à cette location
	commissions = frappe.get_all("Commission", {
		"location_courte_duree_id": doc.name
	})
	
	for commission in commissions:
		comm_doc = frappe.get_doc("Commission", commission.name)
		# Recalcule le montant de la commission basé sur la nouvelle marge
		if comm_doc.pourcentage_commission and doc.marge_totale:
			new_amount = (doc.marge_totale * comm_doc.pourcentage_commission) / 100
			# Utilise frappe.db.set_value pour éviter les hooks récursifs
			frappe.db.set_value("Commission", commission.name, "montant_commission", new_amount)
			frappe.db.commit()


def on_trash_old(doc, method):
	"""Actions lors de la suppression définitive - DÉSACTIVÉE car elle écrase le taux d'occupation"""
	# Supprimer les commissions associées
	commissions = frappe.get_all("Commission", {
		"location_courte_duree_id": doc.name
	})
	
	for commission in commissions:
		try:
			frappe.delete_doc("Commission", commission.name, force=True)
		except Exception as e:
			frappe.log_error(f"Erreur suppression commission {commission.name}: {str(e)}")
	
	# Supprimer les paiements locataires associés
	paiements = frappe.get_all("Paiement Locataire", {
		"location_courte_duree_id": doc.name
	})
	
	for paiement in paiements:
		try:
			frappe.delete_doc("Paiement Locataire", paiement.name, force=True)
		except Exception as e:
			frappe.log_error(f"Erreur suppression paiement {paiement.name}: {str(e)}")
	
	# COMMENTÉ: Cette partie écrasait le taux d'occupation calculé dans la première fonction on_trash
	# if doc.location_bloc_id:
	#	update_location_bloc_metrics_after_deletion(doc)
	#	
	#	# Publier l'événement en temps réel pour mettre à jour le calendrier
	#	frappe.publish_realtime(
	#		'location_bloc_updated',
	#		{
	#			'location_bloc_id': doc.location_bloc_id,
	#			'action': 'location_deleted',
	#			'location_courte_duree_id': doc.name,
	#			'date_debut': str(doc.date_debut),
	#			'date_fin': str(doc.date_fin),
	#			'locataire_nom': doc.locataire_nom
	#		}
	#	)
	
	# Log de la suppression pour audit
	frappe.log_error(
		f"LCD {doc.name} supprimée - {doc.locataire_nom} ({doc.date_debut} - {doc.date_fin})",
		"LCD Suppression"
	)








def calculate_dynamic_pricing(doc):
	"""Calcule le prix dynamique basé sur les règles de tarification"""
	# Cette fonction peut être étendue pour implémenter des règles de pricing dynamique
	# basées sur la saison, la demande, les événements locaux, etc.
	
	# Pour l'instant, applique les règles de base
	if not doc.prix_journalier_locataire and doc.appartement_id:
		# Récupère le prix de base de l'appartement ou du propriétaire
		appartement = frappe.get_doc("Appartement", doc.appartement_id)
		proprietaire = frappe.get_doc("Proprietaire", appartement.proprietaire_id)
		
		base_price = proprietaire.prix_journalier_defaut or 50  # Prix par défaut
		
		# Applique des ajustements saisonniers (exemple simple)
		if doc.date_debut:
			start_date = getdate(doc.date_debut)
			# Haute saison (juillet-août)
			if start_date.month in [7, 8]:
				base_price *= 1.3
			# Moyenne saison (mai-juin, septembre)
			elif start_date.month in [5, 6, 9]:
				base_price *= 1.1
		
		doc.prix_journalier_locataire = base_price


def create_paiement_locataire_for_confirmed_location(doc):
	"""Crée automatiquement un paiement locataire pour une location courte durée"""
	# Vérifie si un paiement existe déjà pour cette location
	existing_payment = frappe.db.exists("Paiement Locataire", {
		"location_courte_duree_id": doc.name
	})
	
	if existing_payment:
		return
	
	# Vérifie que les montants sont définis
	if not doc.montant_total_locataire or doc.montant_total_locataire <= 0:
		return
	
	try:
		# Crée le paiement locataire
		paiement = frappe.new_doc("Paiement Locataire")
		paiement.location_courte_duree_id = doc.name
		
		# Ajoute location_bloc_id seulement si elle existe
		if doc.location_bloc_id:
			paiement.location_bloc_id = doc.location_bloc_id
		
		paiement.montant = doc.montant_total_locataire
		paiement.date_paiement = doc.date_debut
		paiement.type_paiement = "Autre"
		paiement.methode_paiement = "Virement"
		paiement.statut = "Nouveau"
		paiement.commentaires = f"Paiement automatique pour LCD {doc.name}"
		paiement.insert()
		
		frappe.msgprint(
			f"Paiement locataire créé automatiquement: {paiement.name} ({paiement.montant} EUR)",
			title="Paiement créé",
			indicator="green"
		)
		
	except Exception as e:
		frappe.log_error(f"Erreur paiement auto LCD {doc.name}: {str(e)[:100]}")
		frappe.msgprint(
			f"Erreur lors de la création du paiement automatique: {str(e)}",
			title="Erreur",
			indicator="red"
		)


def create_commission_for_location(doc):
	"""Crée la commission pour le référent"""
	# Vérifie si la commission n'existe pas déjà
	existing_commission = frappe.get_all("Commission",
		filters={"location_courte_duree_id": doc.name})
	
	if not existing_commission:
		referent = frappe.get_doc("Referent", doc.referent_id)
		
		# Vérification que le référent a un pourcentage de commission défini
		if not referent.pourcentage_commission_defaut:
			frappe.throw(f"Le référent {referent.nom_complet} n'a pas de pourcentage de commission défini")
		
		commission = frappe.get_doc({
			"doctype": "Commission",
			"location_courte_duree_id": doc.name,
			"referent_id": doc.referent_id,
			"montant_commission": doc.commission_referent,
			"pourcentage_commission": referent.pourcentage_commission_defaut,
			"statut_paiement": "En attente",
			"date_creation": doc.date_fin
		})
		commission.insert()
		frappe.msgprint(f"Commission créée pour le référent {referent.nom_complet}")


def update_location_bloc_metrics_after_update(doc):
	"""Met à jour les métriques de la location bloc après mise à jour d'une location courte durée"""
	try:
		location_bloc = frappe.get_doc("Location Bloc", doc.location_bloc_id)
		location_bloc.update_metrics()
		# Utilise frappe.db.set_value pour éviter les conflits de timestamp
		frappe.db.set_value("Location Bloc", doc.location_bloc_id, {
			"paiements_prevus": location_bloc.paiements_prevus,
			"total_encaisse": location_bloc.total_encaisse,
			"paiements_totaux": location_bloc.paiements_totaux,
			"marge_totale": location_bloc.marge_totale,
			"rentabilite_pourcentage": location_bloc.rentabilite_pourcentage,
			"taux_occupation": location_bloc.taux_occupation
		})
		frappe.db.commit()
		
		# Déclencher une mise à jour en temps réel pour le dashboard
		frappe.publish_realtime(
			'location_bloc_updated',
			{
				'location_bloc_id': doc.location_bloc_id,
				'action': 'location_updated',
				'taux_occupation': location_bloc.taux_occupation,
				'rentabilite_pourcentage': location_bloc.rentabilite_pourcentage
			}
		)
		
	except Exception as e:
		frappe.log_error(f"Erreur MAJ métriques après mise à jour {doc.location_bloc_id}: {str(e)}", "LCD Metrics Update Error")


def update_location_bloc_metrics_after_deletion(doc):
	"""Met à jour les métriques de la location bloc après suppression d'une location courte durée"""
	try:
		location_bloc = frappe.get_doc("Location Bloc", doc.location_bloc_id)
		location_bloc.update_metrics()
		# Utilise frappe.db.set_value pour éviter les conflits de timestamp
		frappe.db.set_value("Location Bloc", doc.location_bloc_id, {
			"paiements_prevus": location_bloc.paiements_prevus,
			"total_encaisse": location_bloc.total_encaisse,
			"paiements_totaux": location_bloc.paiements_totaux,
			"marge_totale": location_bloc.marge_totale,
			"rentabilite_pourcentage": location_bloc.rentabilite_pourcentage,
			"taux_occupation": location_bloc.taux_occupation
		})
		frappe.db.commit()
		
		# Déclencher une mise à jour en temps réel pour le dashboard
		frappe.publish_realtime(
			'location_bloc_updated',
			{
				'location_bloc_id': doc.location_bloc_id,
				'action': 'location_deleted',
				'taux_occupation': location_bloc.taux_occupation,
				'rentabilite_pourcentage': location_bloc.rentabilite_pourcentage
			}
		)
		
	except Exception as e:
		frappe.log_error(f"Erreur MAJ métriques après suppression {doc.location_bloc_id}: {str(e)}", "LCD Metrics Delete Error")


def update_location_bloc_metrics_after_deletion_effective(location_bloc_id):
	"""Met à jour les métriques de la location bloc après suppression effective d'une location courte durée"""
	try:
		location_bloc = frappe.get_doc("Location Bloc", location_bloc_id)
		location_bloc.update_metrics()
		# Utilise frappe.db.set_value pour éviter les conflits de timestamp
		frappe.db.set_value("Location Bloc", location_bloc_id, {
			"paiements_prevus": location_bloc.paiements_prevus,
			"total_encaisse": location_bloc.total_encaisse,
			"paiements_totaux": location_bloc.paiements_totaux,
			"marge_totale": location_bloc.marge_totale,
			"rentabilite_pourcentage": location_bloc.rentabilite_pourcentage,
			"taux_occupation": location_bloc.taux_occupation
		})
		frappe.db.commit()
		
		# Déclencher une mise à jour en temps réel pour le dashboard
		frappe.publish_realtime(
			'location_bloc_updated',
			{
				'location_bloc_id': location_bloc_id,
				'action': 'location_deleted',
				'taux_occupation': location_bloc.taux_occupation,
				'rentabilite_pourcentage': location_bloc.rentabilite_pourcentage
			}
		)
		
	except Exception as e:
		frappe.log_error(f"Erreur MAJ métriques après suppression effective {location_bloc_id}: {str(e)}", "LCD Metrics Delete Effective Error")


def update_location_bloc_metrics_after_deletion_effective_without_occupation(location_bloc_id):
	"""Met à jour les métriques de la location bloc après suppression effective d'une location courte durée sans écraser le taux d'occupation"""
	try:
		location_bloc = frappe.get_doc("Location Bloc", location_bloc_id)
		
		# Mettre à jour seulement les métriques financières sans recalculer le taux d'occupation
		# Calculer le total encaissé (montant des locations)
		total_encaisse = frappe.db.sql("""
			SELECT COALESCE(SUM(montant_total_locataire), 0)
			FROM `tabLocation Courte Duree`
			WHERE location_bloc_id = %s
		""", (location_bloc_id,))[0][0] or 0
		
		# Calculer les paiements prévus (montant total des locations courte durée)
		paiements_prevus = frappe.db.sql("""
			SELECT COALESCE(SUM(montant_total_locataire), 0)
			FROM `tabLocation Courte Duree`
			WHERE location_bloc_id = %s
		""", (location_bloc_id,))[0][0] or 0
		
		# Calculer les paiements totaux (somme des paiements locataires)
		paiements_totaux = frappe.db.sql("""
			SELECT COALESCE(SUM(montant), 0)
			FROM `tabPaiement Locataire`
			WHERE location_bloc_id = %s
		""", (location_bloc_id,))[0][0] or 0
		
		# Calculer la marge totale basée sur les paiements réels
		marge_totale = 0
		rentabilite_pourcentage = 0
		if location_bloc.montant_total_proprietaire:
			marge_totale = frappe.utils.flt(paiements_totaux) - frappe.utils.flt(location_bloc.montant_total_proprietaire)
			
			# Calculer la rentabilité en pourcentage basée sur les paiements réels
			if frappe.utils.flt(location_bloc.montant_total_proprietaire) > 0:
				rentabilite_pourcentage = (frappe.utils.flt(marge_totale) / frappe.utils.flt(location_bloc.montant_total_proprietaire)) * 100
		
		# Utilise frappe.db.set_value pour éviter les conflits de timestamp
		frappe.db.set_value("Location Bloc", location_bloc_id, {
			"paiements_prevus": frappe.utils.flt(paiements_prevus),
			"total_encaisse": frappe.utils.flt(total_encaisse),
			"paiements_totaux": frappe.utils.flt(paiements_totaux),
			"marge_totale": frappe.utils.flt(marge_totale),
			"rentabilite_pourcentage": frappe.utils.flt(rentabilite_pourcentage)
		})
		frappe.db.commit()
		
		# Déclencher une mise à jour en temps réel pour le dashboard
		frappe.publish_realtime(
			'location_bloc_updated',
			{
				'location_bloc_id': location_bloc_id,
				'action': 'location_deleted',
				'rentabilite_pourcentage': rentabilite_pourcentage
			}
		)
		
	except Exception as e:
		frappe.log_error(f"Erreur MAJ métriques après suppression effective sans occupation {location_bloc_id}: {str(e)}", "LCD Metrics Delete Effective Error")


def update_location_bloc_metrics_after_deletion_effective_with_custom_occupation(location_bloc_id, taux_occupation_custom):
	"""Met à jour les métriques de la location bloc après suppression effective d'une location courte durée avec un taux d'occupation personnalisé"""
	try:
		location_bloc = frappe.get_doc("Location Bloc", location_bloc_id)
		
		# Calculer le total encaissé (montant des locations)
		total_encaisse = frappe.db.sql("""
			SELECT COALESCE(SUM(montant_total_locataire), 0)
			FROM `tabLocation Courte Duree`
			WHERE location_bloc_id = %s
		""", (location_bloc_id,))[0][0] or 0
		
		# Calculer les paiements prévus (montant total des locations courte durée)
		paiements_prevus = frappe.db.sql("""
			SELECT COALESCE(SUM(montant_total_locataire), 0)
			FROM `tabLocation Courte Duree`
			WHERE location_bloc_id = %s
		""", (location_bloc_id,))[0][0] or 0
		
		# Calculer les paiements totaux (somme des paiements locataires)
		paiements_totaux = frappe.db.sql("""
			SELECT COALESCE(SUM(montant), 0)
			FROM `tabPaiement Locataire`
			WHERE location_bloc_id = %s
		""", (location_bloc_id,))[0][0] or 0
		
		# Calculer la marge totale basée sur les paiements réels
		marge_totale = 0
		rentabilite_pourcentage = 0
		if location_bloc.montant_total_proprietaire:
			marge_totale = frappe.utils.flt(paiements_totaux) - frappe.utils.flt(location_bloc.montant_total_proprietaire)
			
			# Calculer la rentabilité en pourcentage basée sur les paiements réels
			if frappe.utils.flt(location_bloc.montant_total_proprietaire) > 0:
				rentabilite_pourcentage = (frappe.utils.flt(marge_totale) / frappe.utils.flt(location_bloc.montant_total_proprietaire)) * 100
		
		# Mettre à jour TOUTES les métriques en une seule fois, y compris le taux d'occupation personnalisé
		frappe.db.set_value("Location Bloc", location_bloc_id, {
			"paiements_prevus": frappe.utils.flt(paiements_prevus),
			"total_encaisse": frappe.utils.flt(total_encaisse),
			"paiements_totaux": frappe.utils.flt(paiements_totaux),
			"marge_totale": frappe.utils.flt(marge_totale),
			"rentabilite_pourcentage": frappe.utils.flt(rentabilite_pourcentage),
			"taux_occupation": frappe.utils.flt(taux_occupation_custom)
		})
		frappe.db.commit()
		
		# Log pour debug
		frappe.log_error(f"Toutes métriques mises à jour pour Location Bloc {location_bloc_id}, taux occupation: {taux_occupation_custom}%", "Debug Metrics Update")
		
		# Déclencher une mise à jour en temps réel pour le dashboard
		frappe.publish_realtime(
			'location_bloc_updated',
			{
				'location_bloc_id': location_bloc_id,
				'action': 'location_deleted',
				'taux_occupation': taux_occupation_custom,
				'rentabilite_pourcentage': rentabilite_pourcentage
			}
		)
		
	except Exception as e:
		frappe.log_error(f"Erreur MAJ métriques avec taux occupation personnalisé {location_bloc_id}: {str(e)}", "LCD Metrics Custom Occupation Error")