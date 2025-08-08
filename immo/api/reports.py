# Copyright (c) 2024, Frappe Technologies and Contributors
# See license.txt

import frappe
from frappe import _
from frappe.utils import nowdate, getdate, add_months, flt
from datetime import datetime, timedelta
import json


@frappe.whitelist()
def generate_financial_report(start_date=None, end_date=None, proprietaire_id=None, appartement_id=None):
	"""Génère un rapport financier complet"""
	try:
		if not start_date:
			start_date = f"{getdate().year}-01-01"
		if not end_date:
			end_date = nowdate()
		
		# Construction des filtres
		filters = []
		if proprietaire_id:
			filters.append(f"p.name = '{proprietaire_id}'")
		if appartement_id:
			filters.append(f"a.name = '{appartement_id}'")
		
		where_clause = " AND ".join(filters) if filters else "1=1"
		
		# Revenus des locations longue durée
		long_term_revenue = frappe.db.sql(f"""
			SELECT 
				a.name as appartement_id,
				a.adresse as appartement_adresse,
				p.nom_complet as proprietaire_nom,
				SUM(m.loyer_locataire) as total_loyer_locataire,
				SUM(m.loyer_proprietaire) as total_loyer_proprietaire,
				SUM(m.marge_mensuelle) as total_marge_mensuelle,
				SUM(m.marge_nette) as total_marge_nette,
				COUNT(m.name) as nombre_mensualites,
				AVG(m.marge_mensuelle) as marge_moyenne
			FROM `tabAppartement` a
			INNER JOIN `tabProprietaire` p ON a.proprietaire_id = p.name
			LEFT JOIN `tabLocation Longue Durée` lld ON a.name = lld.appartement_id
			LEFT JOIN `tabMensualite` m ON lld.name = m.location_longue_duree_id
			WHERE {where_clause}
				AND (m.creation IS NULL OR m.creation BETWEEN '{start_date}' AND '{end_date}')
	
			GROUP BY a.name, p.name
			ORDER BY total_marge_mensuelle DESC
		""", as_dict=True)
		
		# Revenus des locations courte durée
		short_term_revenue = frappe.db.sql(f"""
			SELECT 
				a.name as appartement_id,
				a.adresse as appartement_adresse,
				p.nom_complet as proprietaire_nom,
				SUM(lcd.total_locataire) as total_locataire,
				SUM(lcd.total_proprietaire) as total_proprietaire,
				SUM(lcd.marge_totale) as total_marge,
				SUM(lcd.marge_nette) as total_marge_nette,
				COUNT(lcd.name) as nombre_locations,
				SUM(lcd.nombre_nuits) as total_nuits,
				AVG(lcd.marge_par_nuit) as marge_moyenne_nuit
			FROM `tabAppartement` a
			INNER JOIN `tabProprietaire` p ON a.proprietaire_id = p.name
			LEFT JOIN `tabLocation Courte Duree` lcd ON a.name = lcd.appartement_id
			WHERE {where_clause}
				AND (lcd.date_debut IS NULL OR lcd.date_debut BETWEEN '{start_date}' AND '{end_date}')
	
			GROUP BY a.name, p.name
			ORDER BY total_marge DESC
		""", as_dict=True)
		
		# Charges par appartement
		charges_data = frappe.db.sql(f"""
			SELECT 
				a.name as appartement_id,
				a.adresse as appartement_adresse,
				SUM(ch.montant_total) as total_charges,
				SUM(ch.montant_locataire) as charges_locataire,
				SUM(ch.montant_proprietaire) as charges_proprietaire,
				COUNT(ch.name) as nombre_charges,
				AVG(ch.montant_total) as charge_moyenne
			FROM `tabAppartement` a
			INNER JOIN `tabProprietaire` p ON a.proprietaire_id = p.name
			LEFT JOIN `tabCharge` ch ON a.name = ch.appartement_id
			WHERE {where_clause}
				AND (ch.date_charge IS NULL OR ch.date_charge BETWEEN '{start_date}' AND '{end_date}')
	
			GROUP BY a.name
			ORDER BY total_charges DESC
		""", as_dict=True)
		
		# Commissions
		commissions_data = frappe.db.sql(f"""
			SELECT 
				a.name as appartement_id,
				a.adresse as appartement_adresse,
				SUM(c.montant_commission) as total_commissions,
				COUNT(c.name) as nombre_commissions,
				AVG(c.pourcentage_commission) as pourcentage_moyen,
				SUM(c.montant_commission) as commissions_payees
			FROM `tabAppartement` a
			INNER JOIN `tabProprietaire` p ON a.proprietaire_id = p.name
			LEFT JOIN `tabLocation Courte Duree` lcd ON a.name = lcd.appartement_id
			LEFT JOIN `tabCommission` c ON lcd.name = c.location_courte_duree_id
			WHERE {where_clause}
				AND (c.creation IS NULL OR c.creation BETWEEN '{start_date}' AND '{end_date}')
	
			GROUP BY a.name
			ORDER BY total_commissions DESC
		""", as_dict=True)
		
		# Compilation des données par appartement
		appartements_data = {}
		
		# Traitement des revenus longue durée
		for item in long_term_revenue:
			apt_id = item['appartement_id']
			if apt_id not in appartements_data:
				appartements_data[apt_id] = {
					'appartement_id': apt_id,
					'appartement_adresse': item['appartement_adresse'],
					'proprietaire_nom': item['proprietaire_nom'],
					'longue_duree': {},
					'courte_duree': {},
					'charges': {},
					'commissions': {}
				}
			
			appartements_data[apt_id]['longue_duree'] = {
				'total_loyer_locataire': item['total_loyer_locataire'] or 0,
				'total_loyer_proprietaire': item['total_loyer_proprietaire'] or 0,
				'total_marge_mensuelle': item['total_marge_mensuelle'] or 0,
				'total_marge_nette': item['total_marge_nette'] or 0,
				'nombre_mensualites': item['nombre_mensualites'] or 0,
				'marge_moyenne': item['marge_moyenne'] or 0
			}
		
		# Traitement des revenus courte durée
		for item in short_term_revenue:
			apt_id = item['appartement_id']
			if apt_id not in appartements_data:
				appartements_data[apt_id] = {
					'appartement_id': apt_id,
					'appartement_adresse': item['appartement_adresse'],
					'proprietaire_nom': item['proprietaire_nom'],
					'longue_duree': {},
					'courte_duree': {},
					'charges': {},
					'commissions': {}
				}
			
			appartements_data[apt_id]['courte_duree'] = {
				'total_locataire': item['total_locataire'] or 0,
				'total_proprietaire': item['total_proprietaire'] or 0,
				'total_marge': item['total_marge'] or 0,
				'total_marge_nette': item['total_marge_nette'] or 0,
				'nombre_locations': item['nombre_locations'] or 0,
				'total_nuits': item['total_nuits'] or 0,
				'marge_moyenne_nuit': item['marge_moyenne_nuit'] or 0
			}
		
		# Traitement des charges
		for item in charges_data:
			apt_id = item['appartement_id']
			if apt_id in appartements_data:
				appartements_data[apt_id]['charges'] = {
					'total_charges': item['total_charges'] or 0,
					'charges_locataire': item['charges_locataire'] or 0,
					'charges_proprietaire': item['charges_proprietaire'] or 0,
					'nombre_charges': item['nombre_charges'] or 0,
					'charge_moyenne': item['charge_moyenne'] or 0
				}
		
		# Traitement des commissions
		for item in commissions_data:
			apt_id = item['appartement_id']
			if apt_id in appartements_data:
				appartements_data[apt_id]['commissions'] = {
					'total_commissions': item['total_commissions'] or 0,
					'nombre_commissions': item['nombre_commissions'] or 0,
					'pourcentage_moyen': item['pourcentage_moyen'] or 0,
					'commissions_payees': item['commissions_payees'] or 0
				}
		
		# Calcul des totaux globaux
		totaux = {
			'total_revenus_locataire': 0,
			'total_revenus_proprietaire': 0,
			'total_marges_brutes': 0,
			'total_marges_nettes': 0,
			'total_charges': 0,
			'total_commissions': 0,
			'marge_finale': 0
		}
		
		for apt_data in appartements_data.values():
			# Revenus longue durée
			ld = apt_data.get('longue_duree', {})
			totaux['total_revenus_locataire'] += ld.get('total_loyer_locataire', 0)
			totaux['total_revenus_proprietaire'] += ld.get('total_loyer_proprietaire', 0)
			totaux['total_marges_brutes'] += ld.get('total_marge_mensuelle', 0)
			totaux['total_marges_nettes'] += ld.get('total_marge_nette', 0)
			
			# Revenus courte durée
			cd = apt_data.get('courte_duree', {})
			totaux['total_revenus_locataire'] += cd.get('total_locataire', 0)
			totaux['total_revenus_proprietaire'] += cd.get('total_proprietaire', 0)
			totaux['total_marges_brutes'] += cd.get('total_marge', 0)
			totaux['total_marges_nettes'] += cd.get('total_marge_nette', 0)
			
			# Charges et commissions
			totaux['total_charges'] += apt_data.get('charges', {}).get('total_charges', 0)
			totaux['total_commissions'] += apt_data.get('commissions', {}).get('total_commissions', 0)
		
		totaux['marge_finale'] = totaux['total_marges_nettes'] - totaux['total_commissions']
		
		return {
			"success": True,
			"periode": {
				"debut": start_date,
				"fin": end_date
			},
			"appartements": list(appartements_data.values()),
			"totaux": totaux,
			"nombre_appartements": len(appartements_data)
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur génération rapport financier: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def generate_occupancy_report(start_date=None, end_date=None, appartement_id=None):
	"""Génère un rapport de taux d'occupation"""
	try:
		if not start_date:
			start_date = f"{getdate().year}-01-01"
		if not end_date:
			end_date = nowdate()
		
		# Calcul de la période en jours
		start_dt = getdate(start_date)
		end_dt = getdate(end_date)
		total_days = (end_dt - start_dt).days + 1
		
		# Filtres
		filters = []
		if appartement_id:
			filters.append(f"a.name = '{appartement_id}'")
		
		where_clause = " AND ".join(filters) if filters else "1=1"
		
		# Occupation longue durée
		long_term_occupancy = frappe.db.sql(f"""
			SELECT 
				a.name as appartement_id,
				a.adresse as appartement_adresse,
				p.nom_complet as proprietaire_nom,
				COUNT(DISTINCT lld.name) as nombre_locations_longues,
				SUM(
					CASE 
						WHEN lld.date_fin IS NULL OR lld.date_fin > '{end_date}' THEN 
							DATEDIFF('{end_date}', GREATEST(lld.date_debut, '{start_date}')) + 1
						ELSE 
							DATEDIFF(LEAST(lld.date_fin, '{end_date}'), GREATEST(lld.date_debut, '{start_date}')) + 1
					END
				) as jours_occupation_longue
			FROM `tabAppartement` a
			INNER JOIN `tabProprietaire` p ON a.proprietaire_id = p.name
			LEFT JOIN `tabLocation Longue Durée` lld ON a.name = lld.appartement_id

				AND lld.date_debut <= '{end_date}'
				AND (lld.date_fin IS NULL OR lld.date_fin >= '{start_date}')
			WHERE {where_clause}
			GROUP BY a.name, p.name
		""", as_dict=True)
		
		# Occupation courte durée
		short_term_occupancy = frappe.db.sql(f"""
			SELECT 
				a.name as appartement_id,
				COUNT(lcd.name) as nombre_locations_courtes,
				SUM(lcd.nombre_nuits) as total_nuits_courtes,
				SUM(
					CASE 
						WHEN lcd.date_fin > '{end_date}' THEN 
							DATEDIFF('{end_date}', GREATEST(lcd.date_debut, '{start_date}')) + 1
						ELSE 
							DATEDIFF(LEAST(lcd.date_fin, '{end_date}'), GREATEST(lcd.date_debut, '{start_date}')) + 1
					END
				) as jours_occupation_courte
			FROM `tabAppartement` a
			LEFT JOIN `tabLocation Courte Duree` lcd ON a.name = lcd.appartement_id

				AND lcd.date_debut <= '{end_date}'
				AND lcd.date_fin >= '{start_date}'
			WHERE {where_clause}
			GROUP BY a.name
		""", as_dict=True)
		
		# Compilation des données
		occupancy_data = {}
		
		# Traitement occupation longue durée
		for item in long_term_occupancy:
			apt_id = item['appartement_id']
			occupancy_data[apt_id] = {
				'appartement_id': apt_id,
				'appartement_adresse': item['appartement_adresse'],
				'proprietaire_nom': item['proprietaire_nom'],
				'nombre_locations_longues': item['nombre_locations_longues'] or 0,
				'jours_occupation_longue': max(0, item['jours_occupation_longue'] or 0),
				'nombre_locations_courtes': 0,
				'jours_occupation_courte': 0,
				'total_nuits_courtes': 0
			}
		
		# Traitement occupation courte durée
		for item in short_term_occupancy:
			apt_id = item['appartement_id']
			if apt_id in occupancy_data:
				occupancy_data[apt_id]['nombre_locations_courtes'] = item['nombre_locations_courtes'] or 0
				occupancy_data[apt_id]['jours_occupation_courte'] = max(0, item['jours_occupation_courte'] or 0)
				occupancy_data[apt_id]['total_nuits_courtes'] = item['total_nuits_courtes'] or 0
		
		# Calcul des taux d'occupation
		for apt_data in occupancy_data.values():
			total_jours_occupation = apt_data['jours_occupation_longue'] + apt_data['jours_occupation_courte']
			apt_data['total_jours_occupation'] = total_jours_occupation
			apt_data['taux_occupation'] = (total_jours_occupation / total_days * 100) if total_days > 0 else 0
			apt_data['jours_libres'] = max(0, total_days - total_jours_occupation)
			apt_data['taux_liberte'] = (apt_data['jours_libres'] / total_days * 100) if total_days > 0 else 0
		
		# Calcul des moyennes globales
		total_appartements = len(occupancy_data)
		moyennes = {
			'taux_occupation_moyen': sum(apt['taux_occupation'] for apt in occupancy_data.values()) / total_appartements if total_appartements > 0 else 0,
			'jours_occupation_moyen': sum(apt['total_jours_occupation'] for apt in occupancy_data.values()) / total_appartements if total_appartements > 0 else 0,
			'nombre_locations_longues_total': sum(apt['nombre_locations_longues'] for apt in occupancy_data.values()),
			'nombre_locations_courtes_total': sum(apt['nombre_locations_courtes'] for apt in occupancy_data.values())
		}
		
		return {
			"success": True,
			"periode": {
				"debut": start_date,
				"fin": end_date,
				"total_jours": total_days
			},
			"appartements": list(occupancy_data.values()),
			"moyennes": moyennes,
			"nombre_appartements": total_appartements
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur génération rapport occupation: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def generate_commission_report(start_date=None, end_date=None, referent_id=None):
	"""Génère un rapport de commissions"""
	try:
		if not start_date:
			start_date = f"{getdate().year}-01-01"
		if not end_date:
			end_date = nowdate()
		
		# Filtres
		filters = []
		if referent_id:
			filters.append(f"r.name = '{referent_id}'")
		
		where_clause = " AND ".join(filters) if filters else "1=1"
		
		# Données des commissions
		commissions_data = frappe.db.sql(f"""
			SELECT 
				r.name as referent_id,
				r.nom_complet as referent_nom,
				r.email as referent_email,
				r.telephone as referent_telephone,
				COUNT(c.name) as nombre_commissions,
				SUM(c.montant_commission) as total_commissions,
				SUM(c.montant_commission) as commissions_payees,
			SUM(c.montant_commission) as commissions_en_attente,
			SUM(c.montant_commission) as commissions_rejetees,
				AVG(c.pourcentage_commission) as pourcentage_moyen,
				COUNT(DISTINCT lcd.name) as nombre_locations_referees,
				COUNT(DISTINCT a.name) as nombre_appartements_referes,
				SUM(lcd.marge_totale) as marge_totale_generee,
				SUM(lcd.marge_nette) as marge_nette_generee
			FROM `tabReferent` r
			LEFT JOIN `tabCommission` c ON r.name = c.referent_id
			LEFT JOIN `tabLocation Courte Duree` lcd ON c.location_courte_duree_id = lcd.name
			LEFT JOIN `tabAppartement` a ON lcd.appartement_id = a.name
			WHERE {where_clause}
				AND (c.creation IS NULL OR c.creation BETWEEN '{start_date}' AND '{end_date}')
	
			GROUP BY r.name
			ORDER BY total_commissions DESC
		""", as_dict=True)
		
		# Détail des commissions par référent
		detailed_commissions = frappe.db.sql(f"""
			SELECT 
				c.name as commission_id,
				c.referent_id,
				c.montant_commission,
				c.pourcentage_commission,
				1 as commission_statut,
				c.date_paiement as commission_date_paiement,
				c.creation as commission_creation,
				lcd.name as location_id,
				lcd.date_debut,
				lcd.date_fin,
				lcd.marge_totale,
				lcd.marge_nette,
				a.adresse as appartement_adresse,
				p.nom_complet as proprietaire_nom
			FROM `tabCommission` c
			INNER JOIN `tabReferent` r ON c.referent_id = r.name
			INNER JOIN `tabLocation Courte Duree` lcd ON c.location_courte_duree_id = lcd.name
			INNER JOIN `tabAppartement` a ON lcd.appartement_id = a.name
			INNER JOIN `tabProprietaire` p ON a.proprietaire_id = p.name
			WHERE {where_clause}
				AND c.creation BETWEEN '{start_date}' AND '{end_date}'
	
			ORDER BY r.name, c.creation DESC
		""", as_dict=True)
		
		# Organisation des détails par référent
		referents_details = {}
		for commission in detailed_commissions:
			referent_id = commission['referent_id']
			if referent_id not in referents_details:
				referents_details[referent_id] = []
			referents_details[referent_id].append(commission)
		
		# Ajout des détails aux données des référents
		for referent in commissions_data:
			referent_id = referent['referent_id']
			referent['commissions_detail'] = referents_details.get(referent_id, [])
			
			# Calcul des taux
			total_commissions = referent['nombre_commissions'] or 0
			referent['taux_paiement'] = (referent['commissions_payees'] / referent['total_commissions'] * 100) if referent['total_commissions'] > 0 else 0
			referent['taux_rejet'] = (referent['commissions_rejetees'] / referent['total_commissions'] * 100) if referent['total_commissions'] > 0 else 0
			referent['efficacite'] = (referent['marge_totale_generee'] / referent['nombre_locations_referees']) if referent['nombre_locations_referees'] > 0 else 0
		
		# Calcul des totaux globaux
		totaux = {
			'nombre_referents': len(commissions_data),
			'total_commissions_globales': sum(r['total_commissions'] or 0 for r in commissions_data),
			'total_commissions_payees': sum(r['commissions_payees'] or 0 for r in commissions_data),
			'total_commissions_en_attente': sum(r['commissions_en_attente'] or 0 for r in commissions_data),
			'total_locations_referees': sum(r['nombre_locations_referees'] or 0 for r in commissions_data),
			'total_marge_generee': sum(r['marge_totale_generee'] or 0 for r in commissions_data),
			'pourcentage_moyen_global': sum(r['pourcentage_moyen'] or 0 for r in commissions_data) / len(commissions_data) if commissions_data else 0
		}
		
		return {
			"success": True,
			"periode": {
				"debut": start_date,
				"fin": end_date
			},
			"referents": commissions_data,
			"totaux": totaux
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur génération rapport commissions: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def generate_charges_report(start_date=None, end_date=None, appartement_id=None, type_charge=None):
	"""Génère un rapport de charges"""
	try:
		if not start_date:
			start_date = f"{getdate().year}-01-01"
		if not end_date:
			end_date = nowdate()
		
		# Filtres
		filters = []
		if appartement_id:
			filters.append(f"a.name = '{appartement_id}'")
		if type_charge:
			filters.append(f"ch.type_charge = '{type_charge}'")
		
		where_clause = " AND ".join(filters) if filters else "1=1"
		
		# Données des charges par appartement
		charges_by_apartment = frappe.db.sql(f"""
			SELECT 
				a.name as appartement_id,
				a.adresse as appartement_adresse,
				p.nom_complet as proprietaire_nom,
				ch.type_charge,
				COUNT(ch.name) as nombre_charges,
				SUM(ch.montant_total) as total_charges,
				SUM(ch.montant_locataire) as total_charges_locataire,
				SUM(ch.montant_proprietaire) as total_charges_proprietaire,
				AVG(ch.montant_total) as charge_moyenne,
				COUNT(CASE WHEN ch.statut = 'Validée' THEN 1 END) as charges_validees,
				COUNT(CASE WHEN ch.statut = 'Payée' THEN 1 END) as charges_payees,
				COUNT(CASE WHEN ch.statut = 'Remboursée' THEN 1 END) as charges_remboursees
			FROM `tabAppartement` a
			INNER JOIN `tabProprietaire` p ON a.proprietaire_id = p.name
			LEFT JOIN `tabCharge` ch ON a.name = ch.appartement_id
			WHERE {where_clause}
				AND (ch.date_charge IS NULL OR ch.date_charge BETWEEN '{start_date}' AND '{end_date}')
	
			GROUP BY a.name, ch.type_charge
			ORDER BY a.adresse, ch.type_charge
		""", as_dict=True)
		
		# Données des charges par type
		charges_by_type = frappe.db.sql(f"""
			SELECT 
				ch.type_charge,
				COUNT(ch.name) as nombre_charges,
				SUM(ch.montant_total) as total_montant,
				SUM(ch.montant_locataire) as total_locataire,
				SUM(ch.montant_proprietaire) as total_proprietaire,
				AVG(ch.montant_total) as montant_moyen,
				COUNT(DISTINCT ch.appartement_id) as appartements_concernes
			FROM `tabCharge` ch
			INNER JOIN `tabAppartement` a ON ch.appartement_id = a.name
			INNER JOIN `tabProprietaire` p ON a.proprietaire_id = p.name
			WHERE {where_clause}
				AND ch.date_charge BETWEEN '{start_date}' AND '{end_date}'
	
			GROUP BY ch.type_charge
			ORDER BY total_montant DESC
		""", as_dict=True)
		
		# Évolution mensuelle des charges
		monthly_evolution = frappe.db.sql(f"""
			SELECT 
				DATE_FORMAT(ch.date_charge, '%Y-%m') as mois,
				COUNT(ch.name) as nombre_charges,
				SUM(ch.montant_total) as total_montant,
				AVG(ch.montant_total) as montant_moyen
			FROM `tabCharge` ch
			INNER JOIN `tabAppartement` a ON ch.appartement_id = a.name
			INNER JOIN `tabProprietaire` p ON a.proprietaire_id = p.name
			WHERE {where_clause}
				AND ch.date_charge BETWEEN '{start_date}' AND '{end_date}'
			GROUP BY DATE_FORMAT(ch.date_charge, '%Y-%m')
			ORDER BY mois
		""", as_dict=True)
		
		# Organisation des données par appartement
		appartements_charges = {}
		for charge in charges_by_apartment:
			apt_id = charge['appartement_id']
			if apt_id not in appartements_charges:
				appartements_charges[apt_id] = {
					'appartement_id': apt_id,
					'appartement_adresse': charge['appartement_adresse'],
					'proprietaire_nom': charge['proprietaire_nom'],
					'charges_par_type': {},
					'total_charges': 0,
					'total_charges_locataire': 0,
					'total_charges_proprietaire': 0,
					'nombre_total_charges': 0
				}
			
			type_charge = charge['type_charge'] or 'Non spécifié'
			appartements_charges[apt_id]['charges_par_type'][type_charge] = {
				'nombre_charges': charge['nombre_charges'] or 0,
				'total_charges': charge['total_charges'] or 0,
				'total_charges_locataire': charge['total_charges_locataire'] or 0,
				'total_charges_proprietaire': charge['total_charges_proprietaire'] or 0,
				'charge_moyenne': charge['charge_moyenne'] or 0,
				'charges_validees': charge['charges_validees'] or 0,
				'charges_payees': charge['charges_payees'] or 0,
				'charges_remboursees': charge['charges_remboursees'] or 0
			}
			
			# Mise à jour des totaux
			appartements_charges[apt_id]['total_charges'] += charge['total_charges'] or 0
			appartements_charges[apt_id]['total_charges_locataire'] += charge['total_charges_locataire'] or 0
			appartements_charges[apt_id]['total_charges_proprietaire'] += charge['total_charges_proprietaire'] or 0
			appartements_charges[apt_id]['nombre_total_charges'] += charge['nombre_charges'] or 0
		
		# Calcul des totaux globaux
		totaux = {
			'nombre_appartements': len(appartements_charges),
			'total_charges_globales': sum(apt['total_charges'] for apt in appartements_charges.values()),
			'total_charges_locataire_globales': sum(apt['total_charges_locataire'] for apt in appartements_charges.values()),
			'total_charges_proprietaire_globales': sum(apt['total_charges_proprietaire'] for apt in appartements_charges.values()),
			'nombre_total_charges': sum(apt['nombre_total_charges'] for apt in appartements_charges.values()),
			'charge_moyenne_globale': sum(apt['total_charges'] for apt in appartements_charges.values()) / sum(apt['nombre_total_charges'] for apt in appartements_charges.values()) if sum(apt['nombre_total_charges'] for apt in appartements_charges.values()) > 0 else 0
		}
		
		return {
			"success": True,
			"periode": {
				"debut": start_date,
				"fin": end_date
			},
			"appartements": list(appartements_charges.values()),
			"charges_par_type": charges_by_type,
			"evolution_mensuelle": monthly_evolution,
			"totaux": totaux
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur génération rapport charges: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def export_report_to_excel(report_type, report_data, filename=None):
	"""Exporte un rapport vers Excel"""
	try:
		import xlsxwriter
		import io
		import base64
		
		if not filename:
			filename = f"rapport_{report_type}_{nowdate()}.xlsx"
		
		# Création du fichier Excel en mémoire
		output = io.BytesIO()
		workbook = xlsxwriter.Workbook(output, {'in_memory': True})
		
		# Styles
		header_format = workbook.add_format({
			'bold': True,
			'bg_color': '#D7E4BC',
			'border': 1
		})
		
		number_format = workbook.add_format({'num_format': '#,##0.00'})
		percent_format = workbook.add_format({'num_format': '0.00%'})
		
		if report_type == "financial":
			# Feuille principale
			worksheet = workbook.add_worksheet('Rapport Financier')
			
			# En-têtes
			headers = ['Appartement', 'Proprietaire', 'Revenus Locataire', 'Revenus Propriétaire', 
					  'Marge Brute', 'Marge Nette', 'Charges', 'Commissions', 'Marge Finale']
			
			for col, header in enumerate(headers):
				worksheet.write(0, col, header, header_format)
			
			# Données
			row = 1
			for apt in report_data.get('appartements', []):
				worksheet.write(row, 0, apt.get('appartement_adresse', ''))
				worksheet.write(row, 1, apt.get('proprietaire_nom', ''))
				
				# Calcul des revenus totaux
				ld = apt.get('longue_duree', {})
				cd = apt.get('courte_duree', {})
				
				revenu_locataire = (ld.get('total_loyer_locataire', 0) + cd.get('total_locataire', 0))
				revenu_proprietaire = (ld.get('total_loyer_proprietaire', 0) + cd.get('total_proprietaire', 0))
				marge_brute = (ld.get('total_marge_mensuelle', 0) + cd.get('total_marge', 0))
				marge_nette = (ld.get('total_marge_nette', 0) + cd.get('total_marge_nette', 0))
				charges = apt.get('charges', {}).get('total_charges', 0)
				commissions = apt.get('commissions', {}).get('total_commissions', 0)
				marge_finale = marge_nette - commissions
				
				worksheet.write(row, 2, revenu_locataire, number_format)
				worksheet.write(row, 3, revenu_proprietaire, number_format)
				worksheet.write(row, 4, marge_brute, number_format)
				worksheet.write(row, 5, marge_nette, number_format)
				worksheet.write(row, 6, charges, number_format)
				worksheet.write(row, 7, commissions, number_format)
				worksheet.write(row, 8, marge_finale, number_format)
				
				row += 1
		
		elif report_type == "occupancy":
			worksheet = workbook.add_worksheet('Taux Occupation')
			
			headers = ['Appartement', 'Proprietaire', 'Jours Occupation LD', 'Jours Occupation CD', 
					  'Total Jours Occupation', 'Taux Occupation %', 'Jours Libres']
			
			for col, header in enumerate(headers):
				worksheet.write(0, col, header, header_format)
			
			row = 1
			for apt in report_data.get('appartements', []):
				worksheet.write(row, 0, apt.get('appartement_adresse', ''))
				worksheet.write(row, 1, apt.get('proprietaire_nom', ''))
				worksheet.write(row, 2, apt.get('jours_occupation_longue', 0))
				worksheet.write(row, 3, apt.get('jours_occupation_courte', 0))
				worksheet.write(row, 4, apt.get('total_jours_occupation', 0))
				worksheet.write(row, 5, apt.get('taux_occupation', 0) / 100, percent_format)
				worksheet.write(row, 6, apt.get('jours_libres', 0))
				row += 1
		
		workbook.close()
		output.seek(0)
		
		# Encodage en base64 pour le retour
		excel_data = base64.b64encode(output.read()).decode('utf-8')
		
		return {
			"success": True,
			"filename": filename,
			"data": excel_data,
			"content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur export Excel: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}