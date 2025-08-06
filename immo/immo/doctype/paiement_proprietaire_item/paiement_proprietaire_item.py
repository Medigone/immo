# Copyright (c) 2024, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class PaiementProprietaireItem(Document):
	"""Child table doctype for Paiement Proprietaire items in Mensualite"""
	
	def validate(self):
		"""Validate the payment item"""
		self.calculate_net_amount()
	
	def calculate_net_amount(self):
		"""Calculate net amount after transaction fees"""
		if self.montant and self.frais_transaction:
			self.montant_net = self.montant - self.frais_transaction
		else:
			self.montant_net = self.montant or 0