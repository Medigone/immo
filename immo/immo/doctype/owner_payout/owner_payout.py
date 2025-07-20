# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import today

class OwnerPayout(Document):
	def validate(self):
		"""Validation métier pour les paiements aux propriétaires"""
		self.validate_owner()
		self.validate_booking()
		self.validate_amount()
		self.validate_status()
	
	def validate_owner(self):
		"""Vérifier que le propriétaire existe"""
		if self.owner and not frappe.db.exists("Owner", self.owner):
			frappe.throw(f"Le propriétaire {self.owner} n'existe pas.")
	
	def validate_booking(self):
		"""Vérifier que la réservation existe et correspond au propriétaire"""
		if self.booking:
			if not frappe.db.exists("Booking", self.booking):
				frappe.throw(f"La réservation {self.booking} n'existe pas.")
			
			# Vérifier que la réservation correspond au propriétaire
			booking_apartment = frappe.get_value("Booking", self.booking, "apartment")
			if booking_apartment:
				apartment_owner = frappe.get_value("Apartment", booking_apartment, "owner")
				if apartment_owner != self.owner:
					frappe.throw("La réservation ne correspond pas au propriétaire sélectionné.")
	
	def validate_amount(self):
		"""Vérifier que le montant est positif"""
		if self.amount_due and self.amount_due <= 0:
			frappe.throw("Le montant dû doit être supérieur à 0.")
	
	def validate_status(self):
		"""Validation du statut"""
		if self.status == "Paid" and not self.payout_date:
			self.payout_date = today()
		
		if self.status == "Cancelled" and self.payout_date:
			self.payout_date = None
	
	def on_update(self):
		"""Actions lors de la mise à jour"""
		if self.status == "Paid" and not self.payout_date:
			self.payout_date = today() 