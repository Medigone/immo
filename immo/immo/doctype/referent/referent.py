# Copyright (c) 2024, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
import re


class Referent(Document):
	"""Doctype pour gérer les référents et leurs commissions"""
	
	def validate(self):
		"""Validation des données du référent"""
		self.validate_email()
		self.validate_commission_percentage()
	
	def validate_email(self):
		"""Valide le format de l'email"""
		if self.email:
			email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
			if not re.match(email_pattern, self.email):
				frappe.throw(_("Format d'email invalide"))
	
	def validate_commission_percentage(self):
		"""Valide le pourcentage de commission"""
		if self.pourcentage_commission_defaut is not None:
			if self.pourcentage_commission_defaut < 0 or self.pourcentage_commission_defaut > 100:
				frappe.throw(_("Le pourcentage de commission doit être entre 0 et 100"))
	
	def before_save(self):
		"""Actions avant sauvegarde"""
		# Normalise le nom complet
		if self.nom_complet:
			self.nom_complet = self.nom_complet.strip().title()
	
	def on_update(self):
		"""Actions après mise à jour"""
		# Si le référent devient inactif, met à jour les locations courtes durée en cours
		if not self.actif:
			self.update_active_short_term_rentals()
	
	def update_active_short_term_rentals(self):
		"""Met à jour les locations courtes durée actives si le référent devient inactif"""
		active_rentals = frappe.get_all(
			"Location Courte Duree",
			filters={
				"referent_id": self.name,
				"statut": ["in", ["Brouillon", "Confirmé"]]
			},
			fields=["name"]
		)
		
		for rental in active_rentals:
			rental_doc = frappe.get_doc("Location Courte Duree", rental.name)
			rental_doc.add_comment(
				"Comment",
				f"Référent {self.nom_complet} désactivé - Commission mise à jour"
			)
	
	@frappe.whitelist()
	def get_commissions(self):
		"""Récupère toutes les commissions du référent"""
		return frappe.get_all(
			"Commission",
			filters={"referent_id": self.name},
			fields=[
				"name", "location_courte_duree_id", "montant_commission",
				"pourcentage_commission", "date_creation", "statut_paiement"
			],
			order_by="date_creation desc"
		)
	
	@frappe.whitelist()
	def get_total_commissions(self, start_date=None, end_date=None):
		"""Calcule le total des commissions sur une période"""
		filters = {"referent_id": self.name}
		
		if start_date:
			filters["date_creation"] = [">=", start_date]
		if end_date:
			if "date_creation" in filters:
				filters["date_creation"] = ["between", [start_date, end_date]]
			else:
				filters["date_creation"] = ["<=", end_date]
		
		commissions = frappe.get_all(
			"Commission",
			filters=filters,
			fields=["montant_commission", "statut_paiement"]
		)
		
		total_commissions = sum(c.montant_commission for c in commissions)
		commissions_payees = sum(
			c.montant_commission for c in commissions 
			if c.statut_paiement == "Payé"
		)
		commissions_en_attente = total_commissions - commissions_payees
		
		return {
			"total_commissions": total_commissions,
			"commissions_payees": commissions_payees,
			"commissions_en_attente": commissions_en_attente,
			"nombre_commissions": len(commissions)
		}
	
	@frappe.whitelist()
	def get_recent_short_term_rentals(self, limit=10):
		"""Récupère les locations courtes durée récentes du référent"""
		return frappe.get_all(
			"Location Courte Duree",
			filters={"referent_id": self.name},
			fields=[
				"name", "appartement_id", "locataire_nom", "date_debut",
				"date_fin", "montant_total_locataire", "commission_referent", "statut"
			],
			order_by="date_debut desc",
			limit=limit
		)
	
	@frappe.whitelist()
	def calculate_performance_metrics(self, year=None):
		"""Calcule les métriques de performance du référent"""
		if not year:
			year = frappe.utils.nowdate()[:4]
		
		start_date = f"{year}-01-01"
		end_date = f"{year}-12-31"
		
		# Récupère les locations courtes durée de l'année
		rentals = frappe.get_all(
			"Location Courte Duree",
			filters={
				"referent_id": self.name,
				"date_debut": ["between", [start_date, end_date]]
			},
			fields=[
				"montant_total_locataire", "commission_referent",
				"nombre_nuits", "statut"
			]
		)
		
		confirmed_rentals = [r for r in rentals if r.statut in ["Confirmé", "Terminé"]]
		
		total_revenue = sum(r.montant_total_locataire for r in confirmed_rentals)
		total_commission = sum(r.commission_referent for r in confirmed_rentals)
		total_nights = sum(r.nombre_nuits for r in confirmed_rentals)
		
		return {
			"annee": year,
			"nombre_locations": len(confirmed_rentals),
			"chiffre_affaires_genere": total_revenue,
			"total_commissions": total_commission,
			"total_nuits_vendues": total_nights,
			"commission_moyenne_par_location": total_commission / len(confirmed_rentals) if confirmed_rentals else 0,
			"taux_commission_moyen": (total_commission / total_revenue * 100) if total_revenue > 0 else 0
		}