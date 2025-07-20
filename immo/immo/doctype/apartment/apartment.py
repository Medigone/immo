# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class Apartment(Document):
	def validate(self):
		"""Validation métier pour l'appartement"""
		self.validate_owner()
		self.validate_pricing()
		self.validate_availability()
	
	def validate_owner(self):
		"""Vérifier que le propriétaire est renseigné"""
		if not self.owner:
			frappe.msgprint("Attention : Aucun propriétaire n'est renseigné pour cet appartement.")
	
	def validate_pricing(self):
		"""Vérifier que les prix sont positifs"""
		if self.default_price_per_night and self.default_price_per_night <= 0:
			frappe.throw("Le prix par nuit par défaut doit être supérieur à 0.")
		
		if self.custom_price and self.custom_price <= 0:
			frappe.throw("Le prix personnalisé doit être supérieur à 0.")
	
	def validate_availability(self):
		"""Vérifier la disponibilité"""
		if not self.is_available:
			# Vérifier s'il y a des réservations actives
			active_bookings = frappe.get_all("Booking", 
				filters={
					"apartment": self.name,
					"status": "Confirmed"
				})
			if active_bookings:
				frappe.throw("Impossible de marquer comme indisponible : il y a des réservations actives.")
	
	def get_effective_price(self, date=None):
		"""Obtenir le prix effectif pour une date donnée"""
		if date:
			# Vérifier s'il y a une règle de prix pour cette date
			pricing_rule = frappe.get_value("Pricing Rule", {
				"apartment": self.name,
				"from_date": ["<=", date],
				"to_date": [">=", date]
			}, "custom_price")
			
			if pricing_rule:
				return pricing_rule
		
		# Retourner le prix personnalisé ou le prix par défaut de l'appartement
		if self.custom_price:
			return self.custom_price
		
		return self.default_price_per_night or 0
	
	def on_update(self):
		"""Actions après mise à jour"""
		self.update_booking_prices()
	
	def update_booking_prices(self):
		"""Mettre à jour les prix des réservations futures"""
		future_bookings = frappe.get_all("Booking", 
			filters={
				"apartment": self.name,
				"status": "Confirmed",
				"start_date": [">=", frappe.utils.today()]
			})
		
		for booking in future_bookings:
			booking_doc = frappe.get_doc("Booking", booking.name)
			booking_doc.save()  # Cela déclenchera la validation et le recalcul 