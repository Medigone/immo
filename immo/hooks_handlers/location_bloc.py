# -*- coding: utf-8 -*-
# Copyright (c) 2024, IntraPro and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate, add_days

def validate(doc, method):
	"""
	Validation des données lors de la sauvegarde d'une Location Bloc
	"""
	doc.validate_dates()
	doc.validate_appartement_availability()
	doc.calculate_nights_and_price()
	doc.set_timestamps()

def on_update(doc, method):
	"""
	Actions à effectuer lors de la mise à jour d'une Location Bloc
	"""
	doc.update_metrics()



def on_trash(doc, method):
	"""
	Actions à effectuer lors de la suppression définitive d'une Location Bloc
	"""
	# Vérifier s'il y a des Paiements Bloc associés
	paiements_associes = frappe.get_all(
		"Paiement Bloc",
		filters={"location_bloc_id": doc.name},
		fields=["name", "montant_paiement"]
	)
	
	if paiements_associes:
		# Log des paiements qui seront orphelins
		for paiement in paiements_associes:
			frappe.log_error(
				f"Paiement Bloc {paiement.name} (Montant: {paiement.montant_paiement}) devient orphelin suite à la suppression de Location Bloc {doc.name}",
				"Location Bloc Suppression - Paiements Orphelins"
			)
	
	# Log de la suppression pour audit
	frappe.log_error(
		f"Location Bloc {doc.name} supprimée définitivement. Appartement: {doc.appartement_id}, Période: {doc.date_debut_bloc} - {doc.date_fin_bloc}",
		"Location Bloc Suppression"
	)