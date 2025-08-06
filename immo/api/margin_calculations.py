# Copyright (c) 2024, Frappe Technologies and Contributors
# See license.txt

import frappe
from frappe import _
from frappe.utils import nowdate, getdate, add_months, flt
from datetime import datetime, timedelta


@frappe.whitelist()
def calculate_location_longue_duree_margin(loyer_locataire, loyer_proprietaire, charges_mensuelles=0):
	"""Calcule la marge pour une location longue durée"""
	try:
		loyer_locataire = flt(loyer_locataire)
		loyer_proprietaire = flt(loyer_proprietaire)
		charges_mensuelles = flt(charges_mensuelles)
		
		# Validation des montants
		if loyer_locataire <= 0 or loyer_proprietaire <= 0:
			frappe.throw(_("Les loyers doivent être positifs"))
		
		if loyer_locataire < loyer_proprietaire:
			frappe.throw(_("Le loyer locataire ne peut pas être inférieur au loyer propriétaire"))
		
		# Calcul de la marge
		marge_brute = loyer_locataire - loyer_proprietaire
		marge_nette = marge_brute - charges_mensuelles
		pourcentage_marge = (marge_brute / loyer_locataire * 100) if loyer_locataire > 0 else 0
		pourcentage_marge_nette = (marge_nette / loyer_locataire * 100) if loyer_locataire > 0 else 0
		
		return {
			"success": True,
			"marge_brute": marge_brute,
			"marge_nette": marge_nette,
			"pourcentage_marge": pourcentage_marge,
			"pourcentage_marge_nette": pourcentage_marge_nette,
			"loyer_locataire": loyer_locataire,
			"loyer_proprietaire": loyer_proprietaire,
			"charges_mensuelles": charges_mensuelles
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur calcul marge location longue durée: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def calculate_location_courte_duree_margin(prix_locataire_nuit, prix_proprietaire_nuit, nombre_nuits, charges_sejour=0):
	"""Calcule la marge pour une location courte durée"""
	try:
		prix_locataire_nuit = flt(prix_locataire_nuit)
		prix_proprietaire_nuit = flt(prix_proprietaire_nuit)
		nombre_nuits = int(nombre_nuits)
		charges_sejour = flt(charges_sejour)
		
		# Validation des montants
		if prix_locataire_nuit <= 0 or prix_proprietaire_nuit <= 0:
			frappe.throw(_("Les prix par nuit doivent être positifs"))
		
		if nombre_nuits <= 0:
			frappe.throw(_("Le nombre de nuits doit être positif"))
		
		if prix_locataire_nuit < prix_proprietaire_nuit:
			frappe.throw(_("Le prix locataire ne peut pas être inférieur au prix propriétaire"))
		
		# Calculs
		total_locataire = prix_locataire_nuit * nombre_nuits
		total_proprietaire = prix_proprietaire_nuit * nombre_nuits
		marge_brute = total_locataire - total_proprietaire
		marge_nette = marge_brute - charges_sejour
		marge_par_nuit = marge_brute / nombre_nuits if nombre_nuits > 0 else 0
		pourcentage_marge = (marge_brute / total_locataire * 100) if total_locataire > 0 else 0
		pourcentage_marge_nette = (marge_nette / total_locataire * 100) if total_locataire > 0 else 0
		
		return {
			"success": True,
			"total_locataire": total_locataire,
			"total_proprietaire": total_proprietaire,
			"marge_brute": marge_brute,
			"marge_nette": marge_nette,
			"marge_par_nuit": marge_par_nuit,
			"pourcentage_marge": pourcentage_marge,
			"pourcentage_marge_nette": pourcentage_marge_nette,
			"nombre_nuits": nombre_nuits,
			"charges_sejour": charges_sejour
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur calcul marge location courte durée: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def calculate_commission_amount(marge_totale, pourcentage_commission):
	"""Calcule le montant de commission"""
	try:
		marge_totale = flt(marge_totale)
		pourcentage_commission = flt(pourcentage_commission)
		
		# Validation
		if marge_totale < 0:
			frappe.throw(_("La marge totale ne peut pas être négative"))
		
		if pourcentage_commission < 0 or pourcentage_commission > 100:
			frappe.throw(_("Le pourcentage de commission doit être entre 0 et 100"))
		
		# Calculs
		montant_commission = marge_totale * pourcentage_commission / 100
		marge_nette_apres_commission = marge_totale - montant_commission
		
		return {
			"success": True,
			"marge_totale": marge_totale,
			"pourcentage_commission": pourcentage_commission,
			"montant_commission": montant_commission,
			"marge_nette_apres_commission": marge_nette_apres_commission
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur calcul commission: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_apartment_margin_summary(appartement_id, start_date=None, end_date=None):
	"""Récupère un résumé des marges pour un appartement"""
	try:
		if not start_date:
			start_date = f"{getdate().year}-01-01"
		if not end_date:
			end_date = nowdate()
		
		# Vérification de l'existence de l'appartement
		if not frappe.db.exists("Appartement", appartement_id):
			frappe.throw(_("Appartement non trouvé"))
		
		# Marges des locations longue durée
		long_term_margins = frappe.db.sql("""
			SELECT 
				SUM(m.marge_mensuelle) as total_marge_mensuelle,
				SUM(m.marge_nette) as total_marge_nette,
				COUNT(m.name) as nombre_mensualites,
				AVG(m.marge_mensuelle) as marge_moyenne_mensuelle
			FROM `tabMensualité` m
			INNER JOIN `tabLocation Longue Durée` lld ON m.location_longue_duree_id = lld.name
			WHERE lld.appartement_id = %s
				AND m.creation BETWEEN %s AND %s
				AND m.docstatus != 2
		""", (appartement_id, start_date, end_date), as_dict=True)
		
		# Marges des locations courte durée
		short_term_margins = frappe.db.sql("""
			SELECT 
				SUM(lcd.marge_totale) as total_marge_courte_duree,
				SUM(lcd.marge_nette) as total_marge_nette_courte_duree,
				COUNT(lcd.name) as nombre_locations_courtes,
				AVG(lcd.marge_par_nuit) as marge_moyenne_par_nuit
			FROM `tabLocation Courte Durée` lcd
			WHERE lcd.appartement_id = %s
				AND lcd.date_debut BETWEEN %s AND %s
				AND lcd.docstatus != 2
		""", (appartement_id, start_date, end_date), as_dict=True)
		
		# Commissions
		commissions = frappe.db.sql("""
			SELECT 
				SUM(c.montant_commission) as total_commissions,
				COUNT(c.name) as nombre_commissions,
				AVG(c.pourcentage_commission) as pourcentage_moyen_commission
			FROM `tabCommission` c
			INNER JOIN `tabLocation Courte Durée` lcd ON c.location_courte_duree_id = lcd.name
			WHERE lcd.appartement_id = %s
				AND c.creation BETWEEN %s AND %s
				AND c.docstatus != 2
		""", (appartement_id, start_date, end_date), as_dict=True)
		
		# Charges
		charges = frappe.db.sql("""
			SELECT 
				SUM(ch.montant_total) as total_charges,
				SUM(ch.montant_locataire) as charges_locataire,
				SUM(ch.montant_proprietaire) as charges_proprietaire,
				COUNT(ch.name) as nombre_charges
			FROM `tabCharge` ch
			WHERE ch.appartement_id = %s
				AND ch.date_charge BETWEEN %s AND %s
				AND ch.docstatus != 2
		""", (appartement_id, start_date, end_date), as_dict=True)
		
		# Compilation des résultats
		long_term = long_term_margins[0] if long_term_margins else {}
		short_term = short_term_margins[0] if short_term_margins else {}
		commission_data = commissions[0] if commissions else {}
		charge_data = charges[0] if charges else {}
		
		total_marge_brute = (long_term.get('total_marge_mensuelle', 0) or 0) + (short_term.get('total_marge_courte_duree', 0) or 0)
		total_marge_nette = (long_term.get('total_marge_nette', 0) or 0) + (short_term.get('total_marge_nette_courte_duree', 0) or 0)
		total_commissions = commission_data.get('total_commissions', 0) or 0
		total_charges = charge_data.get('total_charges', 0) or 0
		
		marge_finale = total_marge_nette - total_commissions
		
		return {
			"success": True,
			"appartement_id": appartement_id,
			"periode": {
				"debut": start_date,
				"fin": end_date
			},
			"locations_longue_duree": {
				"total_marge_mensuelle": long_term.get('total_marge_mensuelle', 0) or 0,
				"total_marge_nette": long_term.get('total_marge_nette', 0) or 0,
				"nombre_mensualites": long_term.get('nombre_mensualites', 0) or 0,
				"marge_moyenne_mensuelle": long_term.get('marge_moyenne_mensuelle', 0) or 0
			},
			"locations_courte_duree": {
				"total_marge": short_term.get('total_marge_courte_duree', 0) or 0,
				"total_marge_nette": short_term.get('total_marge_nette_courte_duree', 0) or 0,
				"nombre_locations": short_term.get('nombre_locations_courtes', 0) or 0,
				"marge_moyenne_par_nuit": short_term.get('marge_moyenne_par_nuit', 0) or 0
			},
			"commissions": {
				"total_commissions": total_commissions,
				"nombre_commissions": commission_data.get('nombre_commissions', 0) or 0,
				"pourcentage_moyen": commission_data.get('pourcentage_moyen_commission', 0) or 0
			},
			"charges": {
				"total_charges": total_charges,
				"charges_locataire": charge_data.get('charges_locataire', 0) or 0,
				"charges_proprietaire": charge_data.get('charges_proprietaire', 0) or 0,
				"nombre_charges": charge_data.get('nombre_charges', 0) or 0
			},
			"resume": {
				"total_marge_brute": total_marge_brute,
				"total_marge_nette": total_marge_nette,
				"total_commissions": total_commissions,
				"marge_finale": marge_finale
			}
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur résumé marges appartement: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_proprietaire_margin_summary(proprietaire_id, start_date=None, end_date=None):
	"""Récupère un résumé des marges pour un propriétaire"""
	try:
		if not start_date:
			start_date = f"{getdate().year}-01-01"
		if not end_date:
			end_date = nowdate()
		
		# Vérification de l'existence du propriétaire
		if not frappe.db.exists("Propriétaire", proprietaire_id):
			frappe.throw(_("Propriétaire non trouvé"))
		
		# Récupère tous les appartements du propriétaire
		appartements = frappe.get_all("Appartement", 
			filters={"proprietaire_id": proprietaire_id}, 
			fields=["name", "adresse"])
		
		total_summary = {
			"total_marge_brute": 0,
			"total_marge_nette": 0,
			"total_commissions": 0,
			"marge_finale": 0,
			"nombre_appartements": len(appartements),
			"appartements": []
		}
		
		for appartement in appartements:
			# Récupère le résumé pour chaque appartement
			apt_summary = get_apartment_margin_summary(appartement.name, start_date, end_date)
			
			if apt_summary.get("success"):
				resum = apt_summary["resume"]
				total_summary["total_marge_brute"] += resum["total_marge_brute"]
				total_summary["total_marge_nette"] += resum["total_marge_nette"]
				total_summary["total_commissions"] += resum["total_commissions"]
				total_summary["marge_finale"] += resum["marge_finale"]
				
				total_summary["appartements"].append({
					"appartement_id": appartement.name,
					"adresse": appartement.adresse,
					"marge_brute": resum["total_marge_brute"],
					"marge_nette": resum["total_marge_nette"],
					"commissions": resum["total_commissions"],
					"marge_finale": resum["marge_finale"]
				})
		
		return {
			"success": True,
			"proprietaire_id": proprietaire_id,
			"periode": {
				"debut": start_date,
				"fin": end_date
			},
			"resume": total_summary
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur résumé marges propriétaire: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def simulate_pricing_scenario(appartement_id, scenario_data):
	"""Simule différents scénarios de tarification"""
	try:
		# Vérification de l'existence de l'appartement
		if not frappe.db.exists("Appartement", appartement_id):
			frappe.throw(_("Appartement non trouvé"))
		
		scenarios = []
		
		for scenario in scenario_data:
			scenario_name = scenario.get("name", "Scénario")
			type_location = scenario.get("type_location", "longue_duree")
			
			if type_location == "longue_duree":
				result = calculate_location_longue_duree_margin(
					scenario.get("loyer_locataire", 0),
					scenario.get("loyer_proprietaire", 0),
					scenario.get("charges_mensuelles", 0)
				)
			else:
				result = calculate_location_courte_duree_margin(
					scenario.get("prix_locataire_nuit", 0),
					scenario.get("prix_proprietaire_nuit", 0),
					scenario.get("nombre_nuits", 1),
					scenario.get("charges_sejour", 0)
				)
			
			if result.get("success"):
				scenarios.append({
					"name": scenario_name,
					"type_location": type_location,
					"result": result
				})
		
		return {
			"success": True,
			"appartement_id": appartement_id,
			"scenarios": scenarios
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur simulation tarification: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_margin_trends(appartement_id=None, proprietaire_id=None, months=12):
	"""Récupère les tendances de marges sur plusieurs mois"""
	try:
		months = int(months)
		if months <= 0 or months > 24:
			frappe.throw(_("Le nombre de mois doit être entre 1 et 24"))
		
		# Calcule les dates de début et fin
		end_date = getdate()
		start_date = add_months(end_date, -months)
		
		trends = []
		
		# Génère les données pour chaque mois
		for i in range(months):
			month_start = add_months(start_date, i)
			month_end = add_months(month_start, 1) - timedelta(days=1)
			
			if appartement_id:
				summary = get_apartment_margin_summary(appartement_id, month_start, month_end)
			elif proprietaire_id:
				summary = get_proprietaire_margin_summary(proprietaire_id, month_start, month_end)
			else:
				frappe.throw(_("Appartement ID ou Propriétaire ID requis"))
			
			if summary.get("success"):
				if appartement_id:
					resum = summary["resume"]
				else:
					resum = summary["resume"]
				
				trends.append({
					"mois": month_start.strftime("%Y-%m"),
					"marge_brute": resum["total_marge_brute"],
					"marge_nette": resum["total_marge_nette"],
					"commissions": resum["total_commissions"],
					"marge_finale": resum["marge_finale"]
				})
		
		return {
			"success": True,
			"appartement_id": appartement_id,
			"proprietaire_id": proprietaire_id,
			"periode_mois": months,
			"trends": trends
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur tendances marges: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}