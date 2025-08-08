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
		
		# Calculer les statistiques
		stats = calculate_appartement_stats(appartement_id, locations_courte, locations_longue)
		
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


def calculate_appartement_stats(appartement_id, locations_courte, locations_longue):
	"""Calcule les statistiques de l'appartement"""
	try:
		# Période des 12 derniers mois
		aujourdhui = getdate()
		date_debut_stats = add_days(aujourdhui, -365)
		
		# Revenus des locations courte durée
		revenus_courte = frappe.db.sql("""
			SELECT SUM(pl.montant) as total
			FROM `tabPaiement Locataire` pl
			INNER JOIN `tabLocation Courte Duree` lcd ON pl.location_courte_duree_id = lcd.name
			WHERE lcd.appartement_id = %s
			AND pl.date_paiement BETWEEN %s AND %s
			AND pl.statut = 'Payé'
		""", (appartement_id, date_debut_stats, aujourdhui), as_dict=True)
		
		# Revenus des locations longue durée
		revenus_longue = frappe.db.sql("""
			SELECT SUM(pl.montant) as total
			FROM `tabPaiement Locataire` pl
			INNER JOIN `tabLocation Longue Duree` lld ON pl.location_longue_duree_id = lld.name
			WHERE lld.appartement_id = %s
			AND pl.date_paiement BETWEEN %s AND %s
			AND pl.statut = 'Payé'
		""", (appartement_id, date_debut_stats, aujourdhui), as_dict=True)
		
		# Charges de l'appartement
		charges = frappe.db.sql("""
			SELECT SUM(montant) as total
			FROM `tabCharge`
			WHERE appartement_id = %s
			AND date_charge BETWEEN %s AND %s
		""", (appartement_id, date_debut_stats, aujourdhui), as_dict=True)
		
		total_revenus_courte = revenus_courte[0].total or 0
		total_revenus_longue = revenus_longue[0].total or 0
		total_revenus = total_revenus_courte + total_revenus_longue
		total_charges = charges[0].total or 0
		benefit_net = total_revenus - total_charges
		
		# Calculer le taux d'occupation sur les 12 derniers mois
		total_jours = 365
		jours_occupes = 0
		
		# Compter les jours occupés par les locations courte durée
		for location in locations_courte:
			debut = max(getdate(location.date_debut), date_debut_stats)
			fin = min(getdate(location.date_fin), aujourdhui)
			if debut <= fin:
				jours_occupes += date_diff(fin, debut) + 1
		
		# Compter les jours occupés par les locations longue durée
		for location in locations_longue:
			debut = max(getdate(location.date_debut), date_debut_stats)
			fin = min(getdate(location.date_fin), aujourdhui)
			if debut <= fin:
				jours_occupes += date_diff(fin, debut) + 1
		
		taux_occupation = (jours_occupes / total_jours) * 100 if total_jours > 0 else 0
		
		return {
			"revenus_total": total_revenus,
			"revenus_courte_duree": total_revenus_courte,
			"revenus_longue_duree": total_revenus_longue,
			"charges_total": total_charges,
			"benefice_net": benefit_net,
			"taux_occupation": taux_occupation,
			"jours_occupes": jours_occupes,
			"total_jours": total_jours
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur calculate_appartement_stats: {str(e)}")
		return {
			"revenus_total": 0,
			"revenus_courte_duree": 0,
			"revenus_longue_duree": 0,
			"charges_total": 0,
			"benefice_net": 0,
			"taux_occupation": 0,
			"jours_occupes": 0,
			"total_jours": 365
		}