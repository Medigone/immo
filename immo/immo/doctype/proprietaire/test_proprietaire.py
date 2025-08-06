# Copyright (c) 2024, Frappe Technologies and Contributors
# See license.txt

import frappe
import unittest


class TestProprietaire(unittest.TestCase):
	"""Tests pour le doctype Propriétaire"""
	
	def setUp(self):
		"""Configuration avant chaque test"""
		# Nettoie les données de test
		frappe.db.delete("Proprietaire", {"nom_complet": ["like", "Test%"]})
		frappe.db.commit()
	
	def test_create_proprietaire(self):
		"""Test de création d'un propriétaire"""
		proprietaire = frappe.get_doc({
			"doctype": "Proprietaire",
			"nom_complet": "Test Propriétaire",
			"email": "test@example.com",
			"telephone": "0123456789",
			"adresse": "123 Rue de Test",
			"methode_paiement": "Virement",
			"iban": "FR1420041010050500013M02606",
			"actif": 1
		})
		proprietaire.insert()
		
		self.assertEqual(proprietaire.nom_complet, "Test Propriétaire")
		self.assertEqual(proprietaire.email, "test@example.com")
		self.assertTrue(proprietaire.actif)
	
	def test_email_validation(self):
		"""Test de validation de l'email"""
		proprietaire = frappe.get_doc({
			"doctype": "Proprietaire",
			"nom_complet": "Test Email Invalid",
			"email": "email_invalide"
		})
		
		with self.assertRaises(frappe.ValidationError):
			proprietaire.insert()
	
	def test_iban_validation(self):
		"""Test de validation de l'IBAN"""
		proprietaire = frappe.get_doc({
			"doctype": "Proprietaire",
			"nom_complet": "Test IBAN Invalid",
			"iban": "IBAN_TROP_COURT"
		})
		
		with self.assertRaises(frappe.ValidationError):
			proprietaire.insert()
	
	def test_nom_complet_normalization(self):
		"""Test de normalisation du nom complet"""
		proprietaire = frappe.get_doc({
			"doctype": "Proprietaire",
			"nom_complet": "  jean dupont  "
		})
		proprietaire.insert()
		
		self.assertEqual(proprietaire.nom_complet, "Jean Dupont")
	
	def tearDown(self):
		"""Nettoyage après chaque test"""
		frappe.db.delete("Proprietaire", {"nom_complet": ["like", "Test%"]})
		frappe.db.commit()