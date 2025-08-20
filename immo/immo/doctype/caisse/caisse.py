# Copyright (c) 2024, Wezri and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now


class Caisse(Document):
	"""DocType singleton pour la gestion de la caisse principale."""
	
	def validate(self):
		"""Validation du document Caisse."""
		self.date_derniere_maj = now()
		
		# Validation du solde
		if hasattr(self, 'solde_actuel') and self.solde_actuel and self.solde_actuel < 0:
			frappe.throw("Le solde de la caisse ne peut pas être négatif")
	
	def before_save(self):
		"""Actions avant sauvegarde."""
		self.date_derniere_maj = now()
	
	@staticmethod
	def get_solde_actuel():
		"""Récupère le solde actuel de la caisse."""
		caisse = frappe.get_single("Caisse")
		return caisse.solde_actuel or 0
	
	@staticmethod
	def update_solde(nouveau_solde):
		"""Met à jour le solde de la caisse."""
		caisse = frappe.get_single("Caisse")
		caisse.solde_actuel = nouveau_solde
		caisse.date_derniere_maj = now()
		caisse.save()
		frappe.db.commit()
	
	@staticmethod
	def ajouter_montant(montant):
		"""Ajoute un montant au solde de la caisse."""
		if montant <= 0:
			frappe.throw("Le montant à ajouter doit être positif")
		
		solde_actuel = Caisse.get_solde_actuel()
		nouveau_solde = solde_actuel + montant
		Caisse.update_solde(nouveau_solde)
		return nouveau_solde
	
	@staticmethod
	def retirer_montant(montant):
		"""Retire un montant du solde de la caisse."""
		if montant <= 0:
			frappe.throw("Le montant à retirer doit être positif")
		
		solde_actuel = Caisse.get_solde_actuel()
		
		if solde_actuel < montant:
			frappe.throw(f"Solde insuffisant. Solde actuel: {solde_actuel}, Montant demandé: {montant}")
		
		nouveau_solde = solde_actuel - montant
		Caisse.update_solde(nouveau_solde)
		return nouveau_solde
	
	@staticmethod
	def valider_solde_suffisant(montant):
		"""Valide si le solde est suffisant pour un retrait."""
		solde_actuel = Caisse.get_solde_actuel()
		return solde_actuel >= montant