# Copyright (c) 2024, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import getdate, add_months, flt
from datetime import datetime, timedelta


@frappe.whitelist()
def get_proprietaire_dashboard_data(proprietaire_id):
	"""Récupère les données du dashboard pour un propriétaire"""
	try:
		# Vérifier que le propriétaire existe
		proprietaire = frappe.get_doc("Proprietaire", proprietaire_id)
		
		# Calculer la période (année en cours)
		aujourdhui = getdate()
		annee_courante = aujourdhui.year
		date_debut = f"{annee_courante}-01-01"
		date_fin = f"{annee_courante}-12-31"
		
		# Récupérer les statistiques de base du propriétaire
		stats_base = frappe.db.sql("""
			SELECT 
				COUNT(DISTINCT a.name) as total_appartements,
				COUNT(DISTINCT lld.name) as total_locations_longues,
				COUNT(DISTINCT lcd.name) as total_locations_courtes
			FROM `tabProprietaire` p
			LEFT JOIN `tabAppartement` a ON p.name = a.proprietaire_id
			LEFT JOIN `tabLocation Longue Duree` lld ON a.name = lld.appartement_id
			LEFT JOIN `tabLocation Courte Duree` lcd ON a.name = lcd.appartement_id
			WHERE p.name = %s
		""", (proprietaire_id,), as_dict=True)[0]
		
		# Calculer les statistiques financières
		
		# Calculer les revenus locataires (seulement les paiements soumis/validés)
		revenus_mensualites = frappe.db.sql("""
			SELECT COALESCE(SUM(pl.montant), 0) as total
			FROM `tabPaiement Locataire` pl
			INNER JOIN `tabMensualite` m ON pl.mensualite_id = m.name
			INNER JOIN `tabLocation Longue Duree` lld ON m.location_longue_duree_id = lld.name
			INNER JOIN `tabAppartement` a ON lld.appartement_id = a.name
			WHERE a.proprietaire_id = %s
				AND pl.docstatus = 1
				AND pl.date_paiement BETWEEN %s AND %s
		""", (proprietaire_id, date_debut, date_fin), as_dict=True)[0]['total']
		
		revenus_longue = frappe.db.sql("""
			SELECT COALESCE(SUM(pl.montant), 0) as total
			FROM `tabPaiement Locataire` pl
			INNER JOIN `tabLocation Longue Duree` lld ON pl.location_longue_duree_id = lld.name
			INNER JOIN `tabAppartement` a ON lld.appartement_id = a.name
			WHERE a.proprietaire_id = %s
				AND pl.mensualite_id IS NULL
				AND pl.docstatus = 1
				AND pl.date_paiement BETWEEN %s AND %s
		""", (proprietaire_id, date_debut, date_fin), as_dict=True)[0]['total']
		
		revenus_courte = frappe.db.sql("""
			SELECT COALESCE(SUM(pl.montant), 0) as total
			FROM `tabPaiement Locataire` pl
			INNER JOIN `tabLocation Courte Duree` lcd ON pl.location_courte_duree_id = lcd.name
			INNER JOIN `tabAppartement` a ON lcd.appartement_id = a.name
			WHERE a.proprietaire_id = %s
				AND pl.docstatus = 1
				AND pl.date_paiement BETWEEN %s AND %s
		""", (proprietaire_id, date_debut, date_fin), as_dict=True)[0]['total']
		
		# Calculer les paiements propriétaires
		paiements_mensualites = frappe.db.sql("""
			SELECT COALESCE(SUM(pp.montant), 0) as total
			FROM `tabPaiement Proprietaire` pp
			WHERE pp.proprietaire = %s
				AND pp.mensualite_id IS NOT NULL
				AND pp.docstatus = 1
				AND pp.date_paiement BETWEEN %s AND %s
		""", (proprietaire_id, date_debut, date_fin), as_dict=True)[0]['total']
		
		paiements_longue = frappe.db.sql("""
			SELECT COALESCE(SUM(pp.montant), 0) as total
			FROM `tabPaiement Proprietaire` pp
			WHERE pp.proprietaire = %s
				AND pp.location_longue_duree_id IS NOT NULL
				AND pp.mensualite_id IS NULL
				AND pp.docstatus = 1
				AND pp.date_paiement BETWEEN %s AND %s
		""", (proprietaire_id, date_debut, date_fin), as_dict=True)[0]['total']
		
		paiements_courte = frappe.db.sql("""
			SELECT COALESCE(SUM(pp.montant), 0) as total
			FROM `tabPaiement Proprietaire` pp
			WHERE pp.proprietaire = %s
				AND pp.location_courte_duree_id IS NOT NULL
				AND pp.docstatus = 1
				AND pp.date_paiement BETWEEN %s AND %s
		""", (proprietaire_id, date_debut, date_fin), as_dict=True)[0]['total']
		
		# Calculer les charges (simplifié avec le champ proprietaire_id direct)
		charges_total = frappe.db.sql("""
			SELECT COALESCE(SUM(ch.montant), 0) as total
			FROM `tabCharge` ch
			WHERE ch.proprietaire_id = %s
				AND ch.date_charge BETWEEN %s AND %s
		""", (proprietaire_id, date_debut, date_fin), as_dict=True)[0]['total']
		
		# Compter les paiements
		paiements_stats = frappe.db.sql("""
			SELECT 
				SUM(CASE WHEN docstatus = 1 AND date_paiement BETWEEN %s AND %s THEN 1 ELSE 0 END) as payes,
				SUM(CASE WHEN docstatus = 0 THEN 1 ELSE 0 END) as en_attente,
				COALESCE(SUM(CASE WHEN docstatus = 0 THEN montant ELSE 0 END), 0) as montant_en_attente
			FROM `tabPaiement Proprietaire` pp
			WHERE pp.proprietaire = %s
		""", (date_debut, date_fin, proprietaire_id), as_dict=True)[0]
		
		stats_financieres = {
			'revenus_locataires_mensualites': revenus_mensualites or 0,
			'revenus_locataires_longue': revenus_longue or 0,
			'revenus_locataires_courte': revenus_courte or 0,
			'montant_verse_mensualites': paiements_mensualites or 0,
			'montant_verse_longue': paiements_longue or 0,
			'montant_verse_courte': paiements_courte or 0,
			'paiements_payes': paiements_stats['payes'] or 0,
			'paiements_en_attente': paiements_stats['en_attente'] or 0,
			'montant_paiements_en_attente': paiements_stats['montant_en_attente'] or 0,
			'charges_total': charges_total or 0
		}
		
		# Calculer les statistiques d'occupation
		stats_occupation = frappe.db.sql("""
			SELECT 
				COUNT(CASE WHEN lld.statut = 'Actif' THEN 1 END) as appartements_loues_ld,
				COUNT(CASE WHEN lcd.date_debut <= CURDATE() AND lcd.date_fin >= CURDATE() 
						   THEN 1 END) as appartements_loues_cd,
				AVG(CASE WHEN lcd.date_debut BETWEEN %s AND %s 
						 THEN DATEDIFF(lcd.date_fin, lcd.date_debut) + 1 
						 ELSE NULL END) as duree_moyenne_cd
			FROM `tabProprietaire` p
			LEFT JOIN `tabAppartement` a ON p.name = a.proprietaire_id
			LEFT JOIN `tabLocation Longue Duree` lld ON a.name = lld.appartement_id
			LEFT JOIN `tabLocation Courte Duree` lcd ON a.name = lcd.appartement_id
			WHERE p.name = %s
		""", (date_debut, date_fin, proprietaire_id), as_dict=True)[0]
		
		# Calculer les métriques dérivées
		revenus_totaux = (
			(stats_financieres.get('revenus_locataires_mensualites', 0) or 0) +
			(stats_financieres.get('revenus_locataires_longue', 0) or 0) +
			(stats_financieres.get('revenus_locataires_courte', 0) or 0)
		)
		montant_verse = (
			(stats_financieres.get('montant_verse_mensualites', 0) or 0) +
			(stats_financieres.get('montant_verse_longue', 0) or 0) +
			(stats_financieres.get('montant_verse_courte', 0) or 0)
		)
		charges_totales = stats_financieres.get('charges_total', 0) or 0
		paiements_payes = stats_financieres.get('paiements_payes', 0) or 0
		paiements_en_attente = stats_financieres.get('paiements_en_attente', 0) or 0
		montant_paiements_en_attente = stats_financieres.get('montant_paiements_en_attente', 0) or 0
		
		marge_brute = revenus_totaux - montant_verse
		marge_nette = marge_brute - charges_totales
		marge_percentage = (marge_brute / revenus_totaux * 100) if revenus_totaux > 0 else 0
		
		total_appartements = flt(stats_base.get('total_appartements', 0))
		appartements_loues = flt(stats_occupation.get('appartements_loues_ld', 0)) + flt(stats_occupation.get('appartements_loues_cd', 0))
		taux_occupation = (appartements_loues / total_appartements * 100) if total_appartements > 0 else 0
		
		# Calculer le taux de paiement des locataires (basé sur les paiements soumis)
		total_paiements_locataires = frappe.db.count('Paiement Locataire', {
			'proprietaire_id': proprietaire_id,
			'creation': ['between', [date_debut, date_fin]],
			'docstatus': ['in', [0, 1]]  # Brouillon ou soumis
		})
		paiements_confirmes = frappe.db.count('Paiement Locataire', {
			'proprietaire_id': proprietaire_id,
			'docstatus': 1,  # Seulement les paiements soumis (validés)
			'creation': ['between', [date_debut, date_fin]]
		})
		taux_paiement_locataires = (paiements_confirmes / total_paiements_locataires * 100) if total_paiements_locataires > 0 else 0
		
		return {
			"success": True,
			"period": {
				"start_date": date_debut,
				"end_date": date_fin,
				"year": annee_courante
			},
			"general": {
				"total_appartements": int(stats_base.get('total_appartements', 0)),
				"total_locations_longues": int(stats_base.get('total_locations_longues', 0)),
				"total_locations_courtes": int(stats_base.get('total_locations_courtes', 0))
			},
			"financial": {
				"total_revenus_locataire": revenus_totaux,
				"montant_verse_proprietaire": montant_verse,
				"charges_total": charges_totales,
				"marge_brute": marge_brute,
				"marge_nette": marge_nette,
				"marge_percentage": marge_percentage
			},
			"payments": {
				"proprietaires_payes": int(paiements_payes),
				"proprietaires_en_attente": int(paiements_en_attente),
				"montant_proprietaires_paye": montant_verse,
				"montant_proprietaires_en_attente": montant_paiements_en_attente,
				"taux_paiement_locataires": taux_paiement_locataires
			},
			"occupancy": {
				"appartements_loues_ld": int(stats_occupation.get('appartements_loues_ld', 0)),
				"appartements_loues_cd": int(stats_occupation.get('appartements_loues_cd', 0)),
				"taux_occupation": taux_occupation,
				"duree_moyenne_cd": flt(stats_occupation.get('duree_moyenne_cd', 0))
			}
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur get_proprietaire_dashboard_data: {str(e)}")
		return {"success": False, "error": str(e)}


@frappe.whitelist()
def get_proprietaire_performance_metrics(proprietaire_id, months=12):
	"""Récupère les métriques de performance d'un propriétaire sur une période donnée"""
	try:
		# Importer la fonction depuis paiement_proprietaire.py
		from immo.hooks_handlers.paiement_proprietaire import calculate_owner_performance_metrics
		
		# Calculer les dates
		aujourdhui = getdate()
		date_fin = aujourdhui
		date_debut = add_months(aujourdhui, -months)
		
		# Utiliser la fonction corrigée
		metrics = calculate_owner_performance_metrics(proprietaire_id, date_debut.strftime('%Y-%m-%d'), date_fin.strftime('%Y-%m-%d'))
		
		return {
			"success": True,
			"period": {
				"start_date": date_debut.strftime('%Y-%m-%d'),
				"end_date": date_fin.strftime('%Y-%m-%d'),
				"months": months
			},
			"metrics": metrics
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur get_proprietaire_performance_metrics: {str(e)}")
		return {"success": False, "error": str(e)}