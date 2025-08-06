# Copyright (c) 2024, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate
from datetime import datetime, timedelta


class LocationCourteDuree(Document):
	"""Doctype pour gérer les locations courte durée (réservations journalières)"""
	
	def validate(self):
		"""Validation des données de la location"""
		self.validate_appartement()
		self.validate_dates()
		self.validate_prix()
		self.validate_email()
		self.validate_referent()
	
	def validate_appartement(self):
		"""Valide que l'appartement existe et est disponible"""
		if self.appartement_id:
			appartement = frappe.get_doc("Appartement", self.appartement_id)
			if not appartement.disponible and self.is_new():
				frappe.throw(f"L'appartement {appartement.adresse_complete} n'est pas disponible")
	
	def validate_dates(self):
		"""Valide les dates de location"""
		if self.date_debut and self.date_fin:
			date_debut = getdate(self.date_debut)
			date_fin = getdate(self.date_fin)
			if date_fin <= date_debut:
				frappe.throw("La date de fin doit être postérieure à la date de début")
		

	
	def validate_prix(self):
		"""Valide que les prix sont positifs"""
		if self.prix_journalier_locataire and self.prix_journalier_locataire <= 0:
			frappe.throw("Le prix journalier locataire doit être positif")
		
		if self.prix_journalier_proprietaire and self.prix_journalier_proprietaire <= 0:
			frappe.throw("Le prix journalier propriétaire doit être positif")
		
		if (self.prix_journalier_locataire and self.prix_journalier_proprietaire and 
			self.prix_journalier_proprietaire >= self.prix_journalier_locataire):
			frappe.throw("Le prix propriétaire doit être inférieur au prix locataire")
	
	def validate_email(self):
		"""Valide le format de l'email du locataire"""
		if self.locataire_email:
			import re
			email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
			if not re.match(email_pattern, self.locataire_email):
				frappe.throw("Format d'email invalide pour le locataire")
	
	def validate_referent(self):
		"""Valide que le référent existe et est actif"""
		if self.referent_id:
			referent = frappe.get_doc("Referent", self.referent_id)
			if not referent.actif:
				frappe.throw(f"Le référent {referent.nom_complet} n'est pas actif")
	
	def before_save(self):
		"""Actions avant sauvegarde"""
		# Calcule le nombre de nuits
		self.calculate_nights()
		
		# Calcule les montants et marges
		self.calculate_amounts()
		
		# Calcule la commission du référent
		self.calculate_referent_commission()
		
		# Normalise le nom du locataire
		if self.locataire_nom:
			self.locataire_nom = self.locataire_nom.strip().title()
	
	def calculate_nights(self):
		"""Calcule le nombre de nuits"""
		if self.date_debut and self.date_fin:
			start_date = datetime.strptime(str(self.date_debut), "%Y-%m-%d")
			end_date = datetime.strptime(str(self.date_fin), "%Y-%m-%d")
			self.nombre_nuits = (end_date - start_date).days
	
	def calculate_amounts(self):
		"""Calcule les montants totaux et la marge"""
		if self.nombre_nuits and self.prix_journalier_locataire and self.prix_journalier_proprietaire:
			self.montant_total_locataire = self.nombre_nuits * self.prix_journalier_locataire
			self.montant_total_proprietaire = self.nombre_nuits * self.prix_journalier_proprietaire
			self.marge_totale = self.montant_total_locataire - self.montant_total_proprietaire
	
	def calculate_referent_commission(self):
		"""Calcule la commission du référent"""
		if self.referent_id and self.marge_totale:
			referent = frappe.get_doc("Referent", self.referent_id)
			if referent.pourcentage_commission_defaut:
				self.commission_referent = (self.marge_totale * referent.pourcentage_commission_defaut) / 100
		else:
			self.commission_referent = 0
	
	def on_update(self):
		"""Actions après mise à jour"""
		# Crée la commission si le statut devient confirmé et qu'il y a un référent
		if (self.statut == "Confirmé" and self.has_value_changed("statut") and 
			self.referent_id and self.commission_referent > 0):
			self.create_commission()
	
	def create_commission(self):
		"""Crée la commission pour le référent"""
		# Vérifie si la commission n'existe pas déjà
		existing_commission = frappe.get_all("Commission",
			filters={"location_courte_duree_id": self.name})
		
		if not existing_commission:
			referent = frappe.get_doc("Referent", self.referent_id)
			
			# Vérification que le référent a un pourcentage de commission défini
			if not referent.pourcentage_commission_defaut:
				frappe.throw(f"Le référent {referent.nom_complet} n'a pas de pourcentage de commission défini")
			
			commission = frappe.get_doc({
				"doctype": "Commission",
				"location_courte_duree_id": self.name,
				"referent_id": self.referent_id,
				"montant_commission": self.commission_referent,
				"pourcentage_commission": referent.pourcentage_commission_defaut,
				"statut_paiement": "En attente",
				"date_creation": self.date_fin
			})
			commission.insert()
			frappe.msgprint(f"Commission créée pour le référent {referent.nom_complet}")
	
	@frappe.whitelist()
	def get_commission(self):
		"""Retourne la commission associée à cette location"""
		return frappe.get_all("Commission",
			filters={"location_courte_duree_id": self.name},
			fields=["name", "montant_commission", "pourcentage_commission", "statut_paiement", "date_creation", "date_paiement"])
	
	@frappe.whitelist()
	def get_paiements_locataire(self):
		"""Retourne les paiements du locataire"""
		return frappe.get_all("Paiement Locataire",
			filters={"location_courte_duree_id": self.name},
			fields=["name", "montant", "date_paiement", "statut", "methode_paiement"],
			order_by="date_paiement desc")
	
	@frappe.whitelist()
	def get_paiements_proprietaire(self):
		"""Retourne les paiements au propriétaire"""
		return frappe.get_all("Paiement Propriétaire",
			filters={"location_courte_duree_id": self.name},
			fields=["name", "montant", "date_paiement", "statut", "methode_paiement"],
			order_by="date_paiement desc")
	
	@frappe.whitelist()
	def calculate_net_margin(self):
		"""Calcule la marge nette après commission référent"""
		net_margin = self.marge_totale - (self.commission_referent or 0)
		return {
			"marge_totale": self.marge_totale,
			"commission_referent": self.commission_referent or 0,
			"marge_nette": net_margin
		}
	
	def on_cancel(self):
		"""Actions lors de l'annulation"""
		# Supprime la commission associée
		commissions = frappe.get_all("Commission", 
			filters={"location_courte_duree_id": self.name})
		
		for commission in commissions:
			commission_doc = frappe.get_doc("Commission", commission.name)
			if commission_doc.statut != "Payé":
				commission_doc.cancel()
				commission_doc.delete()
	
	@frappe.whitelist()
	def check_availability(self):
		"""Vérifie la disponibilité de l'appartement pour les dates données"""
		if not self.appartement_id or not self.date_debut or not self.date_fin:
			return {"available": False, "message": "Données incomplètes"}
		
		# Vérifie les conflits avec d'autres locations courte durée
		conflicting_short = frappe.get_all("Location Courte Duree",
			filters={
				"appartement_id": self.appartement_id,
				"statut": ["in", ["Confirmé", "En cours"]],
				"name": ["!=", self.name] if not self.is_new() else None
			})
		
		for location in conflicting_short:
			loc_doc = frappe.get_doc("Location Courte Duree", location.name)
			if (self.date_debut <= loc_doc.date_fin and self.date_fin >= loc_doc.date_debut):
				return {
					"available": False, 
					"message": f"Conflit avec la location {loc_doc.name}"
				}
		
		# Vérifie les conflits avec les locations longue durée
		conflicting_long = frappe.get_all("Location Longue Durée",
			filters={
				"appartement_id": self.appartement_id,
				"statut": "Actif"
			})
		
		for location in conflicting_long:
			loc_doc = frappe.get_doc("Location Longue Durée", location.name)
			if (self.date_debut <= loc_doc.date_fin and self.date_fin >= loc_doc.date_debut):
				return {
					"available": False, 
					"message": f"Conflit avec la location longue durée {loc_doc.name}"
				}
		
		return {"available": True, "message": "Appartement disponible"}