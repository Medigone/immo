# Copyright (c) 2024, Frappe Technologies and Contributors
# See license.txt

import frappe
from frappe.utils import nowdate, getdate


def on_update(doc, method):
	"""Actions après mise à jour du paiement locataire"""
	# Met à jour le statut de la mensualité si c'est un loyer mensuel
	if doc.type_paiement == "Loyer mensuel":
		update_mensualite_status(doc)
	
	# Met à jour les statistiques de la location
	update_location_payment_statistics(doc)
	
	# Met à jour les statistiques de l'appartement
	update_apartment_payment_statistics(doc)
	
	# Met à jour les métriques de la location bloc si liée à un bloc
	if doc.location_bloc_id:
		update_location_bloc_metrics_after_payment(doc)
	
	# Mettre à jour le statut des paiements de la location courte durée
	if doc.location_courte_duree_id:
		update_location_courte_duree_payment_status(doc)





def update_mensualite_status(doc):
	"""Met à jour le statut de paiement de la mensualité"""
	if not doc.mensualite_id:
		return
	
	try:
		# Met à jour les informations de paiement locataire de la mensualité
		frappe.db.set_value("Mensualite", doc.mensualite_id, {
			"date_paiement_locataire": doc.date_paiement,
			"methode_paiement_locataire": doc.methode_paiement,
			"reference_paiement_locataire": doc.reference_paiement
		})
			
	except Exception as e:
		frappe.log_error(f"Erreur lors de la mise à jour de la mensualité: {str(e)}")





def update_location_payment_statistics(doc):
	"""Met à jour les statistiques de paiement de la location"""
	try:
		location_id = None
		
		# Détermine l'ID de la location selon le type
		if doc.mensualite_id:
			# Récupère la location via la mensualité
			mensualite = frappe.get_doc("Mensualite", doc.mensualite_id)
			location_id = mensualite.location_longue_duree_id
			location_type = "Location Longue Duree"
		elif doc.location_longue_duree_id:
			location_id = doc.location_longue_duree_id
			location_type = "Location Longue Duree"
		elif doc.location_courte_duree_id:
			location_id = doc.location_courte_duree_id
			location_type = "Location Courte Duree"
		
		if not location_id:
			return
		
		# NOTE: Les champs de statistiques de la location ne sont plus mis à jour
		# car le dashboard HTML affiche ces informations en temps réel
		# via l'API get_proprietaire_dashboard_data
		
	except Exception as e:
		frappe.log_error(f"Erreur lors de la mise à jour des statistiques de location: {str(e)}")


def update_apartment_payment_statistics(doc):
	"""Met à jour les statistiques de paiement de l'appartement"""
	try:
		appartement_id = None
		
		# Récupère l'ID de l'appartement
		if doc.mensualite_id:
			mensualite = frappe.get_doc("Mensualite", doc.mensualite_id)
			location = frappe.get_doc("Location Longue Duree", mensualite.location_longue_duree_id)
			appartement_id = location.appartement_id
		elif doc.location_longue_duree_id:
			location = frappe.get_doc("Location Longue Duree", doc.location_longue_duree_id)
			appartement_id = location.appartement_id
		elif doc.location_courte_duree_id:
			location = frappe.get_doc("Location Courte Duree", doc.location_courte_duree_id)
			appartement_id = location.appartement_id
		
		if not appartement_id:
			return
		
		# NOTE: Les champs de statistiques de l'appartement ne sont plus mis à jour
		# car le dashboard HTML affiche ces informations en temps réel
		# via l'API get_proprietaire_dashboard_data
		
	except Exception as e:
		frappe.log_error(f"Erreur lors de la mise à jour des statistiques d'appartement: {str(e)}")





def notify_payment_confirmed(doc):
	"""Notifie la confirmation du paiement au locataire"""
	try:
		# Récupère les informations du locataire
		locataire_email = None
		locataire_nom = None
		appartement_adresse = None
		
		if doc.mensualite_id:
			mensualite = frappe.get_doc("Mensualite", doc.mensualite_id)
			location = frappe.get_doc("Location Longue Duree", mensualite.location_longue_duree_id)
			locataire_email = location.locataire_email
			locataire_nom = location.locataire_nom
			appartement = frappe.get_doc("Appartement", location.appartement_id)
			appartement_adresse = appartement.adresse
		
		elif doc.location_longue_duree_id:
			location = frappe.get_doc("Location Longue Duree", doc.location_longue_duree_id)
			locataire_email = location.locataire_email
			locataire_nom = location.locataire_nom
			appartement = frappe.get_doc("Appartement", location.appartement_id)
			appartement_adresse = appartement.adresse
		
		elif doc.location_courte_duree_id:
			location = frappe.get_doc("Location Courte Duree", doc.location_courte_duree_id)
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
			- Date de paiement: {doc.date_paiement}
			- Méthode: {doc.methode_paiement}
			- Référence: {doc.reference_paiement or 'N/A'}
			
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
			mensualite = frappe.get_doc("Mensualite", doc.mensualite_id)
			location = frappe.get_doc("Location Longue Duree", mensualite.location_longue_duree_id)
			appartement_id = location.appartement_id
		elif doc.location_longue_duree_id:
			location = frappe.get_doc("Location Longue Duree", doc.location_longue_duree_id)
			appartement_id = location.appartement_id
		elif doc.location_courte_duree_id:
			location = frappe.get_doc("Location Courte Duree", doc.location_courte_duree_id)
			appartement_id = location.appartement_id
		
		if appartement_id:
			appartement = frappe.get_doc("Appartement", appartement_id)
			proprietaire = frappe.get_doc("Proprietaire", appartement.proprietaire_id)
			
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
			mensualite = frappe.get_doc("Mensualite", doc.mensualite_id)
			location = frappe.get_doc("Location Longue Duree", mensualite.location_longue_duree_id)
			locataire_email = location.locataire_email
			locataire_nom = location.locataire_nom
		
		elif doc.location_longue_duree_id:
			location = frappe.get_doc("Location Longue Duree", doc.location_longue_duree_id)
			locataire_email = location.locataire_email
			locataire_nom = location.locataire_nom
		
		elif doc.location_courte_duree_id:
			location = frappe.get_doc("Location Courte Duree", doc.location_courte_duree_id)
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
			- Référence: {doc.reference_paiement or 'N/A'}
			
			Raison: {reason or 'Non spécifiée'}
			
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


def update_location_bloc_metrics_after_payment(doc):
	"""Met à jour les métriques de la location bloc après un paiement locataire"""
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
	except Exception as e:
		frappe.log_error(f"Erreur MAJ métriques après paiement {doc.location_bloc_id}: {str(e)}", "Paiement Locataire Metrics Update Error")


def auto_reconcile_payments():
	"""Réconcilie automatiquement les paiements avec les mensualités"""
	try:
		# Recherche les paiements sans mensualité associée
		unmatched_payments = frappe.get_all("Paiement Locataire", {
			"type_paiement": "Loyer mensuel",
			"mensualite_id": ["", "is", "not set"],
			"location_longue_duree_id": ["", "is not", "not set"]
		}, ["name", "location_longue_duree_id", "date_paiement", "montant"])
		
		for payment in unmatched_payments:
			# Recherche une mensualité correspondante
			payment_date = getdate(payment.date_paiement)
			mois_annee = f"{payment_date.month:02d}/{payment_date.year}"
			
			mensualite = frappe.db.get_value("Mensualite", {
				"location_longue_duree_id": payment.location_longue_duree_id,
				"mois_annee": mois_annee
			}, "name")
			
			if mensualite:
				# Associe le paiement à la mensualité
				frappe.db.set_value("Paiement Locataire", payment.name, "mensualite_id", mensualite)
				
				# Met à jour la mensualité
				frappe.db.set_value("Mensualite", mensualite, {
					"date_paiement_locataire": payment.date_paiement
				})
				
	except Exception as e:
		frappe.log_error(f"Erreur lors de la réconciliation automatique: {str(e)}")


def update_location_courte_duree_payment_status(doc):
	"""Met à jour le statut des paiements de la location courte durée"""
	try:
		if doc.location_courte_duree_id:
			# Déclencher la mise à jour de la location courte durée
			# Cela va automatiquement appeler on_update qui calculera le statut des paiements
			frappe.db.set_value("Location Courte Duree", doc.location_courte_duree_id, "modified", frappe.utils.now())
			
	except Exception as e:
		frappe.log_error(f"Erreur lors de la mise à jour du statut des paiements de la location courte durée: {str(e)}")