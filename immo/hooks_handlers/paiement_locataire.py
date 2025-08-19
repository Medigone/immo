# Copyright (c) 2024, Frappe Technologies and Contributors
# See license.txt

import frappe
from frappe.utils import nowdate, getdate


def on_update(doc, method):
	"""Actions après mise à jour du paiement locataire"""
	# Met à jour le statut de la mensualité si c'est un loyer mensuel
	if doc.type_paiement == "Loyer mensuel":
		update_mensualite_status(doc)
	
	# NOTE: Les statistiques de location et appartement ne sont plus mises à jour
	# car le dashboard HTML affiche ces informations en temps réel
	
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


def update_location_courte_duree_payment_status(doc):
	"""Met à jour le statut des paiements de la location courte durée"""
	try:
		if doc.location_courte_duree_id:
			# Récupérer la location courte durée et recalculer le statut des paiements
			location_doc = frappe.get_doc("Location Courte Duree", doc.location_courte_duree_id)
			
			location_doc.calculate_payment_status()
			
			# Utiliser frappe.db.set_value pour éviter les conflits de concurrence
			update_data = {
				"montant_paye_locataire": location_doc.montant_paye_locataire,
				"montant_restant_locataire": location_doc.montant_restant_locataire,
				"statut_paiement_locataire": location_doc.statut_paiement_locataire,
				"montant_paye_proprietaire": location_doc.montant_paye_proprietaire,
				"montant_restant_proprietaire": location_doc.montant_restant_proprietaire,
				"statut_paiement_proprietaire": location_doc.statut_paiement_proprietaire
			}
			
			for field, value in update_data.items():
				frappe.db.set_value("Location Courte Duree", doc.location_courte_duree_id, field, value)
			
			frappe.db.commit()
			
			# Ajouter à la liste des blocs à mettre à jour si applicable
			if location_doc.location_bloc_id:
				if not hasattr(frappe.local, 'pending_bloc_updates'):
					frappe.local.pending_bloc_updates = set()
				frappe.local.pending_bloc_updates.add(location_doc.location_bloc_id)
				frappe.db.after_commit.add(process_pending_bloc_updates)
			
	except Exception as e:
		frappe.log_error(f"Erreur lors de la mise à jour du statut des paiements de la location courte durée: {str(e)}")


def after_insert(doc, method):
	"""Appelé après l'insertion d'un nouveau paiement locataire"""
	try:
		if not doc.name:
			return
			
		# Mettre à jour le statut des paiements de la location courte durée
		# pour recalculer les montants et mettre à jour le statut
		if doc.location_courte_duree_id:
			update_location_courte_duree_payment_status(doc)
			
	except Exception as e:
		frappe.log_error(f"Erreur dans after_insert Paiement Locataire {doc.name}: {str(e)}")


def on_trash(doc, method):
	"""Appelé lors de la suppression d'un paiement locataire"""
	try:
		if not doc.name:
			return
			
		# Capturer l'ID de la location avant la suppression
		location_id = doc.location_courte_duree_id
		
		# Mettre à jour le statut des paiements de la location courte durée
		# pour recalculer les montants et mettre à jour le statut
		if location_id:
			# Récupérer la location et recalculer
			location_doc = frappe.get_doc("Location Courte Duree", location_id)
			
			# Recalculer le statut des paiements
			location_doc.calculate_payment_status()
			
			# Forcer la sauvegarde avec frappe.db.set_value pour éviter les conflits
			update_data = {
				"montant_paye_locataire": location_doc.montant_paye_locataire,
				"montant_restant_locataire": location_doc.montant_restant_locataire,
				"statut_paiement_locataire": location_doc.statut_paiement_locataire,
				"montant_paye_proprietaire": location_doc.montant_paye_proprietaire,
				"montant_restant_proprietaire": location_doc.montant_restant_proprietaire,
				"statut_paiement_proprietaire": location_doc.statut_paiement_proprietaire
			}
			
			# Mettre à jour chaque champ individuellement pour être sûr
			for field, value in update_data.items():
				frappe.db.set_value("Location Courte Duree", location_id, field, value)
			
			# Vérifier que la mise à jour a bien eu lieu
			frappe.db.commit()
			
			# Forcer le rafraîchissement du formulaire si il est ouvert
			try:
				# Déclencher un événement pour forcer le rafraîchissement
				frappe.publish_realtime('location_courte_duree_updated', {
					'docname': location_id,
					'doctype': 'Location Courte Duree'
				})
			except Exception as e:
				frappe.log_error(f"Erreur lors du rafraîchissement: {str(e)}")
			
	except Exception as e:
		frappe.log_error(f"Erreur dans on_trash Paiement Locataire {doc.name}: {str(e)}")


def process_pending_bloc_updates():
	"""Traite les mises à jour de blocs en attente pour éviter les modifications multiples"""
	try:
		if hasattr(frappe.local, 'pending_bloc_updates') and frappe.local.pending_bloc_updates:
			for bloc_id in frappe.local.pending_bloc_updates:
				try:
					location_bloc = frappe.get_doc("Location Bloc", bloc_id)
					location_bloc.update_metrics()
				except Exception as e:
					frappe.log_error(f"Erreur MAJ métriques bloc {bloc_id}: {str(e)}", "Bloc Update Error")
			
			# Nettoyer la liste après traitement
			frappe.local.pending_bloc_updates.clear()
			
	except Exception as e:
		frappe.log_error(f"Erreur traitement mises à jour blocs: {str(e)}", "Pending Updates Error")