# Copyright (c) 2024, Frappe Technologies and Contributors
# See license.txt

import frappe
from frappe.utils import nowdate, getdate


def on_update(doc, method):
	"""Actions après mise à jour du paiement locataire"""
	# Met à jour le statut de la mensualité si confirmé
	if doc.statut == "Confirmé" and doc.type_paiement == "Loyer mensuel":
		update_mensualite_status(doc)
	
	# Met à jour les statistiques de la location
	update_location_payment_statistics(doc)
	
	# Met à jour les statistiques de l'appartement
	update_apartment_payment_statistics(doc)
	
	# Génère les notifications selon le statut
	notify_payment_status_change(doc)


def on_cancel(doc, method):
	"""Actions lors de l'annulation du paiement"""
	# Remet à jour le statut de la mensualité
	if doc.type_paiement == "Loyer mensuel" and doc.mensualite_id:
		revert_mensualite_status(doc)
	
	# Met à jour les statistiques
	update_location_payment_statistics(doc)
	update_apartment_payment_statistics(doc)


def update_mensualite_status(doc):
	"""Met à jour le statut de paiement de la mensualité"""
	if not doc.mensualite_id:
		return
	
	try:
		# Met à jour le statut de paiement locataire de la mensualité
		frappe.db.set_value("Mensualité", doc.mensualite_id, {
			"statut_paiement_locataire": "Payé",
			"date_paiement_locataire": doc.date_paiement,
			"methode_paiement_locataire": doc.methode_paiement,
			"reference_paiement_locataire": doc.reference_financiere
		})
		
		# Vérifie si la mensualité est complètement payée (locataire + propriétaire)
		mensualite = frappe.get_doc("Mensualité", doc.mensualite_id)
		if (mensualite.statut_paiement_locataire == "Payé" and 
			mensualite.statut_paiement_proprietaire == "Payé"):
			frappe.db.set_value("Mensualité", doc.mensualite_id, "statut_global", "Complète")
			
	except Exception as e:
		frappe.log_error(f"Erreur lors de la mise à jour de la mensualité: {str(e)}")


def revert_mensualite_status(doc):
	"""Remet le statut de la mensualité lors de l'annulation"""
	try:
		frappe.db.set_value("Mensualité", doc.mensualite_id, {
			"statut_paiement_locataire": "En attente",
			"date_paiement_locataire": None,
			"methode_paiement_locataire": None,
			"reference_paiement_locataire": None,
			"statut_global": "En attente"
		})
		
	except Exception as e:
		frappe.log_error(f"Erreur lors de la remise à jour de la mensualité: {str(e)}")


def update_location_payment_statistics(doc):
	"""Met à jour les statistiques de paiement de la location"""
	location_id = None
	
	# Détermine l'ID de la location selon le type
	if doc.mensualite_id:
		# Récupère la location via la mensualité
		mensualite = frappe.get_doc("Mensualité", doc.mensualite_id)
		location_id = mensualite.location_longue_duree_id
		location_type = "Location Longue Durée"
	elif doc.location_longue_duree_id:
		location_id = doc.location_longue_duree_id
		location_type = "Location Longue Durée"
	elif doc.location_courte_duree_id:
		location_id = doc.location_courte_duree_id
		location_type = "Location Courte Durée"
	
	if not location_id:
		return
	
	try:
		# Calcule les statistiques de paiement pour cette location
		stats = frappe.db.sql("""
			SELECT 
				COUNT(*) as total_paiements,
				SUM(montant) as montant_total_recu,
				SUM(montant_net) as montant_net_total,
				SUM(frais_transaction) as frais_totaux,
				COUNT(CASE WHEN statut = 'Confirmé' THEN 1 END) as paiements_confirmes,
				COUNT(CASE WHEN statut = 'En attente' THEN 1 END) as paiements_en_attente,
				AVG(montant) as montant_moyen
			FROM `tabPaiement Locataire`
			WHERE (
				(mensualite_id IN (
					SELECT name FROM `tabMensualité` 
					WHERE location_longue_duree_id = %s
				))
				OR location_longue_duree_id = %s
				OR location_courte_duree_id = %s
			)
			AND docstatus != 2
		""", (location_id, location_id, location_id), as_dict=True)
		
		if stats:
			stat = stats[0]
			# Met à jour la location avec les nouvelles statistiques
			update_data = {
				"total_paiements_recus": stat.montant_total_recu or 0,
				"total_frais_transaction": stat.frais_totaux or 0,
				"nombre_paiements_locataire": stat.total_paiements or 0,
				"taux_paiement_locataire": (stat.paiements_confirmes / stat.total_paiements * 100) if stat.total_paiements > 0 else 0
			}
			
			frappe.db.set_value(location_type, location_id, update_data)
			
	except Exception as e:
		frappe.log_error(f"Erreur lors de la mise à jour des statistiques de location: {str(e)}")


def update_apartment_payment_statistics(doc):
	"""Met à jour les statistiques de paiement de l'appartement"""
	appartement_id = None
	
	# Récupère l'ID de l'appartement
	if doc.mensualite_id:
		mensualite = frappe.get_doc("Mensualité", doc.mensualite_id)
		location = frappe.get_doc("Location Longue Durée", mensualite.location_longue_duree_id)
		appartement_id = location.appartement_id
	elif doc.location_longue_duree_id:
		location = frappe.get_doc("Location Longue Durée", doc.location_longue_duree_id)
		appartement_id = location.appartement_id
	elif doc.location_courte_duree_id:
		location = frappe.get_doc("Location Courte Durée", doc.location_courte_duree_id)
		appartement_id = location.appartement_id
	
	if not appartement_id:
		return
	
	try:
		# Calcule les statistiques globales de paiement pour cet appartement
		stats = frappe.db.sql("""
			SELECT 
				SUM(pl.montant) as total_encaisse_annee,
				SUM(pl.montant_net) as total_net_annee,
				SUM(pl.frais_transaction) as total_frais_annee,
				COUNT(pl.name) as nombre_paiements_annee,
				AVG(pl.montant) as montant_moyen_paiement
			FROM `tabPaiement Locataire` pl
			LEFT JOIN `tabMensualité` m ON pl.mensualite_id = m.name
			LEFT JOIN `tabLocation Longue Durée` lld ON (m.location_longue_duree_id = lld.name OR pl.location_longue_duree_id = lld.name)
			LEFT JOIN `tabLocation Courte Durée` lcd ON pl.location_courte_duree_id = lcd.name
			WHERE (lld.appartement_id = %s OR lcd.appartement_id = %s)
				AND pl.statut = 'Confirmé'
				AND pl.docstatus != 2
				AND YEAR(pl.date_paiement) = YEAR(CURDATE())
		""", (appartement_id, appartement_id), as_dict=True)
		
		if stats:
			stat = stats[0]
			# Met à jour l'appartement avec les nouvelles statistiques
			frappe.db.set_value("Appartement", appartement_id, {
				"total_encaisse_annee": stat.total_encaisse_annee or 0,
				"total_net_encaisse_annee": stat.total_net_annee or 0,
				"total_frais_transaction_annee": stat.total_frais_annee or 0,
				"nombre_paiements_locataire_annee": stat.nombre_paiements_annee or 0
			})
			
	except Exception as e:
		frappe.log_error(f"Erreur lors de la mise à jour des statistiques d'appartement: {str(e)}")


def notify_payment_status_change(doc):
	"""Notifie les changements de statut de paiement"""
	if doc.has_value_changed("statut"):
		if doc.statut == "Confirmé":
			notify_payment_confirmed(doc)
			send_payment_confirmation_to_owner(doc)
		elif doc.statut == "Rejeté":
			notify_payment_rejected(doc)


def notify_payment_confirmed(doc):
	"""Notifie la confirmation du paiement au locataire"""
	try:
		# Récupère les informations du locataire
		locataire_email = None
		locataire_nom = None
		appartement_adresse = None
		
		if doc.mensualite_id:
			mensualite = frappe.get_doc("Mensualité", doc.mensualite_id)
			location = frappe.get_doc("Location Longue Durée", mensualite.location_longue_duree_id)
			locataire_email = location.locataire_email
			locataire_nom = location.locataire_nom
			appartement = frappe.get_doc("Appartement", location.appartement_id)
			appartement_adresse = appartement.adresse
		
		elif doc.location_longue_duree_id:
			location = frappe.get_doc("Location Longue Durée", doc.location_longue_duree_id)
			locataire_email = location.locataire_email
			locataire_nom = location.locataire_nom
			appartement = frappe.get_doc("Appartement", location.appartement_id)
			appartement_adresse = appartement.adresse
		
		elif doc.location_courte_duree_id:
			location = frappe.get_doc("Location Courte Durée", doc.location_courte_duree_id)
			locataire_email = location.locataire_email
			locataire_nom = location.locataire_nom
			appartement = frappe.get_doc("Appartement", location.appartement_id)
			appartement_adresse = appartement.adresse
		
		if locataire_email:
			subject = f"Paiement confirmé - {appartement_adresse}"
			message = f"""
			Bonjour {locataire_nom},
			
			Nous confirmons la réception de votre paiement:
			
			- Appartement: {appartement_adresse}
			- Type: {doc.type_paiement}
			- Montant: {doc.montant} €
			- Montant net: {doc.montant_net} €
			- Date de paiement: {doc.date_paiement}
			- Méthode: {doc.methode_paiement}
			- Référence: {doc.reference_financiere or 'N/A'}
			
			Merci pour votre ponctualité!
			
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
		frappe.log_error(f"Erreur lors de l'envoi de confirmation de paiement: {str(e)}")


def send_payment_confirmation_to_owner(doc):
	"""Envoie une notification au propriétaire"""
	try:
		# Récupère les informations du propriétaire
		appartement_id = None
		
		if doc.mensualite_id:
			mensualite = frappe.get_doc("Mensualité", doc.mensualite_id)
			location = frappe.get_doc("Location Longue Durée", mensualite.location_longue_duree_id)
			appartement_id = location.appartement_id
		elif doc.location_longue_duree_id:
			location = frappe.get_doc("Location Longue Durée", doc.location_longue_duree_id)
			appartement_id = location.appartement_id
		elif doc.location_courte_duree_id:
			location = frappe.get_doc("Location Courte Durée", doc.location_courte_duree_id)
			appartement_id = location.appartement_id
		
		if appartement_id:
			appartement = frappe.get_doc("Appartement", appartement_id)
			proprietaire = frappe.get_doc("Propriétaire", appartement.proprietaire_id)
			
			if proprietaire.email:
				subject = f"Paiement reçu - {appartement.adresse}"
				message = f"""
				Bonjour {proprietaire.nom_complet},
				
				Nous avons reçu un paiement pour votre appartement {appartement.adresse}:
				
				- Type: {doc.type_paiement}
				- Montant: {doc.montant} €
				- Date: {doc.date_paiement}
				- Locataire: {getattr(location, 'locataire_nom', 'N/A')}
				
				Le versement de votre part sera traité selon les modalités convenues.
				
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


def notify_payment_rejected(doc):
	"""Notifie le rejet du paiement"""
	try:
		# Récupère les informations du locataire pour notification
		locataire_email = None
		locataire_nom = None
		
		if doc.mensualite_id:
			mensualite = frappe.get_doc("Mensualité", doc.mensualite_id)
			location = frappe.get_doc("Location Longue Durée", mensualite.location_longue_duree_id)
			locataire_email = location.locataire_email
			locataire_nom = location.locataire_nom
		
		elif doc.location_longue_duree_id:
			location = frappe.get_doc("Location Longue Durée", doc.location_longue_duree_id)
			locataire_email = location.locataire_email
			locataire_nom = location.locataire_nom
		
		elif doc.location_courte_duree_id:
			location = frappe.get_doc("Location Courte Durée", doc.location_courte_duree_id)
			locataire_email = location.locataire_email
			locataire_nom = location.locataire_nom
		
		if locataire_email:
			subject = f"Paiement rejeté - Action requise"
			message = f"""
			Bonjour {locataire_nom},
			
			Nous vous informons que votre paiement a été rejeté:
			
			- Type: {doc.type_paiement}
			- Montant: {doc.montant} €
			- Date: {doc.date_paiement}
			- Référence: {doc.reference_financiere or 'N/A'}
			
			Raison: {doc.commentaires or 'Non spécifiée'}
			
			Veuillez nous contacter pour régulariser la situation.
			
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
		frappe.log_error(f"Erreur lors de l'envoi de notification de rejet: {str(e)}")


def auto_reconcile_payments():
	"""Réconcilie automatiquement les paiements avec les mensualités"""
	try:
		# Recherche les paiements confirmés sans mensualité associée
		unmatched_payments = frappe.get_all("Paiement Locataire", {
			"statut": "Confirmé",
			"type_paiement": "Loyer mensuel",
			"mensualite_id": ["", "is", "not set"],
			"location_longue_duree_id": ["", "is not", "not set"]
		}, ["name", "location_longue_duree_id", "date_paiement", "montant"])
		
		for payment in unmatched_payments:
			# Recherche une mensualité correspondante
			payment_date = getdate(payment.date_paiement)
			mois_annee = f"{payment_date.month:02d}/{payment_date.year}"
			
			mensualite = frappe.db.get_value("Mensualité", {
				"location_longue_duree_id": payment.location_longue_duree_id,
				"mois_annee": mois_annee,
				"statut_paiement_locataire": "En attente"
			}, "name")
			
			if mensualite:
				# Associe le paiement à la mensualité
				frappe.db.set_value("Paiement Locataire", payment.name, "mensualite_id", mensualite)
				
				# Met à jour la mensualité
				frappe.db.set_value("Mensualité", mensualite, {
					"statut_paiement_locataire": "Payé",
					"date_paiement_locataire": payment.date_paiement
				})
				
	except Exception as e:
		frappe.log_error(f"Erreur lors de la réconciliation automatique: {str(e)}")