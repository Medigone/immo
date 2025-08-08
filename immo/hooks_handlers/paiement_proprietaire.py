# Copyright (c) 2024, Frappe Technologies and Contributors
# See license.txt

import frappe
from frappe.utils import nowdate, getdate, add_months


def on_update(doc, method):
	"""Actions après mise à jour du paiement propriétaire"""
	# Met à jour le statut de la mensualité si confirmé
	if doc.statut == "Payé" and doc.type_paiement == "Loyer mensuel":
		update_mensualite_status(doc)
	
	# Traite les paiements de référents pour les locations courte durée
	if doc.statut == "Payé" and doc.location_courte_duree_id:
		process_referent_payment(doc)
	
	# Met à jour les statistiques du propriétaire
	update_proprietaire_statistics(doc)
	
	# Met à jour les statistiques de la location
	update_location_payout_statistics(doc)
	
	# Met à jour les statistiques de l'appartement
	update_apartment_payout_statistics(doc)
	
	# Génère les notifications selon le statut
	notify_payout_status_change(doc)


def on_cancel(doc, method):
	"""Actions lors de l'annulation du paiement"""
	# Remet à jour le statut de la mensualité
	if doc.type_paiement == "Loyer mensuel" and doc.mensualite_id:
		revert_mensualite_status(doc)
	
	# Met à jour les statistiques
	update_proprietaire_statistics(doc)
	update_location_payout_statistics(doc)
	update_apartment_payout_statistics(doc)


def update_mensualite_status(doc):
	"""Met à jour le statut de paiement de la mensualité"""
	if not doc.mensualite_id:
		return
	
	try:
		# Met à jour le statut de paiement propriétaire de la mensualité
		frappe.db.set_value("Mensualite", doc.mensualite_id, {
			"statut_paiement_proprietaire": "Payé",
			"date_paiement_proprietaire": doc.date_paiement,
			"methode_paiement_proprietaire": doc.methode_paiement,
			"reference_paiement_proprietaire": doc.reference_financiere
		})
		
		# Vérifie si la mensualité est complètement payée (locataire + propriétaire)
		mensualite = frappe.get_doc("Mensualite", doc.mensualite_id)
		if (mensualite.statut_paiement_locataire == "Payé" and 
			mensualite.statut_paiement_proprietaire == "Payé"):
			frappe.db.set_value("Mensualite", doc.mensualite_id, "statut_global", "Complète")
			
			# Génère automatiquement la mensualité suivante si configuré
			generate_next_mensualite_if_needed(mensualite)
			
	except Exception as e:
		frappe.log_error(f"Erreur lors de la mise à jour de la mensualité: {str(e)}")


def revert_mensualite_status(doc):
	"""Remet le statut de la mensualité lors de l'annulation"""
	try:
		frappe.db.set_value("Mensualite", doc.mensualite_id, {
			"statut_paiement_proprietaire": "En attente",
			"date_paiement_proprietaire": None,
			"methode_paiement_proprietaire": None,
			"reference_paiement_proprietaire": None,
			"statut_global": "En attente"
		})
		
	except Exception as e:
		frappe.log_error(f"Erreur lors de la remise à jour de la mensualité: {str(e)}")


def generate_next_mensualite_if_needed(mensualite):
	"""Génère la mensualité suivante si nécessaire"""
	try:
		# Récupère la location pour vérifier si elle est toujours active
		location = frappe.get_doc("Location Longue Durée", mensualite.location_longue_duree_id)
		
		if location.statut != "Actif":
			return
		
		# Calcule le mois suivant
		current_date = getdate(f"{mensualite.mois_annee.split('/')[1]}-{mensualite.mois_annee.split('/')[0]}-01")
		next_month_date = add_months(current_date, 1)
		next_mois_annee = f"{next_month_date.month:02d}/{next_month_date.year}"
		
		# Vérifie si la mensualité suivante n'existe pas déjà
		existing_next = frappe.db.exists("Mensualite", {
			"location_longue_duree_id": mensualite.location_longue_duree_id,
			"mois_annee": next_mois_annee
		})
		
		if not existing_next:
			# Vérifie si on n'a pas dépassé la date de fin de location
			if location.date_fin and next_month_date > getdate(location.date_fin):
				return
			
			# Crée la mensualité suivante
			next_mensualite = frappe.get_doc({
				"doctype": "Mensualite",
				"location_longue_duree_id": mensualite.location_longue_duree_id,
				"mois_annee": next_mois_annee,
				"loyer_locataire": mensualite.loyer_locataire,
				"loyer_proprietaire": mensualite.loyer_proprietaire,
				"marge_mensuelle": mensualite.marge_mensuelle,
				"statut_paiement_locataire": "En attente",
				"statut_paiement_proprietaire": "En attente",
				"statut_global": "En attente"
			})
			next_mensualite.insert()
			
	except Exception as e:
		frappe.log_error(f"Erreur lors de la génération de la mensualité suivante: {str(e)}")


def update_proprietaire_statistics(doc):
	"""Met à jour les statistiques du propriétaire"""
	try:
		# Récupère l'ID du propriétaire
		proprietaire_id = None
		
		if doc.mensualite_id:
			mensualite = frappe.get_doc("Mensualite", doc.mensualite_id)
			location = frappe.get_doc("Location Longue Durée", mensualite.location_longue_duree_id)
			appartement = frappe.get_doc("Appartement", location.appartement_id)
			proprietaire_id = appartement.proprietaire_id
		elif doc.location_longue_duree_id:
			location = frappe.get_doc("Location Longue Durée", doc.location_longue_duree_id)
			appartement = frappe.get_doc("Appartement", location.appartement_id)
			proprietaire_id = appartement.proprietaire_id
		elif doc.location_courte_duree_id:
			location = frappe.get_doc("Location Courte Duree", doc.location_courte_duree_id)
			appartement = frappe.get_doc("Appartement", location.appartement_id)
			proprietaire_id = appartement.proprietaire_id
		
		if not proprietaire_id:
			return
		
		# Calcule les statistiques de paiement pour ce propriétaire
		stats = frappe.db.sql("""
			SELECT 
				SUM(pp.montant) as total_verse_annee,
				SUM(pp.montant_net) as total_net_verse_annee,
				SUM(pp.frais_transaction) as total_frais_annee,
				COUNT(pp.name) as nombre_paiements_annee,
				AVG(pp.montant) as montant_moyen_versement,
				COUNT(CASE WHEN pp.statut = 'Payé' THEN 1 END) as paiements_effectues,
				COUNT(CASE WHEN pp.statut = 'En attente' THEN 1 END) as paiements_en_attente
			FROM `tabPaiement Propriétaire` pp
			LEFT JOIN `tabMensualite` m ON pp.mensualite_id = m.name
			LEFT JOIN `tabLocation Longue Durée` lld ON (m.location_longue_duree_id = lld.name OR pp.location_longue_duree_id = lld.name)
			LEFT JOIN `tabLocation Courte Duree` lcd ON pp.location_courte_duree_id = lcd.name
			LEFT JOIN `tabAppartement` a ON (lld.appartement_id = a.name OR lcd.appartement_id = a.name)
			WHERE a.proprietaire_id = %s
				AND YEAR(pp.date_paiement) = YEAR(CURDATE())
		""", (proprietaire_id,), as_dict=True)
		
		if stats:
			stat = stats[0]
			# Met à jour le propriétaire avec les nouvelles statistiques
			frappe.db.set_value("Proprietaire", proprietaire_id, {
				"total_verse_annee": stat.total_verse_annee or 0,
				"total_net_verse_annee": stat.total_net_verse_annee or 0,
				"total_frais_versement_annee": stat.total_frais_annee or 0,
				"nombre_paiements_annee": stat.nombre_paiements_annee or 0,
				"taux_paiement_proprietaire": (stat.paiements_effectues / (stat.paiements_effectues + stat.paiements_en_attente) * 100) if (stat.paiements_effectues + stat.paiements_en_attente) > 0 else 0
			})
			
	except Exception as e:
		frappe.log_error(f"Erreur lors de la mise à jour des statistiques propriétaire: {str(e)}")


def update_location_payout_statistics(doc):
	"""Met à jour les statistiques de versement de la location"""
	location_id = None
	location_type = None
	
	# Détermine l'ID de la location selon le type
	if doc.mensualite_id:
		# Récupère la location via la mensualité
		mensualite = frappe.get_doc("Mensualite", doc.mensualite_id)
		location_id = mensualite.location_longue_duree_id
		location_type = "Location Longue Durée"
	elif doc.location_longue_duree_id:
		location_id = doc.location_longue_duree_id
		location_type = "Location Longue Durée"
	elif doc.location_courte_duree_id:
		location_id = doc.location_courte_duree_id
		location_type = "Location Courte Duree"
	
	if not location_id:
		return
	
	try:
		# Calcule les statistiques de versement pour cette location
		stats = frappe.db.sql("""
			SELECT 
				COUNT(*) as total_versements,
				SUM(montant) as montant_total_verse,
				SUM(montant_net) as montant_net_total_verse,
				SUM(frais_transaction) as frais_totaux_versement,
				COUNT(CASE WHEN statut = 'Payé' THEN 1 END) as versements_effectues,
				COUNT(CASE WHEN statut = 'En attente' THEN 1 END) as versements_en_attente,
				AVG(montant) as montant_moyen_versement
			FROM `tabPaiement Propriétaire`
			WHERE (
				(mensualite_id IN (
					SELECT name FROM `tabMensualite` 
					WHERE location_longue_duree_id = %s
				))
				OR location_longue_duree_id = %s
				OR location_courte_duree_id = %s
			)

		""", (location_id, location_id, location_id), as_dict=True)
		
		if stats:
			stat = stats[0]
			# Met à jour la location avec les nouvelles statistiques
			update_data = {
				"total_paiements_verses": stat.montant_total_verse or 0,
				"total_frais_versement": stat.frais_totaux_versement or 0,
				"nombre_paiements_proprietaire": stat.total_versements or 0,
				"taux_paiement_proprietaire": (stat.versements_effectues / stat.total_versements * 100) if stat.total_versements > 0 else 0
			}
			
			frappe.db.set_value(location_type, location_id, update_data)
			
	except Exception as e:
		frappe.log_error(f"Erreur lors de la mise à jour des statistiques de location: {str(e)}")


def update_apartment_payout_statistics(doc):
	"""Met à jour les statistiques de versement de l'appartement"""
	appartement_id = None
	
	# Récupère l'ID de l'appartement
	if doc.mensualite_id:
		mensualite = frappe.get_doc("Mensualite", doc.mensualite_id)
		location = frappe.get_doc("Location Longue Durée", mensualite.location_longue_duree_id)
		appartement_id = location.appartement_id
	elif doc.location_longue_duree_id:
		location = frappe.get_doc("Location Longue Durée", doc.location_longue_duree_id)
		appartement_id = location.appartement_id
	elif doc.location_courte_duree_id:
		location = frappe.get_doc("Location Courte Duree", doc.location_courte_duree_id)
		appartement_id = location.appartement_id
	
	if not appartement_id:
		return
	
	try:
		# Calcule les statistiques globales de versement pour cet appartement
		stats = frappe.db.sql("""
			SELECT 
				SUM(pp.montant) as total_verse_annee,
				SUM(pp.montant_net) as total_net_verse_annee,
				SUM(pp.frais_transaction) as total_frais_versement_annee,
				COUNT(pp.name) as nombre_versements_annee,
				AVG(pp.montant) as montant_moyen_versement
			FROM `tabPaiement Propriétaire` pp
			LEFT JOIN `tabMensualite` m ON pp.mensualite_id = m.name
			LEFT JOIN `tabLocation Longue Durée` lld ON (m.location_longue_duree_id = lld.name OR pp.location_longue_duree_id = lld.name)
			LEFT JOIN `tabLocation Courte Duree` lcd ON pp.location_courte_duree_id = lcd.name
			WHERE (lld.appartement_id = %s OR lcd.appartement_id = %s)
				AND pp.statut = 'Payé'
				AND YEAR(pp.date_paiement) = YEAR(CURDATE())
		""", (appartement_id, appartement_id), as_dict=True)
		
		if stats:
			stat = stats[0]
			# Met à jour l'appartement avec les nouvelles statistiques
			frappe.db.set_value("Appartement", appartement_id, {
				"total_verse_annee": stat.total_verse_annee or 0,
				"total_net_verse_annee": stat.total_net_verse_annee or 0,
				"total_frais_versement_annee": stat.total_frais_versement_annee or 0,
				"nombre_versements_proprietaire_annee": stat.nombre_versements_annee or 0
			})
			
	except Exception as e:
		frappe.log_error(f"Erreur lors de la mise à jour des statistiques d'appartement: {str(e)}")


def notify_payout_status_change(doc):
	"""Notifie les changements de statut de versement"""
	if doc.has_value_changed("statut"):
		if doc.statut == "Payé":
			notify_payout_completed(doc)
		elif doc.statut == "Rejeté":
			notify_payout_rejected(doc)
		elif doc.statut == "En attente":
			notify_payout_pending(doc)


def notify_payout_completed(doc):
	"""Notifie la completion du versement au propriétaire"""
	try:
		# Récupère les informations du propriétaire
		proprietaire_email = None
		proprietaire_nom = None
		appartement_adresse = None
		
		if doc.mensualite_id:
			mensualite = frappe.get_doc("Mensualite", doc.mensualite_id)
			location = frappe.get_doc("Location Longue Durée", mensualite.location_longue_duree_id)
			appartement = frappe.get_doc("Appartement", location.appartement_id)
			proprietaire = frappe.get_doc("Proprietaire", appartement.proprietaire_id)
			proprietaire_email = proprietaire.email
			proprietaire_nom = proprietaire.nom_complet
			appartement_adresse = appartement.adresse
		
		elif doc.location_longue_duree_id:
			location = frappe.get_doc("Location Longue Durée", doc.location_longue_duree_id)
			appartement = frappe.get_doc("Appartement", location.appartement_id)
			proprietaire = frappe.get_doc("Proprietaire", appartement.proprietaire_id)
			proprietaire_email = proprietaire.email
			proprietaire_nom = proprietaire.nom_complet
			appartement_adresse = appartement.adresse
		
		elif doc.location_courte_duree_id:
			location = frappe.get_doc("Location Courte Duree", doc.location_courte_duree_id)
			appartement = frappe.get_doc("Appartement", location.appartement_id)
			proprietaire = frappe.get_doc("Proprietaire", appartement.proprietaire_id)
			proprietaire_email = proprietaire.email
			proprietaire_nom = proprietaire.nom_complet
			appartement_adresse = appartement.adresse
		
		if proprietaire_email:
			subject = f"Versement effectué - {appartement_adresse}"
			message = f"""
			Bonjour {proprietaire_nom},
			
			Nous vous confirmons que votre versement a été effectué:
			
			- Appartement: {appartement_adresse}
			- Type: {doc.type_paiement}
			- Montant: {doc.montant} €
			- Montant net: {doc.montant_net} €
			- Date de versement: {doc.date_paiement}
			- Méthode: {doc.methode_paiement}
			- Référence: {doc.reference_financiere or 'N/A'}
			
			Le montant devrait apparaître sur votre compte sous 1-3 jours ouvrés.
			
			Cordialement,
			L'équipe de gestion
			"""
			
			# Envoie l'email (à implémenter selon la configuration email)
			# frappe.sendmail(
			#     recipients=[proprietaire_email],
			#     subject=subject,
			#     message=message
			# )
			
	except Exception as e:
		frappe.log_error(f"Erreur lors de l'envoi de confirmation de versement: {str(e)}")


def notify_payout_rejected(doc):
	"""Notifie le rejet du versement"""
	try:
		# Récupère les informations du propriétaire pour notification
		proprietaire_email = None
		proprietaire_nom = None
		
		if doc.mensualite_id:
			mensualite = frappe.get_doc("Mensualite", doc.mensualite_id)
			location = frappe.get_doc("Location Longue Durée", mensualite.location_longue_duree_id)
			appartement = frappe.get_doc("Appartement", location.appartement_id)
			proprietaire = frappe.get_doc("Proprietaire", appartement.proprietaire_id)
			proprietaire_email = proprietaire.email
			proprietaire_nom = proprietaire.nom_complet
		
		elif doc.location_longue_duree_id:
			location = frappe.get_doc("Location Longue Durée", doc.location_longue_duree_id)
			appartement = frappe.get_doc("Appartement", location.appartement_id)
			proprietaire = frappe.get_doc("Proprietaire", appartement.proprietaire_id)
			proprietaire_email = proprietaire.email
			proprietaire_nom = proprietaire.nom_complet
		
		elif doc.location_courte_duree_id:
			location = frappe.get_doc("Location Courte Duree", doc.location_courte_duree_id)
			appartement = frappe.get_doc("Appartement", location.appartement_id)
			proprietaire = frappe.get_doc("Proprietaire", appartement.proprietaire_id)
			proprietaire_email = proprietaire.email
			proprietaire_nom = proprietaire.nom_complet
		
		if proprietaire_email:
			subject = f"Versement rejeté - Information importante"
			message = f"""
			Bonjour {proprietaire_nom},
			
			Nous vous informons que votre versement a été rejeté:
			
			- Type: {doc.type_paiement}
			- Montant: {doc.montant} €
			- Date prévue: {doc.date_paiement}
			- Référence: {doc.reference_financiere or 'N/A'}
			
			Raison: {doc.commentaires or 'Non spécifiée'}
			
			Nous vous contacterons pour résoudre ce problème dans les plus brefs délais.
			
			Cordialement,
			L'équipe de gestion
			"""
			
			# Envoie l'email (à implémenter selon la configuration email)
			# frappe.sendmail(
			#     recipients=[proprietaire_email],
			#     subject=subject,
			#     message=message
			# )
			
	except Exception as e:
		frappe.log_error(f"Erreur lors de l'envoi de notification de rejet: {str(e)}")


def notify_payout_pending(doc):
	"""Notifie la mise en attente du versement"""
	try:
		# Récupère les informations du propriétaire
		proprietaire_email = None
		proprietaire_nom = None
		
		if doc.mensualite_id:
			mensualite = frappe.get_doc("Mensualite", doc.mensualite_id)
			location = frappe.get_doc("Location Longue Durée", mensualite.location_longue_duree_id)
			appartement = frappe.get_doc("Appartement", location.appartement_id)
			proprietaire = frappe.get_doc("Proprietaire", appartement.proprietaire_id)
			proprietaire_email = proprietaire.email
			proprietaire_nom = proprietaire.nom_complet
		
		if proprietaire_email:
			subject = f"Versement en attente - {doc.type_paiement}"
			message = f"""
			Bonjour {proprietaire_nom},
			
			Votre versement est en cours de traitement:
			
			- Type: {doc.type_paiement}
			- Montant: {doc.montant} €
			- Date prévue: {doc.date_paiement}
			
			Nous vous tiendrons informé de l'évolution du traitement.
			
			Cordialement,
			L'équipe de gestion
			"""
			
			# Envoie l'email (à implémenter selon la configuration email)
			# frappe.sendmail(
			#     recipients=[proprietaire_email],
			#     subject=subject,
			#     message=message
			# )
			
	except Exception as e:
		frappe.log_error(f"Erreur lors de l'envoi de notification d'attente: {str(e)}")


def auto_schedule_payouts():
	"""Programme automatiquement les versements pour les mensualités payées"""
	try:
		# Recherche les mensualités avec paiement locataire confirmé mais sans versement propriétaire
		pending_payouts = frappe.db.sql("""
			SELECT 
				m.name as mensualite_id,
				m.location_longue_duree_id,
				m.loyer_proprietaire,
				m.date_paiement_locataire,
				lld.appartement_id,
				a.proprietaire_id
			FROM `tabMensualite` m
			INNER JOIN `tabLocation Longue Durée` lld ON m.location_longue_duree_id = lld.name
			INNER JOIN `tabAppartement` a ON lld.appartement_id = a.name
			WHERE m.statut_paiement_locataire = 'Payé'
				AND m.statut_paiement_proprietaire = 'En attente'
				AND NOT EXISTS (
					SELECT 1 FROM `tabPaiement Propriétaire` pp 
					WHERE pp.mensualite_id = m.name
				)
		""", as_dict=True)
		
		for payout in pending_payouts:
			# Crée automatiquement un versement propriétaire
			payout_doc = frappe.get_doc({
				"doctype": "Paiement Propriétaire",
				"mensualite_id": payout.mensualite_id,
				"location_longue_duree_id": payout.location_longue_duree_id,
				"type_paiement": "Loyer mensuel",
				"montant": payout.loyer_proprietaire,
				"montant_net": payout.loyer_proprietaire,  # À ajuster selon les frais
				"date_paiement": add_months(getdate(payout.date_paiement_locataire), 0),  # Même mois
				"statut": "En attente",
				"methode_paiement": "Virement bancaire",  # Par défaut
				"commentaires": "Versement automatiquement programmé"
			})
			payout_doc.insert()
			
	except Exception as e:
		frappe.log_error(f"Erreur lors de la programmation automatique des versements: {str(e)}")


def calculate_owner_performance_metrics(proprietaire_id, start_date=None, end_date=None):
	"""Calcule les métriques de performance pour un propriétaire"""
	try:
		if not start_date:
			start_date = f"{getdate().year}-01-01"
		if not end_date:
			end_date = nowdate()
		
		metrics = frappe.db.sql("""
			SELECT 
				COUNT(DISTINCT a.name) as nombre_appartements,
				COUNT(DISTINCT lld.name) as nombre_locations_longues,
				COUNT(DISTINCT lcd.name) as nombre_locations_courtes,
				SUM(pp.montant) as total_verse,
				SUM(pp.montant_net) as total_net_verse,
				AVG(pp.montant) as montant_moyen_versement,
				COUNT(pp.name) as nombre_versements,
				SUM(CASE WHEN pp.statut = 'Payé' THEN pp.montant ELSE 0 END) as montant_paye,
				COUNT(CASE WHEN pp.statut = 'Payé' THEN 1 END) as versements_payes,
				COUNT(CASE WHEN pp.statut = 'En attente' THEN 1 END) as versements_en_attente,
				COUNT(CASE WHEN pp.statut = 'Rejeté' THEN 1 END) as versements_rejetes
			FROM `tabProprietaire` p
			LEFT JOIN `tabAppartement` a ON p.name = a.proprietaire_id
			LEFT JOIN `tabLocation Longue Durée` lld ON a.name = lld.appartement_id
			LEFT JOIN `tabLocation Courte Duree` lcd ON a.name = lcd.appartement_id
			LEFT JOIN `tabMensualite` m ON lld.name = m.location_longue_duree_id
			LEFT JOIN `tabPaiement Propriétaire` pp ON (m.name = pp.mensualite_id OR lld.name = pp.location_longue_duree_id OR lcd.name = pp.location_courte_duree_id)
			WHERE p.name = %s
				AND (pp.date_paiement IS NULL OR pp.date_paiement BETWEEN %s AND %s)
			GROUP BY p.name
		""", (proprietaire_id, start_date, end_date), as_dict=True)
		
		if metrics:
			metric = metrics[0]
			metric['taux_paiement'] = (metric.versements_payes / metric.nombre_versements * 100) if metric.nombre_versements > 0 else 0
			metric['taux_rejet'] = (metric.versements_rejetes / metric.nombre_versements * 100) if metric.nombre_versements > 0 else 0
			return metric
		
		return {}
	
	except Exception as e:
		frappe.log_error(f"Erreur lors du calcul des métriques propriétaire: {str(e)}")
		return {}


def process_referent_payment(doc):
	"""Traite automatiquement le paiement du référent pour une location courte durée"""
	if not doc.location_courte_duree_id:
		return
	
	try:
		# Récupère la location courte durée
		location = frappe.get_doc("Location Courte Duree", doc.location_courte_duree_id)
		
		# Vérifie s'il y a un référent
		if not location.referent_id:
			return
		
		# Vérifie s'il existe déjà une commission pour cette location
		existing_commission = frappe.db.exists("Commission", {
			"location_courte_duree_id": doc.location_courte_duree_id,
			"referent_id": location.referent_id
		})
		
		if existing_commission:
			# Met à jour le statut de paiement de la commission existante
			frappe.db.set_value("Commission", existing_commission, {
				"statut_paiement": "Payé",
				"date_paiement": doc.date_paiement,
				"methode_paiement": doc.methode_paiement,
				"reference_paiement": doc.reference_financiere
			})
			frappe.msgprint(f"Commission mise à jour pour le référent {location.referent_id}")
		else:
			# Calcule la commission du référent
			commission_amount = location.calculate_referent_commission()
			
			if commission_amount > 0:
				# Crée un nouveau document Commission
				commission = frappe.get_doc({
					"doctype": "Commission",
					"referent_id": location.referent_id,
					"location_courte_duree_id": doc.location_courte_duree_id,
					"montant_commission": commission_amount,
					"pourcentage_commission": location.pourcentage_commission_referent or 0,
					"date_creation": nowdate(),
					"statut_paiement": "Payé",
					"date_paiement": doc.date_paiement,
					"methode_paiement": doc.methode_paiement,
					"reference_paiement": doc.reference_financiere,
					"commentaires": f"Paiement automatique suite au versement propriétaire {doc.name}"
				})
				commission.insert()
				commission.submit()
				
				frappe.msgprint(f"Commission de {commission_amount} € créée et payée pour le référent {location.referent_id}")
		
	except Exception as e:
		frappe.log_error(f"Erreur lors du traitement du paiement référent: {str(e)}", "Process Referent Payment Error")
		frappe.msgprint(f"Erreur lors du traitement du paiement référent: {str(e)}", indicator="red")