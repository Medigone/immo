# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Owner(Document):
	def validate(self):
		"""Validation métier pour le propriétaire"""
		self.validate_name()
		self.validate_pricing()
	
	def validate_name(self):
		"""Vérifier que le nom complet est renseigné"""
		if self.full_name and len(self.full_name.strip()) < 2:
			frappe.throw("Le nom complet doit contenir au moins 2 caractères.")
	
	def validate_pricing(self):
		"""Validation pour le propriétaire"""
		pass 