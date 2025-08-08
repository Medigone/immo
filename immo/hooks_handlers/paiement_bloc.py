# -*- coding: utf-8 -*-
# Copyright (c) 2024, IntraPro and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate

def validate(doc, method):
	"""
	Validation des données lors de la sauvegarde d'un Paiement Bloc
	"""
	doc.validate_location_bloc()
	doc.validate_montant()
	doc.validate_proprietaire_consistency()
	doc.set_appartement_from_bloc()
	doc.set_timestamps()

def on_update(doc, method):
	"""
	Actions à effectuer lors de la mise à jour d'un Paiement Bloc
	"""
	update_location_bloc_payment_status(doc)



def on_trash(doc, method):
	"""
	Actions à effectuer lors de la suppression définitive d'un Paiement Bloc
	"""
	# Mettre à jour la Location Bloc associée après suppression
	update_location_bloc_payment_status_on_delete(doc)
	
	# Log de la suppression pour audit
	frappe.log_error(
		f"Paiement Bloc {doc.name} supprimé définitivement. Location Bloc: {doc.location_bloc_id}, Montant: {doc.montant_paiement}",
		"Paiement Bloc Suppression"
	)

def update_location_bloc_payment_status(paiement_doc):
	"""
	Met à jour les métriques dans la Location Bloc associée
	"""
	if not paiement_doc.location_bloc_id:
		return
	
	try:
		# Vérifier que la Location Bloc existe encore
		if not frappe.db.exists("Location Bloc", paiement_doc.location_bloc_id):
			frappe.log_error(
				f"Location Bloc {paiement_doc.location_bloc_id} n'existe plus lors de la mise à jour du paiement {paiement_doc.name}",
				"Paiement Bloc - Location Bloc Inexistante"
			)
			return
		
		# Calculer directement le montant total payé depuis la base de données
		# Inclure tous les paiements existants pour cette location bloc
		total_paye = frappe.db.sql("""
			SELECT COALESCE(SUM(montant_paiement), 0)
			FROM `tabPaiement Bloc`
			WHERE location_bloc_id = %s
		""", (paiement_doc.location_bloc_id,))[0][0] or 0
		
		# Récupérer le montant total propriétaire
		montant_total_proprietaire = frappe.db.get_value("Location Bloc", paiement_doc.location_bloc_id, "montant_total_proprietaire") or 0
		
		# Calculer le solde restant et le pourcentage
		solde_restant = flt(montant_total_proprietaire) - flt(total_paye)
		pourcentage_paye = (flt(total_paye) / flt(montant_total_proprietaire)) * 100 if flt(montant_total_proprietaire) > 0 else 0
		
		# Mettre à jour directement les champs liés aux paiements propriétaire
		frappe.db.sql("""
			UPDATE `tabLocation Bloc`
			SET montant_total_paye = %s,
				solde_restant = %s,
				pourcentage_paye = %s,
				modified = NOW()
			WHERE name = %s
		""", (flt(total_paye), solde_restant, pourcentage_paye, paiement_doc.location_bloc_id))
		
		# Log de succès pour debug
		frappe.logger().info(
			f"Métriques mises à jour pour Location Bloc {paiement_doc.location_bloc_id} suite à modification du Paiement Bloc {paiement_doc.name}. Total payé: {total_paye}, Solde: {solde_restant}"
		)
		
	except Exception as e:
		frappe.log_error(
			f"Erreur mise à jour Location Bloc {paiement_doc.location_bloc_id}: {str(e)}",
			"Paiement Bloc Update Error"
		)
		frappe.db.rollback()

def update_location_bloc_payment_status_on_delete(paiement_doc):
	"""
	Met à jour les métriques dans la Location Bloc associée lors de la suppression
	Exclut le paiement en cours de suppression du calcul
	"""
	if not paiement_doc.location_bloc_id:
		return
	
	try:
		# Vérifier que la Location Bloc existe encore
		if not frappe.db.exists("Location Bloc", paiement_doc.location_bloc_id):
			frappe.log_error(
				f"Location Bloc {paiement_doc.location_bloc_id} n'existe plus lors de la suppression du paiement {paiement_doc.name}",
				"Paiement Bloc - Location Bloc Inexistante"
			)
			return
		
		# Calculer le montant total payé SANS le paiement en cours de suppression
		total_paye = frappe.db.sql("""
			SELECT COALESCE(SUM(montant_paiement), 0)
			FROM `tabPaiement Bloc`
			WHERE location_bloc_id = %s AND name != %s
		""", (paiement_doc.location_bloc_id, paiement_doc.name))[0][0] or 0
		
		# Récupérer le montant total propriétaire
		montant_total_proprietaire = frappe.db.get_value("Location Bloc", paiement_doc.location_bloc_id, "montant_total_proprietaire") or 0
		
		# Calculer le solde restant et le pourcentage
		solde_restant = flt(montant_total_proprietaire) - flt(total_paye)
		pourcentage_paye = (flt(total_paye) / flt(montant_total_proprietaire)) * 100 if flt(montant_total_proprietaire) > 0 else 0
		
		# Mettre à jour directement les champs liés aux paiements propriétaire
		frappe.db.sql("""
			UPDATE `tabLocation Bloc`
			SET montant_total_paye = %s,
				solde_restant = %s,
				pourcentage_paye = %s,
				modified = NOW()
			WHERE name = %s
		""", (flt(total_paye), solde_restant, pourcentage_paye, paiement_doc.location_bloc_id))
		
		# Publier l'événement en temps réel pour mettre à jour l'interface
		frappe.publish_realtime(
			'location_bloc_updated',
			{
				'location_bloc_id': paiement_doc.location_bloc_id,
				'action': 'payment_deleted',
				'total_paye': total_paye,
				'solde_restant': solde_restant,
				'pourcentage_paye': pourcentage_paye
			}
		)
		
		# Log de succès pour debug
		frappe.logger().info(
			f"Métriques mises à jour pour Location Bloc {paiement_doc.location_bloc_id} suite à suppression du Paiement Bloc {paiement_doc.name}. Total payé: {total_paye}, Solde: {solde_restant}"
		)
		
	except Exception as e:
		frappe.log_error(
			f"Erreur mise à jour Location Bloc {paiement_doc.location_bloc_id} lors de suppression: {str(e)}",
			"Paiement Bloc Delete Error"
		)
		frappe.db.rollback()