# Copyright (c) 2024, Frappe Technologies and Contributors
# See license.txt

import frappe
from frappe import _
from frappe.utils import nowdate, getdate, add_months, flt, cint
from datetime import datetime, timedelta
import json


@frappe.whitelist()
def get_dashboard_statistics(proprietaire_id=None, period="current_month"):
	"""Récupère les statistiques pour le tableau de bord"""
	try:
		# Calcul des dates selon la période
		if period == "current_month":
			start_date = f"{getdate().year}-{getdate().month:02d}-01"
			end_date = nowdate()
		elif period == "last_month":
			last_month_date = add_months(getdate(), -1)
			start_date = f"{last_month_date.year}-{last_month_date.month:02d}-01"
			end_date = f"{last_month_date.year}-{last_month_date.month:02d}-31"
		elif period == "current_year":
			start_date = f"{getdate().year}-01-01"
			end_date = nowdate()
		else:
			start_date = f"{getdate().year}-01-01"
			end_date = nowdate()
		
		# Filtres pour propriétaire spécifique
		owner_filter = ""
		if proprietaire_id:
			owner_filter = f"AND p.name = '{proprietaire_id}'"
		
		# 1. Statistiques générales
		general_stats = frappe.db.sql(f"""
			SELECT 
				COUNT(DISTINCT p.name) as total_proprietaires,
				COUNT(DISTINCT a.name) as total_appartements,
				COUNT(DISTINCT lld.name) as total_locations_longues,
				COUNT(DISTINCT lcd.name) as total_locations_courtes,
				COUNT(DISTINCT r.name) as total_referents
			FROM `tabProprietaire` p
			LEFT JOIN `tabAppartement` a ON p.name = a.proprietaire_id
			LEFT JOIN `tabLocation Longue Durée` lld ON a.name = lld.appartement_id
			LEFT JOIN `tabLocation Courte Duree` lcd ON a.name = lcd.appartement_id
			LEFT JOIN `tabReferent` r ON r.actif = 1
			WHERE 1=1 {owner_filter}
		""", as_dict=True)[0]
		
		# 2. Revenus et marges
		revenue_stats = frappe.db.sql(f"""
			SELECT 
				-- Revenus longue durée
				SUM(CASE WHEN m.date_echeance BETWEEN '{start_date}' AND '{end_date}' 
						 THEN m.loyer_locataire ELSE 0 END) as revenus_ld_locataire,
				SUM(CASE WHEN m.date_echeance BETWEEN '{start_date}' AND '{end_date}' 
						 THEN m.loyer_proprietaire ELSE 0 END) as revenus_ld_proprietaire,
				SUM(CASE WHEN m.date_echeance BETWEEN '{start_date}' AND '{end_date}' 
						 THEN m.marge_mensuelle ELSE 0 END) as marge_ld,
				
				-- Revenus courte durée
				SUM(CASE WHEN lcd.date_debut BETWEEN '{start_date}' AND '{end_date}' 
						 THEN lcd.total_locataire ELSE 0 END) as revenus_cd_locataire,
				SUM(CASE WHEN lcd.date_debut BETWEEN '{start_date}' AND '{end_date}' 
						 THEN lcd.total_proprietaire ELSE 0 END) as revenus_cd_proprietaire,
				SUM(CASE WHEN lcd.date_debut BETWEEN '{start_date}' AND '{end_date}' 
						 THEN lcd.marge_totale ELSE 0 END) as marge_cd,
				
				-- Charges
				SUM(CASE WHEN ch.date_charge BETWEEN '{start_date}' AND '{end_date}' 
						 THEN ch.montant_total ELSE 0 END) as total_charges,
				
				-- Commissions
				SUM(CASE WHEN c.creation BETWEEN '{start_date}' AND '{end_date}' 
						 THEN c.montant_commission ELSE 0 END) as total_commissions
			FROM `tabProprietaire` p
			LEFT JOIN `tabAppartement` a ON p.name = a.proprietaire_id
			LEFT JOIN `tabLocation Longue Durée` lld ON a.name = lld.appartement_id
			LEFT JOIN `tabMensualite` m ON lld.name = m.location_longue_duree_id
			LEFT JOIN `tabLocation Courte Duree` lcd ON a.name = lcd.appartement_id
			LEFT JOIN `tabCharge` ch ON a.name = ch.appartement_id
			LEFT JOIN `tabCommission` c ON lcd.name = c.location_courte_duree_id
			WHERE 1=1 {owner_filter}
		""", as_dict=True)[0]
		
		# 3. Statistiques de paiement
		payment_stats = frappe.db.sql(f"""
			SELECT 
				-- Paiements locataires
				COUNT(CASE WHEN pl.statut = 'Confirmé' AND pl.creation BETWEEN '{start_date}' AND '{end_date}' 
						   THEN 1 END) as paiements_locataires_confirmes,
				COUNT(CASE WHEN pl.statut = 'En attente' AND pl.creation BETWEEN '{start_date}' AND '{end_date}' 
						   THEN 1 END) as paiements_locataires_en_attente,
				SUM(CASE WHEN pl.statut = 'Confirmé' AND pl.creation BETWEEN '{start_date}' AND '{end_date}' 
						 THEN pl.montant_total ELSE 0 END) as montant_locataires_confirme,
				
				-- Paiements propriétaires
				COUNT(CASE WHEN pp.statut = 'Payé' AND pp.creation BETWEEN '{start_date}' AND '{end_date}' 
						   THEN 1 END) as paiements_proprietaires_payes,
				COUNT(CASE WHEN pp.statut = 'En attente' AND pp.creation BETWEEN '{start_date}' AND '{end_date}' 
						   THEN 1 END) as paiements_proprietaires_en_attente,
				SUM(CASE WHEN pp.statut = 'Payé' AND pp.creation BETWEEN '{start_date}' AND '{end_date}' 
						 THEN pp.montant_net ELSE 0 END) as montant_proprietaires_paye
			FROM `tabProprietaire` p
			LEFT JOIN `tabAppartement` a ON p.name = a.proprietaire_id
			LEFT JOIN `tabPaiement Locataire` pl ON a.name = pl.appartement_id
			LEFT JOIN `tabPaiement Propriétaire` pp ON a.name = pp.appartement_id
			WHERE 1=1 {owner_filter}
		""", as_dict=True)[0]
		
		# 4. Taux d'occupation
		occupancy_stats = frappe.db.sql(f"""
			SELECT 
				COUNT(DISTINCT CASE WHEN lld.statut = 'Actif' THEN a.name END) as appartements_loues_ld,
				COUNT(DISTINCT CASE WHEN lcd.statut IN ('Confirmé', 'En cours') 
										 AND lcd.date_debut <= '{end_date}' 
										 AND lcd.date_fin >= '{start_date}' 
										 THEN a.name END) as appartements_loues_cd,
				AVG(CASE WHEN lcd.date_debut BETWEEN '{start_date}' AND '{end_date}' 
						 THEN lcd.nombre_nuits END) as duree_moyenne_cd
			FROM `tabProprietaire` p
			LEFT JOIN `tabAppartement` a ON p.name = a.proprietaire_id
			LEFT JOIN `tabLocation Longue Durée` lld ON a.name = lld.appartement_id
			LEFT JOIN `tabLocation Courte Duree` lcd ON a.name = lcd.appartement_id
			WHERE 1=1 {owner_filter}
		""", as_dict=True)[0]
		
		# Calculs dérivés
		total_revenus_locataire = (revenue_stats['revenus_ld_locataire'] or 0) + (revenue_stats['revenus_cd_locataire'] or 0)
		total_revenus_proprietaire = (revenue_stats['revenus_ld_proprietaire'] or 0) + (revenue_stats['revenus_cd_proprietaire'] or 0)
		total_marge_brute = (revenue_stats['marge_ld'] or 0) + (revenue_stats['marge_cd'] or 0)
		marge_nette = total_marge_brute - (revenue_stats['total_commissions'] or 0)
		
		taux_occupation = 0
		if general_stats['total_appartements'] > 0:
			appartements_occupes = (occupancy_stats['appartements_loues_ld'] or 0) + (occupancy_stats['appartements_loues_cd'] or 0)
			taux_occupation = (appartements_occupes / general_stats['total_appartements']) * 100
		
		taux_paiement_locataires = 0
		total_paiements_locataires = (payment_stats['paiements_locataires_confirmes'] or 0) + (payment_stats['paiements_locataires_en_attente'] or 0)
		if total_paiements_locataires > 0:
			taux_paiement_locataires = ((payment_stats['paiements_locataires_confirmes'] or 0) / total_paiements_locataires) * 100
		
		return {
			"success": True,
			"period": {
				"start_date": start_date,
				"end_date": end_date,
				"period_name": period
			},
			"general": {
				"total_proprietaires": general_stats['total_proprietaires'] or 0,
				"total_appartements": general_stats['total_appartements'] or 0,
				"total_locations_longues": general_stats['total_locations_longues'] or 0,
				"total_locations_courtes": general_stats['total_locations_courtes'] or 0,
				"total_referents": general_stats['total_referents'] or 0
			},
			"financial": {
				"total_revenus_locataire": total_revenus_locataire,
				"total_revenus_proprietaire": total_revenus_proprietaire,
				"total_marge_brute": total_marge_brute,
				"marge_nette": marge_nette,
				"total_charges": revenue_stats['total_charges'] or 0,
				"total_commissions": revenue_stats['total_commissions'] or 0,
				"marge_percentage": (total_marge_brute / total_revenus_locataire * 100) if total_revenus_locataire > 0 else 0
			},
			"payments": {
				"locataires_confirmes": payment_stats['paiements_locataires_confirmes'] or 0,
				"locataires_en_attente": payment_stats['paiements_locataires_en_attente'] or 0,
				"proprietaires_payes": payment_stats['paiements_proprietaires_payes'] or 0,
				"proprietaires_en_attente": payment_stats['paiements_proprietaires_en_attente'] or 0,
				"montant_locataires_confirme": payment_stats['montant_locataires_confirme'] or 0,
				"montant_proprietaires_paye": payment_stats['montant_proprietaires_paye'] or 0,
				"taux_paiement_locataires": taux_paiement_locataires
			},
			"occupancy": {
				"appartements_loues_ld": occupancy_stats['appartements_loues_ld'] or 0,
				"appartements_loues_cd": occupancy_stats['appartements_loues_cd'] or 0,
				"taux_occupation": taux_occupation,
				"duree_moyenne_cd": occupancy_stats['duree_moyenne_cd'] or 0
			}
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur récupération statistiques tableau de bord: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_performance_metrics(proprietaire_id=None, period_months=12):
	"""Récupère les métriques de performance"""
	try:
		# Calcul des dates
		end_date = nowdate()
		start_date = add_months(getdate(), -period_months).strftime('%Y-%m-%d')
		
		# Filtres pour propriétaire spécifique
		owner_filter = ""
		if proprietaire_id:
			owner_filter = f"AND p.name = '{proprietaire_id}'"
		
		# 1. Métriques de rentabilité
		profitability_metrics = frappe.db.sql(f"""
			SELECT 
				a.name as appartement_id,
				a.adresse as appartement_adresse,
				p.nom_complet as proprietaire_nom,
				
				-- Revenus totaux
				SUM(COALESCE(m.loyer_locataire, 0) + COALESCE(lcd.total_locataire, 0)) as revenus_totaux,
				SUM(COALESCE(m.marge_mensuelle, 0) + COALESCE(lcd.marge_totale, 0)) as marge_totale,
				SUM(COALESCE(ch.montant_total, 0)) as charges_totales,
				SUM(COALESCE(c.montant_commission, 0)) as commissions_totales,
				
				-- Nombre d'opérations
				COUNT(DISTINCT m.name) as nombre_mensualites,
				COUNT(DISTINCT lcd.name) as nombre_locations_cd,
				COUNT(DISTINCT ch.name) as nombre_charges,
				
				-- Moyennes
				AVG(COALESCE(m.marge_mensuelle, 0)) as marge_moyenne_mensuelle,
				AVG(COALESCE(lcd.marge_par_nuit, 0)) as marge_moyenne_nuit
				
			FROM `tabAppartement` a
			INNER JOIN `tabProprietaire` p ON a.proprietaire_id = p.name
			LEFT JOIN `tabLocation Longue Durée` lld ON a.name = lld.appartement_id
			LEFT JOIN `tabMensualite` m ON lld.name = m.location_longue_duree_id 
				AND m.date_echeance BETWEEN '{start_date}' AND '{end_date}'
			LEFT JOIN `tabLocation Courte Duree` lcd ON a.name = lcd.appartement_id 
				AND lcd.date_debut BETWEEN '{start_date}' AND '{end_date}'
			LEFT JOIN `tabCharge` ch ON a.name = ch.appartement_id 
				AND ch.date_charge BETWEEN '{start_date}' AND '{end_date}'
			LEFT JOIN `tabCommission` c ON lcd.name = c.location_courte_duree_id
			WHERE 1=1 {owner_filter}
			GROUP BY a.name, p.name
			HAVING revenus_totaux > 0
			ORDER BY marge_totale DESC
		""", as_dict=True)
		
		# 2. Métriques de performance par mois
		monthly_performance = frappe.db.sql(f"""
			SELECT 
				DATE_FORMAT(COALESCE(m.date_echeance, lcd.date_debut), '%Y-%m') as mois,
				SUM(COALESCE(m.loyer_locataire, 0) + COALESCE(lcd.total_locataire, 0)) as revenus_mois,
				SUM(COALESCE(m.marge_mensuelle, 0) + COALESCE(lcd.marge_totale, 0)) as marge_mois,
				SUM(COALESCE(ch.montant_total, 0)) as charges_mois,
				COUNT(DISTINCT COALESCE(m.name, lcd.name)) as operations_mois
			FROM `tabAppartement` a
			INNER JOIN `tabProprietaire` p ON a.proprietaire_id = p.name
			LEFT JOIN `tabLocation Longue Durée` lld ON a.name = lld.appartement_id
			LEFT JOIN `tabMensualite` m ON lld.name = m.location_longue_duree_id 
				AND m.date_echeance BETWEEN '{start_date}' AND '{end_date}'
			LEFT JOIN `tabLocation Courte Duree` lcd ON a.name = lcd.appartement_id 
				AND lcd.date_debut BETWEEN '{start_date}' AND '{end_date}'
			LEFT JOIN `tabCharge` ch ON a.name = ch.appartement_id 
				AND ch.date_charge BETWEEN '{start_date}' AND '{end_date}'
			WHERE 1=1 {owner_filter}
				AND (m.date_echeance IS NOT NULL OR lcd.date_debut IS NOT NULL)
			GROUP BY DATE_FORMAT(COALESCE(m.date_echeance, lcd.date_debut), '%Y-%m')
			ORDER BY mois
		""", as_dict=True)
		
		# 3. Métriques de référents
		referent_performance = frappe.db.sql(f"""
			SELECT 
				r.name as referent_id,
				r.nom_complet as referent_nom,
				COUNT(c.name) as nombre_commissions,
				SUM(c.montant_commission) as total_commissions,
				AVG(c.pourcentage_commission) as pourcentage_moyen,
				SUM(lcd.marge_totale) as marge_totale_generee,
				COUNT(DISTINCT lcd.name) as locations_referees,
				COUNT(DISTINCT a.name) as appartements_referes,
				SUM(CASE WHEN c.statut = 'Payé' THEN c.montant_commission ELSE 0 END) as commissions_payees,
				(SUM(CASE WHEN c.statut = 'Payé' THEN c.montant_commission ELSE 0 END) / 
				 NULLIF(SUM(c.montant_commission), 0) * 100) as taux_paiement
			FROM `tabReferent` r
			LEFT JOIN `tabCommission` c ON r.name = c.referent_id 
				AND c.creation BETWEEN '{start_date}' AND '{end_date}'
			LEFT JOIN `tabLocation Courte Duree` lcd ON c.location_courte_duree_id = lcd.name
			LEFT JOIN `tabAppartement` a ON lcd.appartement_id = a.name
			LEFT JOIN `tabProprietaire` p ON a.proprietaire_id = p.name
			WHERE r.actif = 1 {owner_filter.replace('p.name', 'p.name') if owner_filter else ''}
			GROUP BY r.name
			HAVING nombre_commissions > 0
			ORDER BY total_commissions DESC
		""", as_dict=True)
		
		# Calcul des métriques globales
		total_revenus = sum(apt['revenus_totaux'] or 0 for apt in profitability_metrics)
		total_marge = sum(apt['marge_totale'] or 0 for apt in profitability_metrics)
		total_charges = sum(apt['charges_totales'] or 0 for apt in profitability_metrics)
		total_commissions = sum(apt['commissions_totales'] or 0 for apt in profitability_metrics)
		
		# Calcul des ratios
		for apt in profitability_metrics:
			apt['roi'] = ((apt['marge_totale'] or 0) / (apt['revenus_totaux'] or 1)) * 100
			apt['marge_nette'] = (apt['marge_totale'] or 0) - (apt['commissions_totales'] or 0)
			apt['ratio_charges'] = ((apt['charges_totales'] or 0) / (apt['revenus_totaux'] or 1)) * 100
			apt['efficacite'] = (apt['marge_totale'] or 0) / max(1, (apt['nombre_mensualites'] or 0) + (apt['nombre_locations_cd'] or 0))
		
		# Calcul des tendances
		trends = {
			"revenus_trend": 0,
			"marge_trend": 0,
			"operations_trend": 0
		}
		
		if len(monthly_performance) >= 2:
			# Comparaison des 3 derniers mois vs 3 mois précédents
			recent_months = monthly_performance[-3:] if len(monthly_performance) >= 3 else monthly_performance[-1:]
			previous_months = monthly_performance[-6:-3] if len(monthly_performance) >= 6 else monthly_performance[:-3] if len(monthly_performance) > 3 else []
			
			if previous_months:
				recent_avg_revenus = sum(m['revenus_mois'] or 0 for m in recent_months) / len(recent_months)
				previous_avg_revenus = sum(m['revenus_mois'] or 0 for m in previous_months) / len(previous_months)
				
				if previous_avg_revenus > 0:
					trends["revenus_trend"] = ((recent_avg_revenus - previous_avg_revenus) / previous_avg_revenus) * 100
				
				recent_avg_marge = sum(m['marge_mois'] or 0 for m in recent_months) / len(recent_months)
				previous_avg_marge = sum(m['marge_mois'] or 0 for m in previous_months) / len(previous_months)
				
				if previous_avg_marge > 0:
					trends["marge_trend"] = ((recent_avg_marge - previous_avg_marge) / previous_avg_marge) * 100
		
		return {
			"success": True,
			"period": {
				"start_date": start_date,
				"end_date": end_date,
				"months": period_months
			},
			"global_metrics": {
				"total_revenus": total_revenus,
				"total_marge": total_marge,
				"total_charges": total_charges,
				"total_commissions": total_commissions,
				"marge_nette_globale": total_marge - total_commissions,
				"roi_global": (total_marge / total_revenus * 100) if total_revenus > 0 else 0,
				"ratio_charges_global": (total_charges / total_revenus * 100) if total_revenus > 0 else 0
			},
			"appartements_performance": profitability_metrics,
			"monthly_performance": monthly_performance,
			"referents_performance": referent_performance,
			"trends": trends
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur récupération métriques performance: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_comparative_analysis(proprietaire_ids=None, period="current_year"):
	"""Analyse comparative entre propriétaires ou appartements"""
	try:
		# Calcul des dates selon la période
		if period == "current_year":
			start_date = f"{getdate().year}-01-01"
			end_date = nowdate()
		elif period == "last_year":
			start_date = f"{getdate().year - 1}-01-01"
			end_date = f"{getdate().year - 1}-12-31"
		else:
			start_date = f"{getdate().year}-01-01"
			end_date = nowdate()
		
		# Filtres pour propriétaires spécifiques
		owner_filter = ""
		if proprietaire_ids:
			if isinstance(proprietaire_ids, str):
				proprietaire_ids = json.loads(proprietaire_ids)
			owner_list = "', '".join(proprietaire_ids)
			owner_filter = f"AND p.name IN ('{owner_list}')"
		
		# Analyse comparative par propriétaire
		proprietaires_comparison = frappe.db.sql(f"""
			SELECT 
				p.name as proprietaire_id,
				p.nom_complet as proprietaire_nom,
				p.email as proprietaire_email,
				COUNT(DISTINCT a.name) as nombre_appartements,
				
				-- Revenus et marges
				SUM(COALESCE(m.loyer_locataire, 0) + COALESCE(lcd.total_locataire, 0)) as revenus_totaux,
				SUM(COALESCE(m.loyer_proprietaire, 0) + COALESCE(lcd.total_proprietaire, 0)) as revenus_proprietaire,
				SUM(COALESCE(m.marge_mensuelle, 0) + COALESCE(lcd.marge_totale, 0)) as marge_brute,
				SUM(COALESCE(ch.montant_total, 0)) as charges_totales,
				SUM(COALESCE(c.montant_commission, 0)) as commissions_totales,
				
				-- Activité
				COUNT(DISTINCT m.name) as nombre_mensualites,
				COUNT(DISTINCT lcd.name) as nombre_locations_cd,
				SUM(COALESCE(lcd.nombre_nuits, 0)) as total_nuits_cd,
				
				-- Paiements
				COUNT(CASE WHEN pl.statut = 'Confirmé' THEN 1 END) as paiements_confirmes,
				COUNT(CASE WHEN pl.statut = 'En attente' THEN 1 END) as paiements_en_attente,
				COUNT(CASE WHEN pp.statut = 'Payé' THEN 1 END) as versements_effectues,
				
				-- Moyennes
				AVG(COALESCE(m.marge_mensuelle, 0)) as marge_moyenne_mensuelle,
				AVG(COALESCE(lcd.marge_par_nuit, 0)) as marge_moyenne_nuit
				
			FROM `tabProprietaire` p
			LEFT JOIN `tabAppartement` a ON p.name = a.proprietaire_id
			LEFT JOIN `tabLocation Longue Durée` lld ON a.name = lld.appartement_id
			LEFT JOIN `tabMensualite` m ON lld.name = m.location_longue_duree_id 
				AND m.date_echeance BETWEEN '{start_date}' AND '{end_date}'
			LEFT JOIN `tabLocation Courte Duree` lcd ON a.name = lcd.appartement_id 
				AND lcd.date_debut BETWEEN '{start_date}' AND '{end_date}'
			LEFT JOIN `tabCharge` ch ON a.name = ch.appartement_id 
				AND ch.date_charge BETWEEN '{start_date}' AND '{end_date}'
			LEFT JOIN `tabCommission` c ON lcd.name = c.location_courte_duree_id
			LEFT JOIN `tabPaiement Locataire` pl ON a.name = pl.appartement_id 
				AND pl.creation BETWEEN '{start_date}' AND '{end_date}'
			LEFT JOIN `tabPaiement Propriétaire` pp ON a.name = pp.appartement_id 
				AND pp.creation BETWEEN '{start_date}' AND '{end_date}'
			WHERE 1=1 {owner_filter}
			GROUP BY p.name
			HAVING nombre_appartements > 0
			ORDER BY marge_brute DESC
		""", as_dict=True)
		
		# Calcul des métriques dérivées et classements
		for i, prop in enumerate(proprietaires_comparison):
			# Calculs de base
			prop['marge_nette'] = (prop['marge_brute'] or 0) - (prop['commissions_totales'] or 0)
			prop['roi'] = ((prop['marge_brute'] or 0) / (prop['revenus_totaux'] or 1)) * 100
			prop['ratio_charges'] = ((prop['charges_totales'] or 0) / (prop['revenus_totaux'] or 1)) * 100
			
			# Efficacité
			total_operations = (prop['nombre_mensualites'] or 0) + (prop['nombre_locations_cd'] or 0)
			prop['efficacite_operationnelle'] = (prop['marge_brute'] or 0) / max(1, total_operations)
			prop['revenus_par_appartement'] = (prop['revenus_totaux'] or 0) / max(1, prop['nombre_appartements'] or 1)
			
			# Taux de paiement
			total_paiements = (prop['paiements_confirmes'] or 0) + (prop['paiements_en_attente'] or 0)
			prop['taux_paiement'] = ((prop['paiements_confirmes'] or 0) / max(1, total_paiements)) * 100
			
			# Classement temporaire
			prop['classement_revenus'] = i + 1
		
		# Recalcul des classements par critère
		# Classement par ROI
		proprietaires_by_roi = sorted(proprietaires_comparison, key=lambda x: x['roi'], reverse=True)
		for i, prop in enumerate(proprietaires_by_roi):
			for p in proprietaires_comparison:
				if p['proprietaire_id'] == prop['proprietaire_id']:
					p['classement_roi'] = i + 1
					break
		
		# Classement par efficacité
		proprietaires_by_efficiency = sorted(proprietaires_comparison, key=lambda x: x['efficacite_operationnelle'], reverse=True)
		for i, prop in enumerate(proprietaires_by_efficiency):
			for p in proprietaires_comparison:
				if p['proprietaire_id'] == prop['proprietaire_id']:
					p['classement_efficacite'] = i + 1
					break
		
		# Analyse des écarts et moyennes
		if proprietaires_comparison:
			moyennes = {
				'revenus_moyens': sum(p['revenus_totaux'] or 0 for p in proprietaires_comparison) / len(proprietaires_comparison),
				'marge_moyenne': sum(p['marge_brute'] or 0 for p in proprietaires_comparison) / len(proprietaires_comparison),
				'roi_moyen': sum(p['roi'] or 0 for p in proprietaires_comparison) / len(proprietaires_comparison),
				'efficacite_moyenne': sum(p['efficacite_operationnelle'] or 0 for p in proprietaires_comparison) / len(proprietaires_comparison),
				'taux_paiement_moyen': sum(p['taux_paiement'] or 0 for p in proprietaires_comparison) / len(proprietaires_comparison)
			}
			
			# Calcul des écarts par rapport à la moyenne
			for prop in proprietaires_comparison:
				prop['ecart_revenus'] = ((prop['revenus_totaux'] or 0) - moyennes['revenus_moyens']) / moyennes['revenus_moyens'] * 100 if moyennes['revenus_moyens'] > 0 else 0
				prop['ecart_roi'] = ((prop['roi'] or 0) - moyennes['roi_moyen']) / moyennes['roi_moyen'] * 100 if moyennes['roi_moyen'] > 0 else 0
				prop['ecart_efficacite'] = ((prop['efficacite_operationnelle'] or 0) - moyennes['efficacite_moyenne']) / moyennes['efficacite_moyenne'] * 100 if moyennes['efficacite_moyenne'] > 0 else 0
		else:
			moyennes = {}
		
		# Top performers
		top_performers = {
			'meilleur_revenus': proprietaires_comparison[0] if proprietaires_comparison else None,
			'meilleur_roi': max(proprietaires_comparison, key=lambda x: x['roi']) if proprietaires_comparison else None,
			'meilleur_efficacite': max(proprietaires_comparison, key=lambda x: x['efficacite_operationnelle']) if proprietaires_comparison else None,
			'meilleur_taux_paiement': max(proprietaires_comparison, key=lambda x: x['taux_paiement']) if proprietaires_comparison else None
		}
		
		return {
			"success": True,
			"period": {
				"start_date": start_date,
				"end_date": end_date,
				"period_name": period
			},
			"proprietaires_comparison": proprietaires_comparison,
			"moyennes": moyennes,
			"top_performers": top_performers,
			"nombre_proprietaires": len(proprietaires_comparison)
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur analyse comparative: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_predictive_analytics(proprietaire_id=None, forecast_months=6):
	"""Analyse prédictive basée sur les tendances historiques"""
	try:
		# Récupération des données historiques (12 derniers mois)
		end_date = nowdate()
		start_date = add_months(getdate(), -12).strftime('%Y-%m-%d')
		
		# Filtres pour propriétaire spécifique
		owner_filter = ""
		if proprietaire_id:
			owner_filter = f"AND p.name = '{proprietaire_id}'"
		
		# Données mensuelles historiques
		historical_data = frappe.db.sql(f"""
			SELECT 
				DATE_FORMAT(COALESCE(m.date_echeance, lcd.date_debut), '%Y-%m') as mois,
				SUM(COALESCE(m.loyer_locataire, 0) + COALESCE(lcd.total_locataire, 0)) as revenus,
				SUM(COALESCE(m.marge_mensuelle, 0) + COALESCE(lcd.marge_totale, 0)) as marge,
				SUM(COALESCE(ch.montant_total, 0)) as charges,
				COUNT(DISTINCT COALESCE(m.name, lcd.name)) as operations,
				COUNT(DISTINCT a.name) as appartements_actifs
			FROM `tabAppartement` a
			INNER JOIN `tabProprietaire` p ON a.proprietaire_id = p.name
			LEFT JOIN `tabLocation Longue Durée` lld ON a.name = lld.appartement_id
			LEFT JOIN `tabMensualite` m ON lld.name = m.location_longue_duree_id 
				AND m.date_echeance BETWEEN '{start_date}' AND '{end_date}'
			LEFT JOIN `tabLocation Courte Duree` lcd ON a.name = lcd.appartement_id 
				AND lcd.date_debut BETWEEN '{start_date}' AND '{end_date}'
			LEFT JOIN `tabCharge` ch ON a.name = ch.appartement_id 
				AND ch.date_charge BETWEEN '{start_date}' AND '{end_date}'
			WHERE 1=1 {owner_filter}
				AND (m.date_echeance IS NOT NULL OR lcd.date_debut IS NOT NULL)
			GROUP BY DATE_FORMAT(COALESCE(m.date_echeance, lcd.date_debut), '%Y-%m')
			ORDER BY mois
		""", as_dict=True)
		
		if len(historical_data) < 3:
			return {
				"success": False,
				"error": "Données historiques insuffisantes pour la prédiction (minimum 3 mois)"
			}
		
		# Calcul des tendances (régression linéaire simple)
		def calculate_trend(values):
			if len(values) < 2:
				return 0
			n = len(values)
			x_sum = sum(range(n))
			y_sum = sum(values)
			xy_sum = sum(i * values[i] for i in range(n))
			x2_sum = sum(i * i for i in range(n))
			
			if n * x2_sum - x_sum * x_sum == 0:
				return 0
			
			slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum)
			return slope
		
		# Extraction des valeurs pour le calcul des tendances
		revenus_values = [d['revenus'] or 0 for d in historical_data]
		marge_values = [d['marge'] or 0 for d in historical_data]
		charges_values = [d['charges'] or 0 for d in historical_data]
		operations_values = [d['operations'] or 0 for d in historical_data]
		
		# Calcul des tendances
		revenus_trend = calculate_trend(revenus_values)
		marge_trend = calculate_trend(marge_values)
		charges_trend = calculate_trend(charges_values)
		operations_trend = calculate_trend(operations_values)
		
		# Moyennes des derniers mois pour la base de prédiction
		last_3_months = historical_data[-3:] if len(historical_data) >= 3 else historical_data
		base_revenus = sum(d['revenus'] or 0 for d in last_3_months) / len(last_3_months)
		base_marge = sum(d['marge'] or 0 for d in last_3_months) / len(last_3_months)
		base_charges = sum(d['charges'] or 0 for d in last_3_months) / len(last_3_months)
		base_operations = sum(d['operations'] or 0 for d in last_3_months) / len(last_3_months)
		
		# Génération des prédictions
		predictions = []
		for i in range(1, forecast_months + 1):
			# Calcul des valeurs prédites
			predicted_revenus = max(0, base_revenus + (revenus_trend * i))
			predicted_marge = max(0, base_marge + (marge_trend * i))
			predicted_charges = max(0, base_charges + (charges_trend * i))
			predicted_operations = max(0, base_operations + (operations_trend * i))
			
			# Date de prédiction
			prediction_date = add_months(getdate(), i)
			prediction_month = f"{prediction_date.year}-{prediction_date.month:02d}"
			
			predictions.append({
				"mois": prediction_month,
				"revenus_predits": predicted_revenus,
				"marge_predite": predicted_marge,
				"charges_predites": predicted_charges,
				"operations_predites": int(predicted_operations),
				"marge_nette_predite": predicted_marge - predicted_charges,
				"confiance": max(0.3, 1 - (i * 0.1))  # Confiance décroissante avec le temps
			})
		
		# Analyse des risques et opportunités
		risks_opportunities = []
		
		# Tendance des revenus
		if revenus_trend > 0:
			risks_opportunities.append({
				"type": "opportunité",
				"description": f"Croissance des revenus prévue (+{revenus_trend:.0f}€/mois)",
				"impact": "positif",
				"probabilite": "élevée" if abs(revenus_trend) > base_revenus * 0.05 else "moyenne"
			})
		elif revenus_trend < -base_revenus * 0.02:  # Baisse > 2%
			risks_opportunities.append({
				"type": "risque",
				"description": f"Baisse des revenus prévue ({revenus_trend:.0f}€/mois)",
				"impact": "négatif",
				"probabilite": "moyenne"
			})
		
		# Tendance des charges
		if charges_trend > base_charges * 0.05:  # Hausse > 5%
			risks_opportunities.append({
				"type": "risque",
				"description": f"Augmentation des charges prévue (+{charges_trend:.0f}€/mois)",
				"impact": "négatif",
				"probabilite": "moyenne"
			})
		
		# Tendance des opérations
		if operations_trend > 0.5:
			risks_opportunities.append({
				"type": "opportunité",
				"description": "Augmentation de l'activité prévue",
				"impact": "positif",
				"probabilite": "moyenne"
			})
		
		# Recommandations
		recommendations = []
		
		if revenus_trend < 0:
			recommendations.append("Analyser les causes de la baisse des revenus et ajuster la stratégie tarifaire")
		
		if charges_trend > base_charges * 0.03:
			recommendations.append("Surveiller l'évolution des charges et optimiser les coûts")
		
		if marge_trend < 0:
			recommendations.append("Revoir la stratégie de pricing pour améliorer les marges")
		
		if operations_trend < 0:
			recommendations.append("Intensifier les efforts marketing pour augmenter l'activité")
		
		# Calcul des totaux prédits
		total_revenus_predits = sum(p['revenus_predits'] for p in predictions)
		total_marge_predite = sum(p['marge_predite'] for p in predictions)
		total_charges_predites = sum(p['charges_predites'] for p in predictions)
		
		return {
			"success": True,
			"period_historique": {
				"start_date": start_date,
				"end_date": end_date,
				"mois_analyses": len(historical_data)
			},
			"period_prediction": {
				"mois_predits": forecast_months,
				"debut_prediction": add_months(getdate(), 1).strftime('%Y-%m-%d')
			},
			"donnees_historiques": historical_data,
			"tendances": {
				"revenus_trend": revenus_trend,
				"marge_trend": marge_trend,
				"charges_trend": charges_trend,
				"operations_trend": operations_trend
			},
			"predictions": predictions,
			"resume_predictions": {
				"total_revenus_predits": total_revenus_predits,
				"total_marge_predite": total_marge_predite,
				"total_charges_predites": total_charges_predites,
				"marge_nette_predite": total_marge_predite - total_charges_predites,
				"roi_predit": (total_marge_predite / total_revenus_predits * 100) if total_revenus_predits > 0 else 0
			},
			"risques_opportunites": risks_opportunities,
			"recommandations": recommendations
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur analyse prédictive: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_kpi_summary(proprietaire_id=None, period="current_month"):
	"""Récupère un résumé des KPI principaux"""
	try:
		# Récupération des statistiques de base
		dashboard_stats = get_dashboard_statistics(proprietaire_id, period)
		if not dashboard_stats["success"]:
			return dashboard_stats
		
		# Récupération des métriques de performance
		performance_metrics = get_performance_metrics(proprietaire_id, 12)
		if not performance_metrics["success"]:
			return performance_metrics
		
		# Compilation des KPI principaux
		kpis = {
			"revenus": {
				"total": dashboard_stats["financial"]["total_revenus_locataire"],
				"trend": performance_metrics["trends"]["revenus_trend"],
				"status": "positive" if performance_metrics["trends"]["revenus_trend"] > 0 else "negative"
			},
			"marge": {
				"total": dashboard_stats["financial"]["marge_nette"],
				"percentage": dashboard_stats["financial"]["marge_percentage"],
				"trend": performance_metrics["trends"]["marge_trend"],
				"status": "positive" if performance_metrics["trends"]["marge_trend"] > 0 else "negative"
			},
			"occupation": {
				"taux": dashboard_stats["occupancy"]["taux_occupation"],
				"appartements_loues": dashboard_stats["occupancy"]["appartements_loues_ld"] + dashboard_stats["occupancy"]["appartements_loues_cd"],
				"total_appartements": dashboard_stats["general"]["total_appartements"],
				"status": "positive" if dashboard_stats["occupancy"]["taux_occupation"] > 70 else "warning" if dashboard_stats["occupancy"]["taux_occupation"] > 50 else "negative"
			},
			"paiements": {
				"taux_reussite": dashboard_stats["payments"]["taux_paiement_locataires"],
				"confirmes": dashboard_stats["payments"]["locataires_confirmes"],
				"en_attente": dashboard_stats["payments"]["locataires_en_attente"],
				"status": "positive" if dashboard_stats["payments"]["taux_paiement_locataires"] > 90 else "warning" if dashboard_stats["payments"]["taux_paiement_locataires"] > 70 else "negative"
			},
			"charges": {
				"total": dashboard_stats["financial"]["total_charges"],
				"ratio": (dashboard_stats["financial"]["total_charges"] / dashboard_stats["financial"]["total_revenus_locataire"] * 100) if dashboard_stats["financial"]["total_revenus_locataire"] > 0 else 0,
				"status": "positive" if (dashboard_stats["financial"]["total_charges"] / dashboard_stats["financial"]["total_revenus_locataire"] * 100) < 20 else "warning" if (dashboard_stats["financial"]["total_charges"] / dashboard_stats["financial"]["total_revenus_locataire"] * 100) < 30 else "negative" if dashboard_stats["financial"]["total_revenus_locataire"] > 0 else "neutral"
			}
		}
		
		# Score global de performance
		scores = []
		for kpi in kpis.values():
			if kpi["status"] == "positive":
				scores.append(100)
			elif kpi["status"] == "warning":
				scores.append(70)
			elif kpi["status"] == "negative":
				scores.append(30)
			else:
				scores.append(50)
		
		global_score = sum(scores) / len(scores) if scores else 0
		
		return {
			"success": True,
			"period": dashboard_stats["period"],
			"kpis": kpis,
			"global_score": global_score,
			"performance_level": "excellent" if global_score >= 90 else "bon" if global_score >= 70 else "moyen" if global_score >= 50 else "faible"
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur récupération KPI: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}