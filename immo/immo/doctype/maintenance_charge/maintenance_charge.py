# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class MaintenanceCharge(Document):
	def validate(self):
		"""Validation métier pour les charges de maintenance"""
		self.validate_apartment()
		self.validate_amount()
	
	def validate_apartment(self):
		"""Vérifier que l'appartement existe"""
		if self.apartment and not frappe.db.exists("Apartment", self.apartment):
			frappe.throw(f"L'appartement {self.apartment} n'existe pas.")
	
	def validate_amount(self):
		"""Vérifier que le montant est positif"""
		if self.amount and self.amount <= 0:
			frappe.throw("Le montant doit être supérieur à 0.") 