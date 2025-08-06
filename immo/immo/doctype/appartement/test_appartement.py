# Copyright (c) 2024, Frappe Technologies and Contributors
# See license.txt

import frappe
import unittest


class TestAppartement(unittest.TestCase):
	"""Tests pour le doctype Appartement"""
	
	def setUp(self):
		"""Configuration avant chaque test"""
		# Nettoie les données de test
		frappe.db.delete("Appartement", {"adresse_complete": ["like", "Test%"]})
		frappe.db.delete("Proprietaire", {"nom_complet": ["like", "Test%"]})
		frappe.db.commit()
		
		# Crée un propriétaire de test
		self.proprietaire = frappe.get_doc({
			"doctype": "Proprietaire",
			"nom_complet": "Test Propriétaire Appartement",
			"email": "test.apt@example.com",
			"actif": 1
		})
		self.proprietaire.insert()
	
	def test_create_appartement(self):
		"""Test de création d'un appartement"""
		appartement = frappe.get_doc({
			"doctype": "Appartement",
			"proprietaire_id": self.proprietaire.name,
			"adresse_complete": "Test 123 Rue de l'Appartement",
			"description": "Appartement de test",
			"nombre_pieces": 3,
			"surface": 75.5,
			"prix_journalier_defaut": 80.0,
			"prix_mensuel_defaut": 1200.0,
			"disponible": 1
		})
		appartement.insert()
		
		self.assertEqual(appartement.proprietaire_id, self.proprietaire.name)
		self.assertEqual(appartement.nombre_pieces, 3)
		self.assertEqual(appartement.surface, 75.5)
		self.assertTrue(appartement.disponible)
	
	def test_surface_validation(self):
		"""Test de validation de la surface"""
		appartement = frappe.get_doc({
			"doctype": "Appartement",
			"proprietaire_id": self.proprietaire.name,
			"adresse_complete": "Test Surface Invalid",
			"surface": -10.0
		})
		
		with self.assertRaises(frappe.ValidationError):
			appartement.insert()
	
	def test_prix_validation(self):
		"""Test de validation des prix"""
		appartement = frappe.get_doc({
			"doctype": "Appartement",
			"proprietaire_id": self.proprietaire.name,
			"adresse_complete": "Test Prix Invalid",
			"prix_journalier_defaut": -50.0
		})
		
		with self.assertRaises(frappe.ValidationError):
			appartement.insert()
	
	def test_proprietaire_inactif(self):
		"""Test avec propriétaire inactif"""
		# Désactive le propriétaire
		self.proprietaire.actif = 0
		self.proprietaire.save()
		
		appartement = frappe.get_doc({
			"doctype": "Appartement",
			"proprietaire_id": self.proprietaire.name,
			"adresse_complete": "Test Propriétaire Inactif"
		})
		
		with self.assertRaises(frappe.ValidationError):
			appartement.insert()
	
	def test_adresse_normalization(self):
		"""Test de normalisation de l'adresse"""
		appartement = frappe.get_doc({
			"doctype": "Appartement",
			"proprietaire_id": self.proprietaire.name,
			"adresse_complete": "  Test 456 Avenue Normalisée  "
		})
		appartement.insert()
		
		self.assertEqual(appartement.adresse_complete, "Test 456 Avenue Normalisée")
	
	def tearDown(self):
		"""Nettoyage après chaque test"""
		frappe.db.delete("Appartement", {"adresse_complete": ["like", "Test%"]})
		frappe.db.delete("Proprietaire", {"nom_complet": ["like", "Test%"]})
		frappe.db.commit()