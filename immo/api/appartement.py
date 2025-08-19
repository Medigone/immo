# Copyright (c) 2024, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from datetime import datetime, timedelta
from frappe.utils import getdate, add_days, date_diff


@frappe.whitelist()
def get_appartement_dashboard_data(appartement_id):
	"""Récupère les données du dashboard pour un appartement"""
	try:
		# Vérifier que l'appartement existe
		appartement = frappe.get_doc("Appartement", appartement_id)
		
		# Calculer la période (6 mois avant et après aujourd'hui)
		aujourdhui = getdate()
		date_debut = add_days(aujourdhui, -180)  # 6 mois avant
		date_fin = add_days(aujourdhui, 180)     # 6 mois après
		
		# Récupérer les locations courte durée
		locations_courte = frappe.get_all("Location Courte Duree",
			filters={
				"appartement_id": appartement_id,
				"date_debut": ["<=", date_fin],
				"date_fin": [">=", date_debut]
			},
			fields=["name", "date_debut", "date_fin", "locataire_nom"]
		)
		
		# Récupérer les locations longue durée
		locations_longue = frappe.get_all("Location Longue Duree",
			filters={
				"appartement_id": appartement_id,
				"date_debut": ["<=", date_fin],
				"date_fin": [">=", date_debut],
				"statut": ["in", ["Actif", "Terminé"]]
			},
			fields=["name", "date_debut", "date_fin", "locataire_nom", "statut"]
		)
		
		# Générer le calendrier d'occupation
		calendrier = generate_occupation_calendar(date_debut, date_fin, locations_courte, locations_longue)
		
		# Calculer les statistiques avec la méthode unifiée
		stats = appartement.calculate_rentability()
		
		return {
			"calendrier": calendrier,
			"stats": stats,
			"locations_courte": locations_courte,
			"locations_longue": locations_longue,
			"periode": {
				"debut": date_debut,
				"fin": date_fin
			}
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur get_appartement_dashboard_data: {str(e)}")
		return {"error": str(e)}


def generate_occupation_calendar(date_debut, date_fin, locations_courte, locations_longue):
	"""Génère le calendrier d'occupation jour par jour"""
	calendrier = []
	current_date = getdate(date_debut)
	end_date = getdate(date_fin)
	
	while current_date <= end_date:
		jour_data = {
			"date": current_date.strftime("%Y-%m-%d"),
			"occupe": False,
			"locataire": None,
			"location_id": None,
			"type_location": None
		}
		
		# Vérifier les locations courte durée
		for location in locations_courte:
			if (getdate(location.date_debut) <= current_date <= getdate(location.date_fin)):
				jour_data["occupe"] = True
				jour_data["locataire"] = location.locataire_nom
				jour_data["location_id"] = location.name
				jour_data["type_location"] = "Courte Durée"
				break
		
		# Si pas occupé par courte durée, vérifier longue durée
		if not jour_data["occupe"]:
			for location in locations_longue:
				if (getdate(location.date_debut) <= current_date <= getdate(location.date_fin)):
					jour_data["occupe"] = True
					jour_data["locataire"] = location.locataire_nom
					jour_data["location_id"] = location.name
					jour_data["type_location"] = "Longue Durée"
					break
		
		calendrier.append(jour_data)
		current_date = add_days(current_date, 1)
	
	return calendrier


# Fonction calculate_appartement_stats supprimée - remplacée par la méthode unifiée calculate_rentability dans la classe Appartement