# Copyright (c) 2024, Frappe Technologies and Contributors
# See license.txt

import frappe
from frappe.utils import nowdate, getdate, add_months


def on_update(doc, method):
	"""Actions après mise à jour du paiement propriétaire"""
	try:
		# Vérifier que le document existe en base et a un nom
		if not doc.name:
			return
		
		# Met à jour le statut de la mensualité si confirmé
		if doc.status == "Payé" and doc.type_paiement == "Loyer mensuel":
			update_mensualite_status(doc)
		
		# NOTE: Les statistiques du propriétaire ne sont plus mises à jour
		# car le dashboard HTML affiche ces informations en temps réel
		
		# Mettre à jour le statut des paiements de la location courte durée
		if doc.location_courte_duree_id:
			update_location_courte_duree_payment_status(doc)
		
	except Exception as e:
		frappe.log_error(f"Erreur dans on_update Paiement Proprietaire {doc.name}: {str(e)}")
		# Ne pas faire échouer la sauvegarde pour des erreurs de statistiques


def on_cancel(doc, method):
	"""Actions lors de l'annulation du paiement"""
	try:
		# Remet à jour le statut de la mensualité
		if doc.type_paiement == "Loyer mensuel" and doc.mensualite_id:
			revert_mensualite_status(doc)
		
		# NOTE: Les statistiques du propriétaire ne sont plus mises à jour
		# car le dashboard HTML affiche ces informations en temps réel
		
		# Mettre à jour le statut des paiements de la location courte durée
		if doc.location_courte_duree_id:
			update_location_courte_duree_payment_status(doc)
		
	except Exception as e:
		frappe.log_error(f"Erreur dans on_cancel Paiement Proprietaire {doc.name}: {str(e)}")
		# Ne pas faire échouer l'annulation pour des erreurs de statistiques


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
		location = frappe.get_doc("Location Longue Duree", mensualite.location_longue_duree_id)
		
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
			# Crée la mensualité suivante
			next_mensualite = frappe.get_doc({
				"doctype": "Mensualite",
				"location_longue_duree_id": mensualite.location_longue_duree_id,
				"mois_annee": next_mois_annee,
				"loyer_locataire": mensualite.loyer_locataire,
				"loyer_proprietaire": mensualite.loyer_proprietaire,
				"charges_locataire": mensualite.charges_locataire,
				"charges_proprietaire": mensualite.charges_proprietaire,
				"statut_global": "En attente",
				"statut_paiement_locataire": "En attente",
				"statut_paiement_proprietaire": "En attente"
			})
			next_mensualite.insert()
			
	except Exception as e:
		frappe.log_error(f"Erreur lors de la génération de la mensualité suivante: {str(e)}")


def update_location_courte_duree_payment_status(doc):
	"""Met à jour le statut des paiements de la location courte durée"""
	try:
		if doc.location_courte_duree_id:
			# Récupérer la location courte durée et recalculer le statut des paiements
			location_doc = frappe.get_doc("Location Courte Duree", doc.location_courte_duree_id)
			
			location_doc.calculate_payment_status()
			
			location_doc.save()
			
	except Exception as e:
		frappe.log_error(f"Erreur lors de la mise à jour du statut des paiements de la location courte durée: {str(e)}")


def after_insert(doc, method):
	"""Appelé après l'insertion d'un nouveau paiement propriétaire"""
	try:
		if not doc.name:
			return
			
		# Mettre à jour le statut des paiements de la location courte durée
		# pour recalculer les montants et mettre à jour le statut
		if doc.location_courte_duree_id:
			update_location_courte_duree_payment_status(doc)
			
	except Exception as e:
		frappe.log_error(f"Erreur dans after_insert Paiement Proprietaire {doc.name}: {str(e)}")


def on_trash(doc, method):
	"""Appelé lors de la suppression d'un paiement propriétaire"""
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
				"montant_paye_proprietaire": location_doc.montant_paye_proprietaire,
				"montant_paye_locataire": location_doc.montant_paye_locataire,
				"montant_restant_locataire": location_doc.montant_restant_locataire,
				"statut_paiement_locataire": location_doc.statut_paiement_locataire,
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
		frappe.log_error(f"Erreur dans on_trash Paiement Proprietaire {doc.name}: {str(e)}")
