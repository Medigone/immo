# -*- coding: utf-8 -*-
# Copyright (c) 2024, IntraPro and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
	"""Migration pour ajouter les fonctionnalités de location bloc"""
	
	# Créer les champs personnalisés pour Location Courte Duree
	custom_fields = {
		"Location Courte Duree": [
			{
				"fieldname": "bloc_section",
				"label": "Gestion Location Bloc",
				"fieldtype": "Section Break",
				"insert_after": "statut",
				"collapsible": 1
			},
			{
				"fieldname": "location_bloc_id",
				"label": "Location Bloc",
				"fieldtype": "Link",
				"options": "Location Bloc",
				"insert_after": "bloc_section",
				"depends_on": "eval:doc.type_location=='Sous-location'"
			},
			{
				"fieldname": "type_location",
				"label": "Type de location",
				"fieldtype": "Select",
				"options": "Directe\nSous-location",
				"default": "Directe",
				"insert_after": "location_bloc_id",
				"reqd": 1
			},
			{
				"fieldname": "marge_sur_bloc",
				"label": "Marge sur bloc",
				"fieldtype": "Currency",
				"insert_after": "type_location",
				"read_only": 1,
				"depends_on": "eval:doc.type_location=='Sous-location'"
			},
			{
				"fieldname": "quote_part_bloc",
				"label": "Quote-part bloc",
				"fieldtype": "Currency",
				"insert_after": "marge_sur_bloc",
				"read_only": 1,
				"depends_on": "eval:doc.type_location=='Sous-location'"
			}
		]
	}
	
	try:
		# Créer les champs personnalisés
		create_custom_fields(custom_fields, update=True)
		frappe.db.commit()
		
		print("Migration terminée: Fonctionnalités de location bloc ajoutées avec succès")
		
	except Exception as e:
		frappe.log_error(f"Erreur lors de la migration location bloc: {str(e)}")
		print(f"Erreur lors de la migration: {str(e)}")
		raise