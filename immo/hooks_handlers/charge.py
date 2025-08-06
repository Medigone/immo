# Copyright (c) 2024, Frappe Technologies and Contributors
# See license.txt

import frappe
from frappe.utils import nowdate, getdate


def validate(doc, method):
	"""Validation des données avant sauvegarde"""
	# Validation des montants et répartitions
	validate_amounts_and_distribution(doc)
	
	# Validation de la cohérence appartement-location
	validate_apartment_location_consistency(doc)
	
	# Validation des dates
	validate_dates(doc)
	
	# Calcul automatique des montants
	calculate_amounts(doc)


def on_update(doc, method):
	"""Actions après mise à jour"""
	# Met à jour les marges des mensualités si la charge est validée
	if doc.statut == "Validée":
		update_mensualite_margins(doc)
	
	# Met à jour les statistiques de l'appartement
	update_apartment_charges_statistics(doc)
	
	# Notifie les parties concernées selon le statut
	notify_stakeholders(doc)


def on_cancel(doc, method):
	"""Actions lors de l'annulation"""
	# Remet à jour les marges des mensualités
	revert_mensualite_margins(doc)
	
	# Met à jour les statistiques de l'appartement
	update_apartment_charges_statistics(doc)


def validate_amounts_and_distribution(doc):
	"""Valide les montants et la répartition"""
	if doc.montant and doc.montant <= 0:
		frappe.throw("Le montant de la charge doit être positif")
	
	# Validation de la répartition
	if doc.repartition_locataire < 0 or doc.repartition_locataire > 100:
		frappe.throw("La répartition locataire doit être entre 0 et 100%")
	
	if doc.repartition_proprietaire < 0 or doc.repartition_proprietaire > 100:
		frappe.throw("La répartition propriétaire doit être entre 0 et 100%")
	
	if (doc.repartition_locataire + doc.repartition_proprietaire) != 100:
		frappe.throw("La somme des répartitions doit être égale à 100%")
	
	# Validation des détails de paiement si nécessaire
	if doc.statut in ["Payée", "Remboursée"]:
		if not doc.date_paiement:
			frappe.throw("La date de paiement est obligatoire pour une charge payée ou remboursée")
		
		if not doc.methode_paiement:
			frappe.throw("La méthode de paiement est obligatoire pour une charge payée ou remboursée")


def validate_apartment_location_consistency(doc):
	"""Valide la cohérence entre appartement et locations"""
	if not doc.appartement_id:
		frappe.throw("L'appartement est obligatoire")
	
	# Vérifie que l'appartement existe
	if not frappe.db.exists("Appartement", doc.appartement_id):
		frappe.throw("L'appartement spécifié n'existe pas")
	
	# Vérifie la cohérence avec la location longue durée si spécifiée
	if doc.location_longue_duree_id:
		location = frappe.get_doc("Location Longue Durée", doc.location_longue_duree_id)
		if location.appartement_id != doc.appartement_id:
			frappe.throw("La location longue durée ne correspond pas à l'appartement sélectionné")
	
	# Vérifie la cohérence avec la location courte durée si spécifiée
	if doc.location_courte_duree_id:
		location = frappe.get_doc("Location Courte Durée", doc.location_courte_duree_id)
		if location.appartement_id != doc.appartement_id:
			frappe.throw("La location courte durée ne correspond pas à l'appartement sélectionné")
	
	# Ne peut pas avoir les deux types de location en même temps
	if doc.location_longue_duree_id and doc.location_courte_duree_id:
		frappe.throw("Une charge ne peut pas être liée à la fois à une location longue et courte durée")


def validate_dates(doc):
	"""Valide les dates"""
	if doc.date_charge and getdate(doc.date_charge) > getdate(nowdate()):
		frappe.throw("La date de la charge ne peut pas être dans le futur")
	
	if doc.date_paiement and getdate(doc.date_paiement) > getdate(nowdate()):
		frappe.throw("La date de paiement ne peut pas être dans le futur")
	
	if doc.date_charge and doc.date_paiement:
		if getdate(doc.date_paiement) < getdate(doc.date_charge):
			frappe.throw("La date de paiement ne peut pas être antérieure à la date de la charge")


def calculate_amounts(doc):
	"""Calcule automatiquement les montants locataire et propriétaire"""
	if doc.montant:
		# Calcule les montants selon la répartition
		doc.montant_locataire = (doc.montant * doc.repartition_locataire) / 100
		doc.montant_proprietaire = (doc.montant * doc.repartition_proprietaire) / 100
	
	# Définit les informations de création si nouveau document
	if not doc.date_creation:
		doc.date_creation = nowdate()
		doc.cree_par = frappe.session.user


def update_mensualite_margins(doc):
	"""Met à jour les marges des mensualités affectées par cette charge"""
	if not doc.location_longue_duree_id:
		return
	
	# Trouve les mensualités du même mois que la charge
	if doc.date_charge:
		charge_date = getdate(doc.date_charge)
		mois_annee = f"{charge_date.month:02d}/{charge_date.year}"
		
		# Recherche la mensualité correspondante
		mensualite = frappe.db.get_value("Mensualite", {
			"location_longue_duree_id": doc.location_longue_duree_id,
			"mois_annee": mois_annee
		}, "name")
		
		if mensualite:
			# Recalcule les charges de cette mensualité
			recalculate_mensualite_charges(mensualite)


def revert_mensualite_margins(doc):
	"""Remet à jour les marges des mensualités lors de l'annulation"""
	if not doc.location_longue_duree_id:
		return
	
	if doc.date_charge:
		charge_date = getdate(doc.date_charge)
		mois_annee = f"{charge_date.month:02d}/{charge_date.year}"
		
		mensualite = frappe.db.get_value("Mensualite", {
			"location_longue_duree_id": doc.location_longue_duree_id,
			"mois_annee": mois_annee
		}, "name")
		
		if mensualite:
			recalculate_mensualite_charges(mensualite)


def recalculate_mensualite_charges(mensualite_name):
	"""Recalcule les charges d'une mensualité"""
	mensualite = frappe.get_doc("Mensualite", mensualite_name)
	
	# Récupère toutes les charges validées pour ce mois
	mois, annee = map(int, mensualite.mois_annee.split('/'))
	
	charges = frappe.db.sql("""
		SELECT 
			SUM(montant_locataire) as total_charges_locataire,
			SUM(montant_proprietaire) as total_charges_proprietaire
		FROM `tabCharge`
		WHERE appartement_id = (
			SELECT appartement_id 
			FROM `tabLocation Longue Durée` 
			WHERE name = %s
		)
		AND statut = 'Validée'
		AND MONTH(date_charge) = %s
		AND YEAR(date_charge) = %s
		AND docstatus != 2
	""", (mensualite.location_longue_duree_id, mois, annee), as_dict=True)
	
	if charges and charges[0]:
		charge_data = charges[0]
		mensualite.charges_locataire = charge_data.total_charges_locataire or 0
		mensualite.charges_proprietaire = charge_data.total_charges_proprietaire or 0
		
		# Recalcule la marge nette
		if mensualite.marge_mensuelle:
			mensualite.marge_nette = (mensualite.marge_mensuelle - 
								  mensualite.charges_locataire + 
								  mensualite.charges_proprietaire)
		
		mensualite.save(ignore_permissions=True)


def update_apartment_charges_statistics(doc):
	"""Met à jour les statistiques des charges de l'appartement"""
	if not doc.appartement_id:
		return
	
	# Calcule les statistiques des charges pour cet appartement
	stats = frappe.db.sql("""
		SELECT 
			COUNT(*) as total_charges,
			SUM(montant) as montant_total_charges,
			SUM(montant_locataire) as montant_total_locataire,
			SUM(montant_proprietaire) as montant_total_proprietaire,
			SUM(CASE WHEN statut = 'Payée' THEN montant ELSE 0 END) as montant_paye,
			SUM(CASE WHEN statut IN ('En attente', 'Validée') THEN montant ELSE 0 END) as montant_en_attente
		FROM `tabCharge`
		WHERE appartement_id = %s
			AND docstatus != 2
			AND YEAR(date_charge) = YEAR(CURDATE())
	""", (doc.appartement_id,), as_dict=True)
	
	if stats:
		stat = stats[0]
		# Met à jour l'appartement avec les nouvelles statistiques
		frappe.db.set_value("Appartement", doc.appartement_id, {
			"charges_annuelles_totales": stat.montant_total_charges or 0,
			"charges_locataire_annuelles": stat.montant_total_locataire or 0,
			"charges_proprietaire_annuelles": stat.montant_total_proprietaire or 0,
			"charges_payees_annuelles": stat.montant_paye or 0,
			"charges_en_attente_annuelles": stat.montant_en_attente or 0
		})


def notify_stakeholders(doc):
	"""Notifie les parties concernées selon le statut de la charge"""
	if doc.statut == "Validée":
		# Notifie le propriétaire de la nouvelle charge validée
		notify_owner_charge_validated(doc)
		
		# Notifie le locataire si la charge lui incombe partiellement
		if doc.montant_locataire > 0:
			notify_tenant_charge_validated(doc)
	
	elif doc.statut == "Payée":
		# Notifie que la charge a été payée
		notify_charge_paid(doc)
	
	elif doc.statut == "Rejetée":
		# Notifie le rejet de la charge
		notify_charge_rejected(doc)


def notify_owner_charge_validated(doc):
	"""Notifie le propriétaire qu'une charge a été validée"""
	try:
		# Récupère les informations du propriétaire
		appartement = frappe.get_doc("Appartement", doc.appartement_id)
		proprietaire = frappe.get_doc("Proprietaire", appartement.proprietaire_id)
		
		if proprietaire.email:
			# Prépare le contenu de l'email
			subject = f"Nouvelle charge validée - {appartement.adresse}"
			message = f"""
			Bonjour {proprietaire.nom_complet},
			
			Une nouvelle charge a été validée pour votre appartement {appartement.adresse}:
			
			- Type: {doc.type_charge}
			- Description: {doc.description}
			- Montant total: {doc.montant} €
			- Votre part: {doc.montant_proprietaire} €
			- Date: {doc.date_charge}
			
			Cordialement,
			L'équipe de gestion
			"""
			
			# Envoie l'email (à implémenter selon la configuration email)
			# frappe.sendmail(
			#     recipients=[proprietaire.email],
			#     subject=subject,
			#     message=message
			# )
			
	except Exception as e:
		frappe.log_error(f"Erreur lors de l'envoi de notification propriétaire: {str(e)}")


def notify_tenant_charge_validated(doc):
	"""Notifie le locataire qu'une charge lui incombe"""
	try:
		# Récupère les informations du locataire selon le type de location
		locataire_email = None
		locataire_nom = None
		
		if doc.location_longue_duree_id:
			location = frappe.get_doc("Location Longue Durée", doc.location_longue_duree_id)
			locataire_email = location.locataire_email
			locataire_nom = location.locataire_nom
		
		elif doc.location_courte_duree_id:
			location = frappe.get_doc("Location Courte Durée", doc.location_courte_duree_id)
			locataire_email = location.locataire_email
			locataire_nom = location.locataire_nom
		
		if locataire_email:
			appartement = frappe.get_doc("Appartement", doc.appartement_id)
			
			subject = f"Nouvelle charge locative - {appartement.adresse}"
			message = f"""
			Bonjour {locataire_nom},
			
			Une nouvelle charge locative a été validée pour votre logement {appartement.adresse}:
			
			- Type: {doc.type_charge}
			- Description: {doc.description}
			- Montant total: {doc.montant} €
			- Votre part: {doc.montant_locataire} €
			- Date: {doc.date_charge}
			
			Cordialement,
			L'équipe de gestion
			"""
			
			# Envoie l'email (à implémenter selon la configuration email)
			# frappe.sendmail(
			#     recipients=[locataire_email],
			#     subject=subject,
			#     message=message
			# )
			
	except Exception as e:
		frappe.log_error(f"Erreur lors de l'envoi de notification locataire: {str(e)}")


def notify_charge_paid(doc):
	"""Notifie que la charge a été payée"""
	# Logique de notification de paiement (à implémenter)
	pass


def notify_charge_rejected(doc):
	"""Notifie que la charge a été rejetée"""
	# Logique de notification de rejet (à implémenter)
	pass


def calculate_monthly_charges_summary(appartement_id, month, year):
	"""Calcule un résumé des charges mensuelles pour un appartement"""
	charges_summary = frappe.db.sql("""
		SELECT 
			type_charge,
			categorie,
			COUNT(*) as nombre_charges,
			SUM(montant) as montant_total,
			SUM(montant_locataire) as total_locataire,
			SUM(montant_proprietaire) as total_proprietaire,
			statut
		FROM `tabCharge`
		WHERE appartement_id = %s
			AND MONTH(date_charge) = %s
			AND YEAR(date_charge) = %s
			AND docstatus != 2
		GROUP BY type_charge, categorie, statut
		ORDER BY type_charge, categorie
	""", (appartement_id, month, year), as_dict=True)
	
	return charges_summary