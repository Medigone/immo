# -*- coding: utf-8 -*-
# Copyright (c) 2024, IntraPro and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate
from datetime import datetime, timedelta

@frappe.whitelist()
def validate_paiement_amount(location_bloc_id, montant_paiement, exclude_paiement_id=None):
	"""Valide qu'un montant de paiement ne dépasse pas le solde restant"""
	try:
		location_bloc = frappe.get_doc("Location Bloc", location_bloc_id)
		
		# Calculer le total déjà payé
		filters = {
			"location_bloc_id": location_bloc_id
		}
		
		if exclude_paiement_id:
			filters["name"] = ["!=", exclude_paiement_id]
		
		if exclude_paiement_id:
			total_paiements = frappe.db.sql("""
				SELECT COALESCE(SUM(montant_paiement), 0)
				FROM `tabPaiement Bloc`
				WHERE location_bloc_id = %s
				AND name != %s
			""", (location_bloc_id, exclude_paiement_id))[0][0] or 0
		else:
			total_paiements = frappe.db.sql("""
				SELECT COALESCE(SUM(montant_paiement), 0)
				FROM `tabPaiement Bloc`
				WHERE location_bloc_id = %s
			""", (location_bloc_id,))[0][0] or 0
		
		solde_restant = flt(location_bloc.montant_total_proprietaire) - flt(total_paiements)
		
		return {
			"valid": flt(montant_paiement) <= solde_restant,
			"solde_restant": solde_restant,
			"total_paiements": total_paiements,
			"montant_bloc": location_bloc.montant_total_proprietaire,
			"message": f"Solde restant: {solde_restant}€" if flt(montant_paiement) <= solde_restant else f"Montant trop élevé. Solde restant: {solde_restant}€"
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur validation montant paiement: {str(e)}")
		return {
			"valid": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_paiement_schedule(location_bloc_id):
	"""Retourne l'échéancier de paiement pour une location bloc"""
	try:
		location_bloc = frappe.get_doc("Location Bloc", location_bloc_id)
		
		# Récupérer tous les paiements
		paiements = frappe.get_all("Paiement Bloc",
			filters={"location_bloc_id": location_bloc_id},
			fields=["name", "montant_paiement", "date_paiement", "type_paiement", "methode_paiement"],
			order_by="date_paiement")
		
		# Calculer les totaux
		total_prevu = flt(location_bloc.montant_total_proprietaire)
		total_paye = sum([flt(p.montant_paiement) for p in paiements])
		total_en_attente = 0
		solde_restant = total_prevu - total_paye - total_en_attente
		
		# Générer des suggestions d'échéancier si nécessaire
		suggestions = []
		if location_bloc.type_paiement == "Échelonné" and solde_restant > 0:
			suggestions = generate_payment_suggestions(location_bloc, solde_restant)
		
		return {
			"location_bloc": {
				"name": location_bloc.name,
				"montant_total": total_prevu,
				"type_paiement": location_bloc.type_paiement,
				"date_debut": location_bloc.date_debut_bloc,
				"date_fin": location_bloc.date_fin_bloc
			},
			"paiements": paiements,
			"totaux": {
				"total_prevu": total_prevu,
				"total_paye": total_paye,
				"total_en_attente": total_en_attente,
				"solde_restant": solde_restant,
				"pourcentage_paye": (total_paye / total_prevu * 100) if total_prevu > 0 else 0
			},
			"suggestions": suggestions
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur récupération échéancier: {str(e)}")
		return {"error": str(e)}


def generate_payment_suggestions(location_bloc, solde_restant):
	"""Génère des suggestions d'échéancier de paiement"""
	try:
		suggestions = []
		date_debut = getdate(location_bloc.date_debut_bloc)
		date_fin = getdate(location_bloc.date_fin_bloc)
		
		# Suggestion 1: Paiement unique avant le début
		suggestions.append({
			"type": "Paiement unique",
			"montant": solde_restant,
			"date_suggere": (date_debut - timedelta(days=7)).strftime("%Y-%m-%d"),
			"description": "Paiement complet 7 jours avant le début"
		})
		
		# Suggestion 2: Paiement en 2 fois
		if solde_restant >= 200:  # Minimum pour justifier un échelonnement
			montant_1 = solde_restant * 0.6  # 60% en avance
			montant_2 = solde_restant - montant_1
			
			suggestions.append({
				"type": "Échelonné (2 fois)",
				"paiements": [
					{
						"montant": montant_1,
						"date_suggere": (date_debut - timedelta(days=14)).strftime("%Y-%m-%d"),
						"description": "Acompte (60%)"
					},
					{
						"montant": montant_2,
						"date_suggere": (date_debut - timedelta(days=3)).strftime("%Y-%m-%d"),
						"description": "Solde (40%)"
					}
				]
			})
		
		# Suggestion 3: Paiement en 3 fois pour les gros montants
		if solde_restant >= 500:
			montant_1 = solde_restant * 0.4  # 40% en avance
			montant_2 = solde_restant * 0.4  # 40% avant début
			montant_3 = solde_restant - montant_1 - montant_2  # 20% pendant
			
			milieu_periode = date_debut + timedelta(days=(date_fin - date_debut).days // 2)
			
			suggestions.append({
				"type": "Échelonné (3 fois)",
				"paiements": [
					{
						"montant": montant_1,
						"date_suggere": (date_debut - timedelta(days=21)).strftime("%Y-%m-%d"),
						"description": "Premier acompte (40%)"
					},
					{
						"montant": montant_2,
						"date_suggere": (date_debut - timedelta(days=7)).strftime("%Y-%m-%d"),
						"description": "Deuxième acompte (40%)"
					},
					{
						"montant": montant_3,
						"date_suggere": milieu_periode.strftime("%Y-%m-%d"),
						"description": "Solde (20%)"
					}
				]
			})
		
		return suggestions
		
	except Exception as e:
		frappe.log_error(f"Erreur génération suggestions paiement: {str(e)}")
		return []


@frappe.whitelist()
def mark_paiement_as_paid(paiement_id, reference_paiement=None, notes=None):
	"""Marque un paiement comme payé"""
	try:
		paiement = frappe.get_doc("Paiement Bloc", paiement_id)
		
		# Paiement marqué comme payé
		if reference_paiement:
			paiement.reference_paiement = reference_paiement
		if notes:
			paiement.notes = notes
		
		paiement.save()
		
		return {
			"success": True,
			"message": f"Paiement {paiement_id} marqué comme payé"
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur marquage paiement payé: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_paiement_statistics(proprietaire_id=None, date_debut=None, date_fin=None):
	"""Retourne les statistiques des paiements bloc"""
	try:
		filters = {}
		
		if proprietaire_id:
			filters["proprietaire_id"] = proprietaire_id
		if date_debut:
			filters["date_paiement"] = [">=", date_debut]
		if date_fin:
			if "date_paiement" in filters:
				filters["date_paiement"] = ["between", [date_debut, date_fin]]
			else:
				filters["date_paiement"] = ["<=", date_fin]
		
		paiements = frappe.get_all("Paiement Bloc",
			filters=filters,
			fields=["name", "location_bloc_id", "proprietaire_id", "montant_paiement", 
					"date_paiement", "type_paiement", "methode_paiement"])
		
		# Calculer les statistiques
		total_paiements = len(paiements)
		montant_total = sum([p.montant_paiement for p in paiements])
		montant_paye = sum([p.montant_paiement for p in paiements])
		montant_en_attente = 0
		montant_annule = 0
		
		# Statistiques par statut
		paiements_payes = len(paiements)
		paiements_en_attente = 0
		paiements_annules = 0
		
		# Statistiques par type de paiement
		paiements_uniques = len([p for p in paiements if p.type_paiement == "Unique"])
		paiements_echelonnes = len([p for p in paiements if p.type_paiement == "Échelonné"])
		
		# Statistiques par méthode de paiement
		methodes = {}
		for p in paiements:
			if p.methode_paiement:
				if p.methode_paiement not in methodes:
					methodes[p.methode_paiement] = {"count": 0, "montant": 0}
				methodes[p.methode_paiement]["count"] += 1
				methodes[p.methode_paiement]["montant"] += p.montant_paiement
		
		return {
			"paiements": paiements,
			"statistiques": {
				"total_paiements": total_paiements,
				"montant_total": montant_total,
				"montant_paye": montant_paye,
				"montant_en_attente": montant_en_attente,
				"montant_annule": montant_annule,
				"pourcentage_paye": (montant_paye / montant_total * 100) if montant_total > 0 else 0,
				"paiements_payes": paiements_payes,
				"paiements_en_attente": paiements_en_attente,
				"paiements_annules": paiements_annules,
				"paiements_uniques": paiements_uniques,
				"paiements_echelonnes": paiements_echelonnes,
				"methodes_paiement": methodes
			}
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur statistiques paiements: {str(e)}")
		return {"error": str(e)}