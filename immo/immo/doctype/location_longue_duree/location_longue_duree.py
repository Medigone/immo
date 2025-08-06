# Copyright (c) 2024, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class LocationLongueDuree(Document):
	"""Doctype pour gérer les locations longue durée (contrats mensuels)"""
	
	def validate(self):
		"""Validation des données de la location"""
		self.validate_appartement()
		self.validate_dates()
		self.validate_loyers()
		self.validate_email()
	
	def validate_appartement(self):
		"""Valide que l'appartement existe et est disponible"""
		if self.appartement_id:
			appartement = frappe.get_doc("Appartement", self.appartement_id)
			if not appartement.disponible and self.is_new():
				frappe.throw(f"L'appartement {appartement.adresse_complete} n'est pas disponible")
	
	def validate_dates(self):
		"""Valide les dates de location"""
		if self.date_debut and self.date_fin:
			if self.date_fin <= self.date_debut:
				frappe.throw("La date de fin doit être postérieure à la date de début")
		
		if self.date_debut and self.date_debut < datetime.now().date():
			if self.is_new():
				frappe.throw("La date de début ne peut pas être dans le passé")
	
	def validate_loyers(self):
		"""Valide que les loyers sont positifs"""
		if self.loyer_mensuel_locataire and self.loyer_mensuel_locataire <= 0:
			frappe.throw("Le loyer mensuel locataire doit être positif")
		
		if self.loyer_mensuel_proprietaire and self.loyer_mensuel_proprietaire <= 0:
			frappe.throw("Le loyer mensuel propriétaire doit être positif")
		
		if (self.loyer_mensuel_locataire and self.loyer_mensuel_proprietaire and 
			self.loyer_mensuel_proprietaire >= self.loyer_mensuel_locataire):
			frappe.throw("Le loyer propriétaire doit être inférieur au loyer locataire")
	
	def validate_email(self):
		"""Valide le format de l'email du locataire"""
		if self.locataire_email:
			import re
			email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
			if not re.match(email_pattern, self.locataire_email):
				frappe.throw("Format d'email invalide pour le locataire")
	
	def before_save(self):
		"""Actions avant sauvegarde"""
		# Calcule les marges automatiquement
		self.calculate_margins()
		
		# Normalise le nom du locataire
		if self.locataire_nom:
			self.locataire_nom = self.locataire_nom.strip().title()
	
	def calculate_margins(self):
		"""Calcule les marges initiale et mensuelle"""
		if self.loyer_mensuel_locataire and self.loyer_mensuel_proprietaire:
			# Marge initiale = généralement 1 mois de différence
			self.marge_initiale = self.loyer_mensuel_locataire - self.loyer_mensuel_proprietaire
			# Marge mensuelle = différence mensuelle
			self.marge_mensuelle = self.loyer_mensuel_locataire - self.loyer_mensuel_proprietaire
	
	def on_update(self):
		"""Actions après mise à jour"""
		# Crée les mensualités si le statut devient actif
		if self.statut == "Actif" and self.has_value_changed("statut"):
			self.create_mensualites()
	
	def create_mensualites(self):
		"""Crée les mensualités pour la période de location"""
		if not self.date_debut or not self.date_fin:
			return
		
		# Supprime les anciennes mensualités si elles existent
		frappe.db.delete("Mensualite", {"location_longue_duree_id": self.name})
		
		current_date = self.date_debut
		while current_date <= self.date_fin:
			mensualite = frappe.get_doc({
				"doctype": "Mensualite",
				"location_longue_duree_id": self.name,
				"date_echeance": current_date,
				"montant_locataire": self.loyer_mensuel_locataire,
				"montant_proprietaire": self.loyer_mensuel_proprietaire,
				"statut_paiement_locataire": "En attente",
				"statut_paiement_proprietaire": "En attente"
			})
			mensualite.insert()
			
			# Passe au mois suivant
			current_date = current_date + relativedelta(months=1)
		
		frappe.msgprint(f"Mensualités créées pour la location {self.name}")
	
	@frappe.whitelist()
	def get_mensualites(self):
		"""Retourne les mensualités de la location"""
		return frappe.get_all("Mensualite",
			filters={"location_longue_duree_id": self.name},
			fields=["name", "date_echeance", "montant_locataire", "montant_proprietaire", 
					"statut_paiement_locataire", "statut_paiement_proprietaire"],
			order_by="date_echeance")
	
	@frappe.whitelist()
	def get_paiements_locataire(self):
		"""Retourne les paiements du locataire"""
		return frappe.get_all("Paiement Locataire",
			filters={"location_longue_duree_id": self.name},
			fields=["name", "montant", "date_paiement", "statut", "methode_paiement"],
			order_by="date_paiement desc")
	
	@frappe.whitelist()
	def get_paiements_proprietaire(self):
		"""Retourne les paiements au propriétaire"""
		return frappe.get_all("Paiement Propriétaire",
			filters={"location_longue_duree_id": self.name},
			fields=["name", "montant", "date_paiement", "statut", "methode_paiement"],
			order_by="date_paiement desc")
	
	@frappe.whitelist()
	def calculate_total_margin(self):
		"""Calcule la marge totale sur la période"""
		if not self.date_debut or not self.date_fin:
			return 0
		
		# Calcule le nombre de mois
		start_date = datetime.strptime(str(self.date_debut), "%Y-%m-%d")
		end_date = datetime.strptime(str(self.date_fin), "%Y-%m-%d")
		nb_months = (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)
		
		total_margin = self.marge_initiale + (self.marge_mensuelle * nb_months)
		return total_margin
	
	def on_cancel(self):
		"""Actions lors de l'annulation"""
		# Supprime les mensualités associées
		frappe.db.delete("Mensualite", {"location_longue_duree_id": self.name})
		
		# Met à jour le statut de l'appartement
		appartement = frappe.get_doc("Appartement", self.appartement_id)
		appartement.disponible = 1
		appartement.save()