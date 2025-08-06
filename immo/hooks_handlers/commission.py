# Copyright (c) 2024, Frappe Technologies and Contributors
# See license.txt

import frappe
from frappe.utils import nowdate, getdate


def validate(doc, method):
	"""Validation des données avant sauvegarde"""
	# Validation des pourcentages
	validate_commission_percentage(doc)
	
	# Calcul automatique du montant de commission
	calculate_commission_amount(doc)
	
	# Validation de la cohérence des données
	validate_data_consistency(doc)


def on_update(doc, method):
	"""Actions après mise à jour"""
	# Met à jour les statistiques du référent
	update_referent_statistics(doc)
	
	# Met à jour la marge nette de la location
	update_location_net_margin(doc)
	
	# Génère les notifications selon le statut
	notify_commission_status_change(doc)


def on_cancel(doc, method):
	"""Actions lors de l'annulation"""
	# Remet à jour les statistiques du référent
	update_referent_statistics(doc)
	
	# Remet à jour la marge nette de la location
	update_location_net_margin(doc)


def validate_commission_percentage(doc):
	"""Valide le pourcentage de commission"""
	if doc.pourcentage_commission < 0 or doc.pourcentage_commission > 100:
		frappe.throw("Le pourcentage de commission doit être entre 0 et 100%")
	
	# Vérifie que le pourcentage n'est pas excessif (plus de 50%)
	if doc.pourcentage_commission > 50:
		frappe.msgprint(
			"Attention: Le pourcentage de commission est élevé (plus de 50%)",
			title="Commission élevée",
			indicator="orange"
		)


def calculate_commission_amount(doc):
	"""Calcule automatiquement le montant de la commission"""
	if not doc.location_courte_duree_id or not doc.pourcentage_commission:
		return
	
	try:
		# Récupère la location courte durée
		location = frappe.get_doc("Location Courte Durée", doc.location_courte_duree_id)
		
		# Calcule la commission basée sur la marge totale
		if location.marge_totale:
			doc.montant_commission = (location.marge_totale * doc.pourcentage_commission) / 100
			
			# Calcule aussi la marge nette après commission
			doc.marge_nette_apres_commission = location.marge_totale - doc.montant_commission
		else:
			doc.montant_commission = 0
			doc.marge_nette_apres_commission = 0
			
	except Exception as e:
		frappe.log_error(f"Erreur lors du calcul de la commission: {str(e)}")


def validate_data_consistency(doc):
	"""Valide la cohérence des données"""
	# Vérifie que la location existe et est confirmée
	if doc.location_courte_duree_id:
		location = frappe.get_doc("Location Courte Durée", doc.location_courte_duree_id)
		if location.statut not in ["Confirmé", "En cours", "Terminé"]:
			frappe.throw("La commission ne peut être créée que pour une location confirmée")
	
	# Vérifie que le référent existe et est actif
	if doc.referent_id:
		referent = frappe.get_doc("Référent", doc.referent_id)
		if referent.statut != "Actif":
			frappe.throw("Le référent doit être actif pour recevoir une commission")
	
	# Vérifie qu'il n'y a pas déjà une commission pour cette location et ce référent
	existing = frappe.db.exists("Commission", {
		"location_courte_duree_id": doc.location_courte_duree_id,
		"referent_id": doc.referent_id,
		"name": ["!=", doc.name or ""]
	})
	
	if existing:
		frappe.throw("Une commission existe déjà pour cette location et ce référent")
	
	# Validation des dates de paiement
	if doc.statut_paiement == "Payé":
		if not doc.date_paiement:
			frappe.throw("La date de paiement est obligatoire pour une commission payée")
		
		if not doc.methode_paiement:
			frappe.throw("La méthode de paiement est obligatoire pour une commission payée")
		
		if getdate(doc.date_paiement) > getdate(nowdate()):
			frappe.throw("La date de paiement ne peut pas être dans le futur")


def update_referent_statistics(doc):
	"""Met à jour les statistiques du référent"""
	if not doc.referent_id:
		return
	
	# Calcule les statistiques globales du référent
	stats = frappe.db.sql("""
		SELECT 
			COUNT(*) as total_commissions,
			SUM(montant_commission) as total_montant,
			SUM(CASE WHEN statut_paiement = 'Payé' THEN montant_commission ELSE 0 END) as montant_paye,
			SUM(CASE WHEN statut_paiement = 'En attente' THEN montant_commission ELSE 0 END) as montant_en_attente,
			AVG(pourcentage_commission) as pourcentage_moyen,
			COUNT(DISTINCT location_courte_duree_id) as nombre_locations
		FROM `tabCommission`
		WHERE referent_id = %s
			AND docstatus != 2
	""", (doc.referent_id,), as_dict=True)
	
	if stats:
		stat = stats[0]
		# Met à jour le référent avec les nouvelles statistiques
		frappe.db.set_value("Référent", doc.referent_id, {
			"total_commissions_gagnees": stat.total_montant or 0,
			"commissions_payees": stat.montant_paye or 0,
			"commissions_en_attente": stat.montant_en_attente or 0,
			"nombre_locations_referees": stat.nombre_locations or 0,
			"pourcentage_commission_moyen": stat.pourcentage_moyen or 0
		})


def update_location_net_margin(doc):
	"""Met à jour la marge nette de la location après commission"""
	if not doc.location_courte_duree_id:
		return
	
	# Calcule la marge nette totale après toutes les commissions
	total_commissions = frappe.db.sql("""
		SELECT SUM(montant_commission) as total
		FROM `tabCommission`
		WHERE location_courte_duree_id = %s
			AND docstatus != 2
	""", (doc.location_courte_duree_id,), as_dict=True)
	
	total_commission_amount = total_commissions[0].total if total_commissions else 0
	
	# Met à jour la location avec la marge nette
	location = frappe.get_doc("Location Courte Durée", doc.location_courte_duree_id)
	marge_nette = location.marge_totale - (total_commission_amount or 0)
	
	frappe.db.set_value("Location Courte Durée", doc.location_courte_duree_id, {
		"marge_nette_apres_commission": marge_nette,
		"total_commissions": total_commission_amount or 0
	})


def notify_commission_status_change(doc):
	"""Notifie les changements de statut de commission"""
	if doc.has_value_changed("statut_paiement"):
		if doc.statut_paiement == "Payé":
			notify_commission_paid(doc)
		elif doc.statut_paiement == "Rejeté":
			notify_commission_rejected(doc)


def notify_commission_paid(doc):
	"""Notifie que la commission a été payée"""
	try:
		# Récupère les informations du référent
		referent = frappe.get_doc("Référent", doc.referent_id)
		
		if referent.email:
			# Récupère les informations de la location
			location = frappe.get_doc("Location Courte Durée", doc.location_courte_duree_id)
			appartement = frappe.get_doc("Appartement", location.appartement_id)
			
			subject = f"Commission payée - {appartement.adresse}"
			message = f"""
			Bonjour {referent.nom_complet},
			
			Votre commission a été payée pour la location suivante:
			
			- Appartement: {appartement.adresse}
			- Locataire: {location.locataire_nom}
			- Période: {location.date_debut} - {location.date_fin}
			- Montant de la commission: {doc.montant_commission} €
			- Pourcentage: {doc.pourcentage_commission}%
			- Date de paiement: {doc.date_paiement}
			- Méthode: {doc.methode_paiement}
			
			Merci pour votre collaboration!
			
			Cordialement,
			L'équipe de gestion
			"""
			
			# Envoie l'email (à implémenter selon la configuration email)
			# frappe.sendmail(
			#     recipients=[referent.email],
			#     subject=subject,
			#     message=message
			# )
			
	except Exception as e:
		frappe.log_error(f"Erreur lors de l'envoi de notification de paiement commission: {str(e)}")


def notify_commission_rejected(doc):
	"""Notifie que la commission a été rejetée"""
	try:
		# Récupère les informations du référent
		referent = frappe.get_doc("Référent", doc.referent_id)
		
		if referent.email:
			location = frappe.get_doc("Location Courte Durée", doc.location_courte_duree_id)
			appartement = frappe.get_doc("Appartement", location.appartement_id)
			
			subject = f"Commission rejetée - {appartement.adresse}"
			message = f"""
			Bonjour {referent.nom_complet},
			
			Nous vous informons que votre commission pour la location suivante a été rejetée:
			
			- Appartement: {appartement.adresse}
			- Locataire: {location.locataire_nom}
			- Période: {location.date_debut} - {location.date_fin}
			- Montant: {doc.montant_commission} €
			
			Raison: {doc.commentaires or 'Non spécifiée'}
			
			Pour plus d'informations, veuillez nous contacter.
			
			Cordialement,
			L'équipe de gestion
			"""
			
			# Envoie l'email (à implémenter selon la configuration email)
			# frappe.sendmail(
			#     recipients=[referent.email],
			#     subject=subject,
			#     message=message
			# )
			
	except Exception as e:
		frappe.log_error(f"Erreur lors de l'envoi de notification de rejet commission: {str(e)}")


def auto_calculate_commission_on_location_completion(location_name):
	"""Calcule automatiquement les commissions quand une location se termine"""
	try:
		location = frappe.get_doc("Location Courte Durée", location_name)
		
		# Recherche les référents qui ont des commissions automatiques
		auto_referents = frappe.get_all("Référent", {
			"statut": "Actif",
			"commission_automatique": 1
		}, ["name", "pourcentage_commission_defaut"])
		
		for referent in auto_referents:
			# Vérifie s'il n'y a pas déjà une commission pour ce référent
			existing = frappe.db.exists("Commission", {
				"location_courte_duree_id": location_name,
				"referent_id": referent.name
			})
			
			if not existing and referent.pourcentage_commission_defaut:
				# Crée automatiquement la commission
				commission = frappe.get_doc({
					"doctype": "Commission",
					"referent_id": referent.name,
					"location_courte_duree_id": location_name,
					"pourcentage_commission": referent.pourcentage_commission_defaut,
					"statut_paiement": "En attente",
					"commentaires": "Commission générée automatiquement"
				})
				commission.insert(ignore_permissions=True)
				
	except Exception as e:
		frappe.log_error(f"Erreur lors de la génération automatique des commissions: {str(e)}")


def calculate_referent_performance_metrics(referent_id, period_start=None, period_end=None):
	"""Calcule les métriques de performance d'un référent"""
	date_filter = ""
	params = [referent_id]
	
	if period_start and period_end:
		date_filter = "AND c.creation BETWEEN %s AND %s"
		params.extend([period_start, period_end])
	
	metrics = frappe.db.sql(f"""
		SELECT 
			COUNT(DISTINCT c.location_courte_duree_id) as locations_referees,
			SUM(c.montant_commission) as total_commissions,
			AVG(c.pourcentage_commission) as pourcentage_moyen,
			SUM(l.marge_totale) as marge_totale_generee,
			AVG(l.marge_totale) as marge_moyenne_par_location,
			SUM(l.montant_total_locataire) as chiffre_affaires_genere,
			COUNT(CASE WHEN c.statut_paiement = 'Payé' THEN 1 END) as commissions_payees,
			COUNT(CASE WHEN c.statut_paiement = 'En attente' THEN 1 END) as commissions_en_attente
		FROM `tabCommission` c
		JOIN `tabLocation Courte Durée` l ON c.location_courte_duree_id = l.name
		WHERE c.referent_id = %s
			AND c.docstatus != 2
			{date_filter}
	""", params, as_dict=True)
	
	return metrics[0] if metrics else {}


def generate_commission_report(referent_id=None, period_start=None, period_end=None):
	"""Génère un rapport détaillé des commissions"""
	filters = []
	params = []
	
	if referent_id:
		filters.append("c.referent_id = %s")
		params.append(referent_id)
	
	if period_start and period_end:
		filters.append("c.creation BETWEEN %s AND %s")
		params.extend([period_start, period_end])
	
	where_clause = "WHERE " + " AND ".join(filters) if filters else ""
	
	report_data = frappe.db.sql(f"""
		SELECT 
			r.nom_complet as referent_nom,
			r.email as referent_email,
			l.locataire_nom,
			a.adresse as appartement_adresse,
			l.date_debut,
			l.date_fin,
			l.marge_totale,
			c.pourcentage_commission,
			c.montant_commission,
			c.statut_paiement,
			c.date_paiement,
			c.methode_paiement,
			c.creation as date_creation_commission
		FROM `tabCommission` c
		JOIN `tabRéférent` r ON c.referent_id = r.name
		JOIN `tabLocation Courte Durée` l ON c.location_courte_duree_id = l.name
		JOIN `tabAppartement` a ON l.appartement_id = a.name
		{where_clause}
		AND c.docstatus != 2
		ORDER BY c.creation DESC
	""", params, as_dict=True)
	
	return report_data