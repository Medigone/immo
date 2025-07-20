# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import getdate, add_days, date_diff

class Booking(Document):
	def validate(self):
		"""Validation métier pour la réservation"""
		self.validate_dates()
		self.validate_availability()
		self.validate_apartment()
		self.validate_guest()
		self.calculate_fields()
	
	def validate_dates(self):
		"""Vérifier la validité des dates"""
		if self.start_date and self.end_date:
			start = getdate(self.start_date)
			end = getdate(self.end_date)
			today = getdate()
			
			# Vérifier que la date de début est dans le futur
			if start < today:
				frappe.throw("La date de début doit être dans le futur.")
			
			# Vérifier que la date de fin est après la date de début
			if end <= start:
				frappe.throw("La date de fin doit être après la date de début.")
			
			# Vérifier que la durée n'est pas trop longue (optionnel)
			if date_diff(end, start) > 365:
				frappe.throw("La réservation ne peut pas dépasser 365 jours.")
	
	def validate_availability(self):
		"""Vérifier la disponibilité de l'appartement"""
		if self.apartment and self.start_date and self.end_date:
			# Vérifier que l'appartement est disponible
			apartment = frappe.get_doc("Apartment", self.apartment)
			if not apartment.is_available:
				frappe.throw("Cet appartement n'est pas disponible.")
			
			# Vérifier qu'il n'y a pas de chevauchement avec d'autres réservations
			overlapping_bookings = frappe.get_all("Booking", 
				filters={
					"apartment": self.apartment,
					"status": ["in", ["Pending", "Confirmed"]],
					"name": ["!=", self.name] if self.name else ["!=", ""]
				},
				or_filters=[
					{
						"start_date": ["<=", self.start_date],
						"end_date": [">", self.start_date]
					},
					{
						"start_date": ["<", self.end_date],
						"end_date": [">=", self.end_date]
					},
					{
						"start_date": [">=", self.start_date],
						"end_date": ["<=", self.end_date]
					}
				])
			
			if overlapping_bookings:
				frappe.throw("Il y a un chevauchement avec une autre réservation pour cette période.")
	
	def validate_apartment(self):
		"""Vérifier que l'appartement existe"""
		if self.apartment and not frappe.db.exists("Apartment", self.apartment):
			frappe.throw(f"L'appartement {self.apartment} n'existe pas.")
	
	def validate_guest(self):
		"""Vérifier que l'invité existe"""
		if self.guest and not frappe.db.exists("User", self.guest):
			frappe.throw(f"L'invité {self.guest} n'existe pas.")
	
	def calculate_fields(self):
		"""Calculer les champs automatiques"""
		if self.start_date and self.end_date:
			self.calculate_total_nights()
			self.calculate_prices()
	
	def calculate_total_nights(self):
		"""Calculer le nombre total de nuits"""
		if self.start_date and self.end_date:
			start = getdate(self.start_date)
			end = getdate(self.end_date)
			self.total_nights = date_diff(end, start)
	
	def calculate_prices(self):
		"""Calculer les prix automatiquement"""
		if self.apartment and self.total_nights:
			apartment = frappe.get_doc("Apartment", self.apartment)
			
			# Calculer le prix au propriétaire
			price_per_night = apartment.get_effective_price(self.start_date)
			self.price_to_owner = price_per_night * self.total_nights
			
			# Calculer mon prix (avec markup de 20% par défaut)
			markup_percentage = 20  # Peut être configuré globalement
			markup_multiplier = 1 + (markup_percentage / 100)
			self.my_price = self.price_to_owner * markup_multiplier
			
			# Calculer la marge
			self.margin = self.my_price - self.price_to_owner
	
	def on_submit(self):
		"""Actions lors de la soumission"""
		if self.status == "Confirmed":
			self.create_owner_payout()
	
	def on_update(self):
		"""Actions lors de la mise à jour"""
		if self.status == "Confirmed":
			self.create_owner_payout()
	
	def create_owner_payout(self):
		"""Créer automatiquement un paiement au propriétaire"""
		if not self.price_to_owner:
			return
		
		# Vérifier s'il existe déjà un paiement pour cette réservation
		existing_payout = frappe.get_value("Owner Payout", {
			"booking": self.name
		}, "name")
		
		if not existing_payout:
			# Récupérer le propriétaire de l'appartement
			owner = frappe.get_value("Apartment", self.apartment, "owner")
			
			if owner:
				payout_doc = frappe.new_doc("Owner Payout")
				payout_doc.owner = owner
				payout_doc.booking = self.name
				payout_doc.amount_due = self.price_to_owner
				payout_doc.status = "Pending"
				payout_doc.insert()
	
	def on_cancel(self):
		"""Actions lors de l'annulation"""
		# Annuler le paiement au propriétaire si il existe
		payout = frappe.get_value("Owner Payout", {
			"booking": self.name
		}, "name")
		
		if payout:
			payout_doc = frappe.get_doc("Owner Payout", payout)
			payout_doc.status = "Cancelled"
			payout_doc.save() 