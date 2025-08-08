# -*- coding: utf-8 -*-
# Copyright (c) 2024, IntraPro and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt, getdate, add_days
from datetime import datetime, timedelta

@frappe.whitelist()
def get_bloc_dashboard_data(location_bloc_id):
	"""Retourne les données du dashboard pour une location bloc"""
	try:
		location_bloc = frappe.get_doc("Location Bloc", location_bloc_id)
		
		# Récupérer toutes les sous-locations
		sous_locations = frappe.get_all("Location Courte Duree",
			filters={"location_bloc_id": location_bloc_id, "docstatus": ["!=", 2]},
			fields=["name", "locataire_nom", "date_debut", "date_fin", "nombre_nuits", 
					"montant_total_locataire", "marge_sur_bloc"],
			order_by="date_debut")
		
		# Récupérer les paiements
		paiements = frappe.get_all("Paiement Bloc",
			filters={"location_bloc_id": location_bloc_id, "docstatus": ["!=", 2]},
			fields=["name", "montant_paiement", "date_paiement", "type_paiement"],
			order_by="date_paiement")
		
		# Calculer les métriques
		total_nuits_occupees = sum([sl.nombre_nuits for sl in sous_locations])
		total_revenus = sum([sl.montant_total_locataire for sl in sous_locations])
		total_marge = sum([sl.marge_sur_bloc for sl in sous_locations])
		total_paye = sum([p.montant_paiement for p in paiements])
		
		# Générer le calendrier d'occupation
		calendrier = generate_occupation_calendar(location_bloc, sous_locations)
		
		return {
			"location_bloc": location_bloc.as_dict(),
			"sous_locations": sous_locations,
			"paiements": paiements,
			"metriques": {
				"total_nuits_occupees": total_nuits_occupees,
				"total_revenus": total_revenus,
				"total_marge": total_marge,
				"total_paye": total_paye,
				"solde_restant": flt(location_bloc.montant_total_proprietaire) - total_paye,
				"taux_occupation_reel": (total_nuits_occupees / location_bloc.nombre_nuits_total * 100) if location_bloc.nombre_nuits_total > 0 else 0,
				"rentabilite_reelle": (total_marge / location_bloc.montant_total_proprietaire * 100) if location_bloc.montant_total_proprietaire > 0 else 0
			},
			"calendrier": calendrier
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur dashboard Location Bloc {location_bloc_id}: {str(e)}")
		return {"error": str(e)}


def generate_occupation_calendar(location_bloc, sous_locations):
	"""Génère un calendrier d'occupation pour la location bloc"""
	try:
		calendrier = []
		current_date = getdate(location_bloc.date_debut_bloc)
		end_date = getdate(location_bloc.date_fin_bloc)
		
		while current_date <= end_date:
			# Vérifier si cette date est occupée
			occupe = False
			locataire = None
			location_id = None
			
			for sl in sous_locations:
				if (getdate(sl.date_debut) <= current_date < getdate(sl.date_fin)):
					occupe = True
					locataire = sl.locataire_nom
					location_id = sl.name
					break
			
			calendrier.append({
				"date": current_date.strftime("%Y-%m-%d"),
				"occupe": occupe,
				"locataire": locataire,
				"location_id": location_id
			})
			
			current_date = current_date + timedelta(days=1)
		
		return calendrier
		
	except Exception as e:
		frappe.log_error(f"Erreur génération calendrier: {str(e)}")
		return []


@frappe.whitelist()
def create_paiement_bloc(location_bloc_id, montant, date_paiement, type_paiement="Unique", methode_paiement=None, reference=None, notes=None):
	"""Crée un nouveau paiement bloc"""
	try:
		location_bloc = frappe.get_doc("Location Bloc", location_bloc_id)
		
		paiement = frappe.new_doc("Paiement Bloc")
		paiement.location_bloc_id = location_bloc_id
		paiement.proprietaire_id = location_bloc.proprietaire_id
		paiement.appartement_id = location_bloc.appartement_id
		paiement.montant_paiement = flt(montant)
		paiement.date_paiement = date_paiement
		paiement.type_paiement = type_paiement

		
		if methode_paiement:
			paiement.methode_paiement = methode_paiement
		if reference:
			paiement.reference_paiement = reference
		if notes:
			paiement.notes = notes
		
		paiement.insert()
		
		return {
			"success": True,
			"paiement_id": paiement.name,
			"message": f"Paiement bloc créé: {paiement.name}"
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur création paiement bloc: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_available_periods(appartement_id, exclude_bloc_id=None):
	"""Retourne les périodes disponibles pour créer une location bloc"""
	try:
		# Récupérer toutes les locations bloc existantes pour cet appartement
		filters = {
			"appartement_id": appartement_id,
			"docstatus": ["!=", 2]
		}
		
		if exclude_bloc_id:
			filters["name"] = ["!=", exclude_bloc_id]
		
		blocs_existants = frappe.get_all("Location Bloc",
			filters=filters,
			fields=["name", "date_debut_bloc", "date_fin_bloc"])
		
		# Récupérer les locations longue durée
		locations_longues = frappe.get_all("Location Longue Duree",
			filters={
				"appartement_id": appartement_id,
				"docstatus": ["!=", 2]
			},
			fields=["name", "date_debut", "date_fin"])
		
		return {
			"blocs_existants": blocs_existants,
			"locations_longues": locations_longues
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur récupération périodes disponibles: {str(e)}")
		return {"error": str(e)}


@frappe.whitelist()
def get_bloc_performance_metrics(appartement_id=None, proprietaire_id=None, date_debut=None, date_fin=None):
	"""Retourne les métriques de performance des locations bloc"""
	try:
		filters = {"docstatus": ["!=", 2]}
		
		if appartement_id:
			filters["appartement_id"] = appartement_id
		if proprietaire_id:
			filters["proprietaire_id"] = proprietaire_id
		if date_debut:
			filters["date_debut_bloc"] = [">=", date_debut]
		if date_fin:
			filters["date_fin_bloc"] = ["<=", date_fin]
		
		blocs = frappe.get_all("Location Bloc",
			filters=filters,
			fields=["name", "appartement_id", "proprietaire_id", "date_debut_bloc", "date_fin_bloc",
					"nombre_nuits_total", "montant_total_proprietaire", "prix_proprietaire_par_nuit",
					"total_encaisse", "marge_totale", "taux_occupation", "rentabilite_pourcentage"])
		
		# Calculer les métriques globales
		total_blocs = len(blocs)
		total_nuits = sum([b.nombre_nuits_total for b in blocs])
		total_revenus = sum([b.total_encaisse for b in blocs])
		total_marges = sum([b.marge_totale for b in blocs])
		total_paiements_proprietaires = sum([b.montant_total_proprietaire for b in blocs])
		
		# Calculer les moyennes
		taux_occupation_moyen = sum([b.taux_occupation for b in blocs]) / total_blocs if total_blocs > 0 else 0
		rentabilite_moyenne = sum([b.rentabilite_pourcentage for b in blocs]) / total_blocs if total_blocs > 0 else 0
		prix_moyen_par_nuit = total_revenus / total_nuits if total_nuits > 0 else 0
		
		return {
			"blocs": blocs,
			"metriques_globales": {
				"total_blocs": total_blocs,
				"total_nuits": total_nuits,
				"total_revenus": total_revenus,
				"total_marges": total_marges,
				"total_paiements_proprietaires": total_paiements_proprietaires,
				"taux_occupation_moyen": taux_occupation_moyen,
				"rentabilite_moyenne": rentabilite_moyenne,
				"prix_moyen_par_nuit": prix_moyen_par_nuit
			}
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur métriques performance bloc: {str(e)}")
		return {"error": str(e)}