# Copyright (c) 2024, Frappe Technologies and Contributors
# See license.txt

import frappe
import unittest
from datetime import datetime, timedelta


class TestLocationLongueDuree(unittest.TestCase):
	"""Tests pour le doctype Location Longue Durée"""
	
	def setUp(self):
		"""Configuration avant chaque test"""
		# Nettoie les données de test
		frappe.db.delete("Location Longue Durée", {"locataire_nom": ["like", "Test%"]})
		frappe.db.delete("Appartement", {"adresse_complete": ["like", "Test%"]})
		frappe.db.delete("Propriétaire", {"nom_complet": ["like", "Test%"]})
		frappe.db.commit()
		
		# Crée un propriétaire de test
		self.proprietaire = frappe.get_doc({
			"doctype": "Propriétaire",
			"nom_complet": "Test Propriétaire Location",
			"email": "test.location@example.com",
			"actif": 1
		})
		self.proprietaire.insert()
		
		# Crée un appartement de test
		self.appartement = frappe.get_doc({
			"doctype": "Appartement",
			"proprietaire_id": self.proprietaire.name,
			"adresse_complete": "Test 789 Rue de la Location",
			"nombre_pieces": 2,
			"surface": 50.0,
			"prix_mensuel_defaut": 1000.0,
			"disponible": 1
		})
		self.appartement.insert()
	
	def test_create_location_longue_duree(self):
		"""Test de création d'une location longue durée"""
		today = datetime.now().date()
		future_date = today + timedelta(days=365)
		
		location = frappe.get_doc({
			"doctype": "Location Longue Durée",
			"appartement_id": self.appartement.name,
			"locataire_nom": "Test Locataire",
			"locataire_email": "locataire@example.com",
			"locataire_telephone": "0123456789",
			"date_debut": today,
			"date_fin": future_date,
			"loyer_mensuel_locataire": 1200.0,
			"loyer_mensuel_proprietaire": 1000.0,
			"statut": "Brouillon"
		})
		location.insert()
		
		self.assertEqual(location.appartement_id, self.appartement.name)
		self.assertEqual(location.locataire_nom, "Test Locataire")
		self.assertEqual(location.marge_mensuelle, 200.0)
		self.assertEqual(location.marge_initiale, 200.0)
	
	def test_margin_calculation(self):
		"""Test du calcul des marges"""
		location = frappe.get_doc({
			"doctype": "Location Longue Durée",
			"appartement_id": self.appartement.name,
			"locataire_nom": "Test Marge",
			"loyer_mensuel_locataire": 1500.0,
			"loyer_mensuel_proprietaire": 1200.0
		})
		location.insert()
		
		self.assertEqual(location.marge_mensuelle, 300.0)
		self.assertEqual(location.marge_initiale, 300.0)
	
	def test_date_validation(self):
		"""Test de validation des dates"""
		today = datetime.now().date()
		yesterday = today - timedelta(days=1)
		
		location = frappe.get_doc({
			"doctype": "Location Longue Durée",
			"appartement_id": self.appartement.name,
			"locataire_nom": "Test Date Invalid",
			"date_debut": today,
			"date_fin": yesterday,
			"loyer_mensuel_locataire": 1200.0,
			"loyer_mensuel_proprietaire": 1000.0
		})
		
		with self.assertRaises(frappe.ValidationError):
			location.insert()
	
	def test_loyer_validation(self):
		"""Test de validation des loyers"""
		location = frappe.get_doc({
			"doctype": "Location Longue Durée",
			"appartement_id": self.appartement.name,
			"locataire_nom": "Test Loyer Invalid",
			"loyer_mensuel_locataire": 1000.0,
			"loyer_mensuel_proprietaire": 1200.0  # Propriétaire > Locataire
		})
		
		with self.assertRaises(frappe.ValidationError):
			location.insert()
	
	def test_email_validation(self):
		"""Test de validation de l'email du locataire"""
		location = frappe.get_doc({
			"doctype": "Location Longue Durée",
			"appartement_id": self.appartement.name,
			"locataire_nom": "Test Email Invalid",
			"locataire_email": "email_invalide",
			"loyer_mensuel_locataire": 1200.0,
			"loyer_mensuel_proprietaire": 1000.0
		})
		
		with self.assertRaises(frappe.ValidationError):
			location.insert()
	
	def test_nom_locataire_normalization(self):
		"""Test de normalisation du nom du locataire"""
		location = frappe.get_doc({
			"doctype": "Location Longue Durée",
			"appartement_id": self.appartement.name,
			"locataire_nom": "  jean martin  ",
			"loyer_mensuel_locataire": 1200.0,
			"loyer_mensuel_proprietaire": 1000.0
		})
		location.insert()
		
		self.assertEqual(location.locataire_nom, "Jean Martin")
	
	def tearDown(self):
		"""Nettoyage après chaque test"""
		frappe.db.delete("Location Longue Durée", {"locataire_nom": ["like", "Test%"]})
		frappe.db.delete("Appartement", {"adresse_complete": ["like", "Test%"]})
		frappe.db.delete("Propriétaire", {"nom_complet": ["like", "Test%"]})
		frappe.db.commit()