# Copyright (c) 2024, Frappe Technologies and Contributors
# See license.txt

import frappe
import unittest
from datetime import datetime, timedelta


class TestReferent(unittest.TestCase):
	"""Tests pour le doctype Référent"""
	
	def setUp(self):
		"""Configuration avant chaque test"""
		# Nettoie les données de test
		frappe.db.delete("Referent", {"nom_complet": ["like", "Test%"]})
		frappe.db.commit()
	
	def test_create_referent(self):
		"""Test de création d'un référent"""
		referent = frappe.get_doc({
			"doctype": "Referent",
			"nom_complet": "Test Référent",
			"email": "test.referent@example.com",
			"telephone": "0123456789",
			"adresse": "123 Rue du Test",
			"pourcentage_commission_defaut": 10.0,
			"actif": 1
		})
		referent.insert()
		
		self.assertEqual(referent.nom_complet, "Test Référent")
		self.assertEqual(referent.email, "test.referent@example.com")
		self.assertEqual(referent.pourcentage_commission_defaut, 10.0)
		self.assertTrue(referent.actif)
	
	def test_email_validation(self):
		"""Test de validation de l'email"""
		referent = frappe.get_doc({
			"doctype": "Referent",
			"nom_complet": "Test Email Invalid",
			"email": "email_invalide",
			"pourcentage_commission_defaut": 10.0
		})
		
		with self.assertRaises(frappe.ValidationError):
			referent.insert()
	
	def test_commission_percentage_validation(self):
		"""Test de validation du pourcentage de commission"""
		# Test pourcentage négatif
		referent_negative = frappe.get_doc({
			"doctype": "Referent",
			"nom_complet": "Test Commission Negative",
			"email": "test.negative@example.com",
			"pourcentage_commission_defaut": -5.0
		})
		
		with self.assertRaises(frappe.ValidationError):
			referent_negative.insert()
		
		# Test pourcentage supérieur à 100
		referent_high = frappe.get_doc({
			"doctype": "Referent",
			"nom_complet": "Test Commission High",
			"email": "test.high@example.com",
			"pourcentage_commission_defaut": 150.0
		})
		
		with self.assertRaises(frappe.ValidationError):
			referent_high.insert()
	
	def test_name_normalization(self):
		"""Test de normalisation du nom complet"""
		referent = frappe.get_doc({
			"doctype": "Referent",
			"nom_complet": "  jean-claude van damme  ",
			"email": "jcvd@example.com",
			"pourcentage_commission_defaut": 15.0
		})
		referent.insert()
		
		self.assertEqual(referent.nom_complet, "Jean-Claude Van Damme")
	
	def test_total_commissions_calculation(self):
		"""Test du calcul du total des commissions"""
		referent = frappe.get_doc({
			"doctype": "Referent",
			"nom_complet": "Test Commission Calc",
			"email": "test.calc@example.com",
			"pourcentage_commission_defaut": 10.0,
			"actif": 1
		})
		referent.insert()
		
		# Crée quelques commissions de test
		today = frappe.utils.nowdate()
		
		commission1 = frappe.get_doc({
			"doctype": "Commission",
			"referent_id": referent.name,
			"montant_commission": 100.0,
			"pourcentage_commission": 10.0,
			"date_creation": today,
			"status": "Nouveau"
		})
		commission1.insert()
		
		commission2 = frappe.get_doc({
			"doctype": "Commission",
			"referent_id": referent.name,
			"montant_commission": 50.0,
			"pourcentage_commission": 10.0,
			"date_creation": today,
			"status": "Payé"
		})
		commission2.insert()
		
		total_data = referent.get_total_commissions()
		
		self.assertEqual(total_data["total_commissions"], 150.0)
		self.assertEqual(total_data["commissions_payees"], 50.0)
		self.assertEqual(total_data["commissions_en_attente"], 100.0)
		self.assertEqual(total_data["nombre_commissions"], 2)
	
	def test_performance_metrics(self):
		"""Test du calcul des métriques de performance"""
		referent = frappe.get_doc({
			"doctype": "Referent",
			"nom_complet": "Test Performance",
			"email": "test.performance@example.com",
			"pourcentage_commission_defaut": 12.0,
			"actif": 1
		})
		referent.insert()
		
		# Crée un propriétaire et appartement de test
		proprietaire = frappe.get_doc({
			"doctype": "Proprietaire",
			"nom_complet": "Test Propriétaire Perf",
			"email": "test.perf@example.com",
			"actif": 1
		})
		proprietaire.insert()
		
		appartement = frappe.get_doc({
			"doctype": "Appartement",
			"proprietaire_id": proprietaire.name,
			"adresse_complete": "Test Performance Address",
			"nombre_pieces": 2,
			"surface": 50.0,
			"prix_journalier_defaut": 100.0,
			"disponible": 1
		})
		appartement.insert()
		
		# Crée une location courte duree de test
		today = datetime.now().date()
		future_date = today + timedelta(days=5)
		
		location = frappe.get_doc({
			"doctype": "Location Courte Duree",
			"appartement_id": appartement.name,
			"locataire_nom": "Test Locataire Perf",
			"locataire_email": "locataire.perf@example.com",
			"date_debut": today,
			"date_fin": future_date,
			"prix_journalier_locataire": 120.0,
			"prix_journalier_proprietaire": 80.0,
			"referent_id": referent.name,
			"statut": "Confirmé"
		})
		location.insert()
		
		current_year = str(today.year)
		metrics = referent.calculate_performance_metrics(current_year)
		
		self.assertEqual(metrics["nombre_locations"], 1)
		self.assertEqual(metrics["chiffre_affaires_genere"], 600.0)  # 5 nuits * 120
		self.assertEqual(metrics["total_nuits_vendues"], 5)
		self.assertGreater(metrics["total_commissions"], 0)
	
	def tearDown(self):
		"""Nettoyage après chaque test"""
		frappe.db.delete("Location Courte Duree", {"locataire_nom": ["like", "Test%"]})
		frappe.db.delete("Commission", {"referent_id": ["like", "REF-%"]})
		frappe.db.delete("Appartement", {"adresse_complete": ["like", "Test%"]})
		frappe.db.delete("Proprietaire", {"nom_complet": ["like", "Test%"]})
		frappe.db.delete("Referent", {"nom_complet": ["like", "Test%"]})
		frappe.db.commit()