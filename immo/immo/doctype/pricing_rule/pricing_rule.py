# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import getdate

class PricingRule(Document):
	def validate(self):
		"""Validation métier pour les règles de prix"""
		self.validate_dates()
		self.validate_apartment()
		self.validate_price()
		self.validate_overlap()
	
	def validate_dates(self):
		"""Vérifier la validité des dates"""
		if self.from_date and self.to_date:
			from_date = getdate(self.from_date)
			to_date = getdate(self.to_date)
			
			if to_date <= from_date:
				frappe.throw("La date de fin doit être après la date de début.")
	
	def validate_apartment(self):
		"""Vérifier que l'appartement existe"""
		if self.apartment and not frappe.db.exists("Apartment", self.apartment):
			frappe.throw(f"L'appartement {self.apartment} n'existe pas.")
	
	def validate_price(self):
		"""Vérifier que le prix est positif"""
		if self.custom_price and self.custom_price <= 0:
			frappe.throw("Le prix personnalisé doit être supérieur à 0.")
	
	def validate_overlap(self):
		"""Vérifier qu'il n'y a pas de chevauchement avec d'autres règles"""
		if self.apartment and self.from_date and self.to_date:
			overlapping_rules = frappe.get_all("Pricing Rule", 
				filters={
					"apartment": self.apartment,
					"name": ["!=", self.name] if self.name else ["!=", ""]
				},
				or_filters=[
					{
						"from_date": ["<=", self.from_date],
						"to_date": [">", self.from_date]
					},
					{
						"from_date": ["<", self.to_date],
						"to_date": [">=", self.to_date]
					},
					{
						"from_date": [">=", self.from_date],
						"to_date": ["<=", self.to_date]
					}
				])
			
			if overlapping_rules:
				frappe.throw("Il y a un chevauchement avec une autre règle de prix pour cette période.") 