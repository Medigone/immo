# Copyright (c) 2024, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Proprietaire(Document):
	"""Doctype pour gérer les propriétaires d'appartements"""
	
	def validate(self):
		"""Validation des données du propriétaire"""
		self.validate_email()
		self.validate_iban()
	
	def validate_email(self):
		"""Valide le format de l'email"""
		if self.email:
			import re
			email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
			if not re.match(email_pattern, self.email):
				frappe.throw("Format d'email invalide")
	
	def validate_iban(self):
		"""Valide le format de l'IBAN"""
		if self.iban:
			# Supprime les espaces et convertit en majuscules
			self.iban = self.iban.replace(" ", "").upper()
			# Validation basique de la longueur IBAN
			if len(self.iban) < 15 or len(self.iban) > 34:
				frappe.throw("Format d'IBAN invalide")
	
	def before_save(self):
		"""Actions avant sauvegarde"""
		# Normalise le nom complet
		if self.nom_complet:
			self.nom_complet = self.nom_complet.strip().title()
	
	def on_update(self):
		"""Actions après mise à jour"""
		# Fonction conservée pour compatibilité
		pass
	

	
	@frappe.whitelist()
	def get_appartements(self):
		"""Retourne la liste des appartements du propriétaire"""
		return frappe.get_all("Appartement",
			filters={"proprietaire_id": self.name},
			fields=["name", "adresse_complete", "nombre_pieces", "surface", "disponible"])
	
	@frappe.whitelist()
	def get_paiements_recents(self, limit=10):
		"""Retourne les paiements récents du propriétaire"""
		return frappe.get_all("Paiement Propriétaire",
			filters={"proprietaire_id": self.name},
			fields=["name", "montant", "date_paiement", "statut", "methode_paiement"],
			order_by="date_paiement desc",
			limit=limit)