# Copyright (c) 2024, Frappe Technologies and Contributors
# See license.txt

import frappe
import unittest
from datetime import datetime, timedelta


class TestLocationCourteDuree(unittest.TestCase):
	"""Tests pour le doctype Location Courte Durée"""
	
	def setUp(self):
		"""Configuration avant chaque test"""
		# Nettoie les données de test
		frappe.db.delete("Location Courte Durée", {"locataire_nom": ["like", "Test%"]})
		frappe.db.delete("Appartement", {"adresse_complete": ["like", "Test%"]})
		frappe.db.delete("Propriétaire", {"nom_complet": ["like", "Test%"]})
		frappe.db.delete("Référent", {"nom_complet": ["like", "Test%"]})
		frappe.db.commit()
		
		# Crée un propriétaire de test
		self.proprietaire = frappe.get_doc({
			"doctype": "Propriétaire",
			"nom_complet": "Test Propriétaire LCD",
			"email": "test.lcd@example.com",
			"actif": 1
		})
		self.proprietaire.insert()
		
		# Crée un appartement de test
		self.appartement = frappe.get_doc({
			"doctype": "Appartement",
			"proprietaire_id": self.proprietaire.name,
			"adresse_complete": "Test 456 Rue de la Location Courte",
			"nombre_pieces": 1,
			"surface": 30.0,
			"prix_journalier_defaut": 80.0,
			"disponible": 1
		})
		self.appartement.insert()
		
		# Crée un référent de test
		self.referent = frappe.get_doc({
			"doctype": "Référent",
			"nom_complet": "Test Référent",
			"email": "referent@example.com",
			"pourcentage_commission_defaut": 10.0,
			"actif": 1
		})
		self.referent.insert()
	
	def test_create_location_courte_duree(self):
		"""Test de création d'une location courte durée"""
		today = datetime.now().date()
		future_date = today + timedelta(days=7)
		
		location = frappe.get_doc({
			"doctype": "Location Courte Durée",
			"appartement_id": self.appartement.name,
			"locataire_nom": "Test Locataire Court",
			"locataire_email": "locataire.court@example.com",
			"date_debut": today,
			"date_fin": future_date,
			"prix_journalier_locataire": 100.0,
			"prix_journalier_proprietaire": 70.0,
			"statut": "Brouillon"
		})
		location.insert()
		
		self.assertEqual(location.appartement_id, self.appartement.name)
		self.assertEqual(location.locataire_nom, "Test Locataire Court")
		self.assertEqual(location.nombre_nuits, 7)
		self.assertEqual(location.montant_total_locataire, 700.0)
		self.assertEqual(location.montant_total_proprietaire, 490.0)
		self.assertEqual(location.marge_totale, 210.0)
	
	def test_nights_calculation(self):
		"""Test du calcul du nombre de nuits"""
		today = datetime.now().date()
		future_date = today + timedelta(days=3)
		
		location = frappe.get_doc({
			"doctype": "Location Courte Durée",
			"appartement_id": self.appartement.name,
			"locataire_nom": "Test Nuits",
			"date_debut": today,
			"date_fin": future_date,
			"prix_journalier_locataire": 80.0,
			"prix_journalier_proprietaire": 60.0
		})
		location.insert()
		
		self.assertEqual(location.nombre_nuits, 3)
	
	def test_referent_commission_calculation(self):
		"""Test du calcul de la commission référent"""
		today = datetime.now().date()
		future_date = today + timedelta(days=5)
		
		location = frappe.get_doc({
			"doctype": "Location Courte Durée",
			"appartement_id": self.appartement.name,
			"locataire_nom": "Test Commission",
			"date_debut": today,
			"date_fin": future_date,
			"prix_journalier_locataire": 100.0,
			"prix_journalier_proprietaire": 80.0,
			"referent_id": self.referent.name
		})
		location.insert()
		
		# Marge totale = 5 nuits * (100 - 80) = 100
		# Commission = 100 * 10% = 10
		self.assertEqual(location.marge_totale, 100.0)
		self.assertEqual(location.commission_referent, 10.0)
	
	def test_date_validation(self):
		"""Test de validation des dates"""
		today = datetime.now().date()
		yesterday = today - timedelta(days=1)
		
		location = frappe.get_doc({
			"doctype": "Location Courte Durée",
			"appartement_id": self.appartement.name,
			"locataire_nom": "Test Date Invalid",
			"date_debut": today,
			"date_fin": yesterday,
			"prix_journalier_locataire": 100.0,
			"prix_journalier_proprietaire": 80.0
		})
		
		with self.assertRaises(frappe.ValidationError):
			location.insert()
	
	def test_prix_validation(self):
		"""Test de validation des prix"""
		today = datetime.now().date()
		future_date = today + timedelta(days=3)
		
		location = frappe.get_doc({
			"doctype": "Location Courte Durée",
			"appartement_id": self.appartement.name,
			"locataire_nom": "Test Prix Invalid",
			"date_debut": today,
			"date_fin": future_date,
			"prix_journalier_locataire": 80.0,
			"prix_journalier_proprietaire": 100.0  # Propriétaire > Locataire
		})
		
		with self.assertRaises(frappe.ValidationError):
			location.insert()
	
	def test_email_validation(self):
		"""Test de validation de l'email du locataire"""
		today = datetime.now().date()
		future_date = today + timedelta(days=3)
		
		location = frappe.get_doc({
			"doctype": "Location Courte Durée",
			"appartement_id": self.appartement.name,
			"locataire_nom": "Test Email Invalid",
			"locataire_email": "email_invalide",
			"date_debut": today,
			"date_fin": future_date,
			"prix_journalier_locataire": 100.0,
			"prix_journalier_proprietaire": 80.0
		})
		
		with self.assertRaises(frappe.ValidationError):
			location.insert()
	
	def test_net_margin_calculation(self):
		"""Test du calcul de la marge nette"""
		today = datetime.now().date()
		future_date = today + timedelta(days=2)
		
		location = frappe.get_doc({
			"doctype": "Location Courte Durée",
			"appartement_id": self.appartement.name,
			"locataire_nom": "Test Marge Nette",
			"date_debut": today,
			"date_fin": future_date,
			"prix_journalier_locataire": 100.0,
			"prix_journalier_proprietaire": 70.0,
			"referent_id": self.referent.name
		})
		location.insert()
		
		net_margin = location.calculate_net_margin()
		
		# Marge totale = 2 * (100 - 70) = 60
		# Commission = 60 * 10% = 6
		# Marge nette = 60 - 6 = 54
		self.assertEqual(net_margin["marge_totale"], 60.0)
		self.assertEqual(net_margin["commission_referent"], 6.0)
		self.assertEqual(net_margin["marge_nette"], 54.0)
	
	def tearDown(self):
		"""Nettoyage après chaque test"""
		frappe.db.delete("Location Courte Durée", {"locataire_nom": ["like", "Test%"]})
		frappe.db.delete("Appartement", {"adresse_complete": ["like", "Test%"]})
		frappe.db.delete("Propriétaire", {"nom_complet": ["like", "Test%"]})
		frappe.db.delete("Référent", {"nom_complet": ["like", "Test%"]})
		frappe.db.commit()