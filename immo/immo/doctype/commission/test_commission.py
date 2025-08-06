# Copyright (c) 2024, Frappe Technologies and Contributors
# See license.txt

import frappe
import unittest
from datetime import datetime, timedelta


class TestCommission(unittest.TestCase):
	"""Tests pour le doctype Commission"""
	
	def setUp(self):
		"""Configuration avant chaque test"""
		# Nettoie les données de test
		frappe.db.delete("Commission", {"referent_id": ["like", "REF-%"]})
		frappe.db.delete("Location Courte Duree", {"locataire_nom": ["like", "Test%"]})
		frappe.db.delete("Appartement", {"adresse_complete": ["like", "Test%"]})
		frappe.db.delete("Proprietaire", {"nom_complet": ["like", "Test%"]})
		frappe.db.delete("Referent", {"nom_complet": ["like", "Test%"]})
		frappe.db.commit()
		
		# Crée un propriétaire de test
		self.proprietaire = frappe.get_doc({
			"doctype": "Proprietaire",
			"nom_complet": "Test Propriétaire Commission",
			"email": "test.commission@example.com",
			"actif": 1
		})
		self.proprietaire.insert()
		
		# Crée un appartement de test
		self.appartement = frappe.get_doc({
			"doctype": "Appartement",
			"proprietaire_id": self.proprietaire.name,
			"adresse_complete": "Test 789 Rue de la Commission",
			"nombre_pieces": 2,
			"surface": 40.0,
			"prix_journalier_defaut": 90.0,
			"disponible": 1
		})
		self.appartement.insert()
		
		# Crée un référent de test
		self.referent = frappe.get_doc({
			"doctype": "Referent",
			"nom_complet": "Test Référent Commission",
			"email": "referent.commission@example.com",
			"pourcentage_commission_defaut": 15.0,
			"actif": 1
		})
		self.referent.insert()
		
		# Crée une location courte duree de test
		today = datetime.now().date()
		future_date = today + timedelta(days=4)
		
		self.location = frappe.get_doc({
			"doctype": "Location Courte Duree",
			"appartement_id": self.appartement.name,
			"locataire_nom": "Test Locataire Commission",
			"locataire_email": "locataire.commission@example.com",
			"date_debut": today,
			"date_fin": future_date,
			"prix_journalier_locataire": 120.0,
			"prix_journalier_proprietaire": 80.0,
			"referent_id": self.referent.name,
			"statut": "Confirmé"
		})
		self.location.insert()
	
	def test_create_commission(self):
		"""Test de création d'une commission"""
		commission = frappe.get_doc({
			"doctype": "Commission",
			"referent_id": self.referent.name,
			"location_courte_duree_id": self.location.name,
			"pourcentage_commission": 15.0,
			"statut_paiement": "En attente"
		})
		commission.insert()
		
		self.assertEqual(commission.referent_id, self.referent.name)
		self.assertEqual(commission.location_courte_duree_id, self.location.name)
		self.assertEqual(commission.pourcentage_commission, 15.0)
		self.assertGreater(commission.montant_commission, 0)
	
	def test_commission_calculation(self):
		"""Test du calcul automatique de la commission"""
		commission = frappe.get_doc({
			"doctype": "Commission",
			"referent_id": self.referent.name,
			"location_courte_duree_id": self.location.name,
			"statut_paiement": "En attente"
		})
		commission.insert()
		
		# Marge totale = 4 nuits * (120 - 80) = 160
		# Commission = 160 * 15% = 24
		self.assertEqual(commission.montant_commission, 24.0)
		self.assertEqual(commission.pourcentage_commission, 15.0)
	
	def test_inactive_referent_validation(self):
		"""Test de validation avec un référent inactif"""
		# Désactive le référent
		self.referent.actif = 0
		self.referent.save()
		
		commission = frappe.get_doc({
			"doctype": "Commission",
			"referent_id": self.referent.name,
			"location_courte_duree_id": self.location.name,
			"pourcentage_commission": 15.0
		})
		
		with self.assertRaises(frappe.ValidationError):
			commission.insert()
	
	def test_unconfirmed_location_validation(self):
		"""Test de validation avec une location non confirmée"""
		# Change le statut de la location
		self.location.statut = "Brouillon"
		self.location.save()
		
		commission = frappe.get_doc({
			"doctype": "Commission",
			"referent_id": self.referent.name,
			"location_courte_duree_id": self.location.name,
			"pourcentage_commission": 15.0
		})
		
		with self.assertRaises(frappe.ValidationError):
			commission.insert()
	
	def test_negative_commission_validation(self):
		"""Test de validation avec un montant négatif"""
		commission = frappe.get_doc({
			"doctype": "Commission",
			"referent_id": self.referent.name,
			"location_courte_duree_id": self.location.name,
			"montant_commission": -50.0,
			"pourcentage_commission": 15.0
		})
		
		with self.assertRaises(frappe.ValidationError):
			commission.insert()
	
	def test_invalid_percentage_validation(self):
		"""Test de validation avec un pourcentage invalide"""
		commission = frappe.get_doc({
			"doctype": "Commission",
			"referent_id": self.referent.name,
			"location_courte_duree_id": self.location.name,
			"pourcentage_commission": 150.0  # > 100%
		})
		
		with self.assertRaises(frappe.ValidationError):
			commission.insert()
	
	def test_payment_details_validation(self):
		"""Test de validation des détails de paiement"""
		commission = frappe.get_doc({
			"doctype": "Commission",
			"referent_id": self.referent.name,
			"location_courte_duree_id": self.location.name,
			"pourcentage_commission": 15.0,
			"statut_paiement": "Payé"  # Sans date ni méthode
		})
		
		with self.assertRaises(frappe.ValidationError):
			commission.insert()
	
	def test_mark_as_paid(self):
		"""Test de marquage comme payé"""
		commission = frappe.get_doc({
			"doctype": "Commission",
			"referent_id": self.referent.name,
			"location_courte_duree_id": self.location.name,
			"pourcentage_commission": 15.0,
			"statut_paiement": "En attente"
		})
		commission.insert()
		
		today = frappe.utils.nowdate()
		result = commission.mark_as_paid(
			date_paiement=today,
			methode_paiement="Virement",
			reference_paiement="REF123"
		)
		
		self.assertEqual(commission.statut_paiement, "Payé")
		self.assertEqual(commission.date_paiement, today)
		self.assertEqual(commission.methode_paiement, "Virement")
		self.assertEqual(commission.reference_paiement, "REF123")
	
	def test_net_margin_calculation(self):
		"""Test du calcul de la marge nette"""
		commission = frappe.get_doc({
			"doctype": "Commission",
			"referent_id": self.referent.name,
			"location_courte_duree_id": self.location.name,
			"pourcentage_commission": 15.0,
			"statut_paiement": "En attente"
		})
		commission.insert()
		
		net_margin = commission.calculate_net_margin_after_commission()
		
		# Marge brute = 160, Commission = 24, Marge nette = 136
		self.assertEqual(net_margin["marge_brute"], 160.0)
		self.assertEqual(net_margin["commission_referent"], 24.0)
		self.assertEqual(net_margin["marge_nette"], 136.0)
		self.assertEqual(net_margin["pourcentage_commission"], 15.0)
	
	def test_commission_details(self):
		"""Test de récupération des détails de la commission"""
		commission = frappe.get_doc({
			"doctype": "Commission",
			"referent_id": self.referent.name,
			"location_courte_duree_id": self.location.name,
			"pourcentage_commission": 15.0,
			"statut_paiement": "En attente"
		})
		commission.insert()
		
		details = commission.get_commission_details()
		
		self.assertIn("commission", details)
		self.assertIn("referent", details)
		self.assertIn("location", details)
		self.assertIn("appartement", details)
		
		self.assertEqual(details["referent"]["nom_complet"], "Test Référent Commission")
		self.assertEqual(details["location"]["locataire_nom"], "Test Locataire Commission")
		self.assertEqual(details["appartement"]["adresse_complete"], "Test 789 Rue de la Commission")
	
	def tearDown(self):
		"""Nettoyage après chaque test"""
		frappe.db.delete("Commission", {"referent_id": ["like", "REF-%"]})
		frappe.db.delete("Location Courte Duree", {"locataire_nom": ["like", "Test%"]})
		frappe.db.delete("Appartement", {"adresse_complete": ["like", "Test%"]})
		frappe.db.delete("Proprietaire", {"nom_complet": ["like", "Test%"]})
		frappe.db.delete("Referent", {"nom_complet": ["like", "Test%"]})
		frappe.db.commit()