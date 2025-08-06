# Copyright (c) 2024, Frappe Technologies and Contributors
# See license.txt

import frappe
import unittest
from datetime import datetime, timedelta


class TestMensualite(unittest.TestCase):
	"""Tests pour le doctype Mensualité"""
	
	def setUp(self):
		"""Configuration avant chaque test"""
		# Nettoie les données de test
		frappe.db.delete("Mensualité", {"mois_annee": ["like", "%2024"]})
		frappe.db.delete("Location Longue Durée", {"locataire_nom": ["like", "Test%"]})
		frappe.db.delete("Appartement", {"adresse_complete": ["like", "Test%"]})
		frappe.db.delete("Propriétaire", {"nom_complet": ["like", "Test%"]})
		frappe.db.commit()
		
		# Crée un propriétaire de test
		self.proprietaire = frappe.get_doc({
			"doctype": "Propriétaire",
			"nom_complet": "Test Propriétaire Mensualité",
			"email": "test.mensualite@example.com",
			"actif": 1
		})
		self.proprietaire.insert()
		
		# Crée un appartement de test
		self.appartement = frappe.get_doc({
			"doctype": "Appartement",
			"proprietaire_id": self.proprietaire.name,
			"adresse_complete": "Test 101 Rue de la Mensualité",
			"nombre_pieces": 3,
			"surface": 70.0,
			"prix_mensuel_defaut": 1200.0,
			"disponible": 1
		})
		self.appartement.insert()
		
		# Crée une location longue durée de test
		today = datetime.now().date()
		future_date = today + timedelta(days=365)
		
		self.location = frappe.get_doc({
			"doctype": "Location Longue Durée",
			"appartement_id": self.appartement.name,
			"locataire_nom": "Test Locataire Mensualité",
			"locataire_email": "locataire.mensualite@example.com",
			"locataire_telephone": "0123456789",
			"date_debut": today,
			"date_fin": future_date,
			"loyer_mensuel_locataire": 1500.0,
			"loyer_mensuel_proprietaire": 1200.0,
			"statut": "Actif"
		})
		self.location.insert()
	
	def test_create_mensualite(self):
		"""Test de création d'une mensualité"""
		today = datetime.now().date()
		
		mensualite = frappe.get_doc({
			"doctype": "Mensualité",
			"location_longue_duree_id": self.location.name,
			"mois_annee": "01/2024",
			"date_echeance": today,
			"montant_loyer_locataire": 1500.0,
			"montant_loyer_proprietaire": 1200.0,
			"statut_paiement_locataire": "En attente",
			"statut_paiement_proprietaire": "En attente"
		})
		mensualite.insert()
		
		self.assertEqual(mensualite.location_longue_duree_id, self.location.name)
		self.assertEqual(mensualite.mois_annee, "01/2024")
		self.assertEqual(mensualite.marge_mensuelle, 300.0)
	
	def test_margin_calculation(self):
		"""Test du calcul de la marge mensuelle"""
		today = datetime.now().date()
		
		mensualite = frappe.get_doc({
			"doctype": "Mensualité",
			"location_longue_duree_id": self.location.name,
			"mois_annee": "02/2024",
			"date_echeance": today,
			"montant_loyer_locataire": 1600.0,
			"montant_loyer_proprietaire": 1100.0
		})
		mensualite.insert()
		
		self.assertEqual(mensualite.marge_mensuelle, 500.0)
	
	def test_month_year_normalization(self):
		"""Test de normalisation du format mois/année"""
		today = datetime.now().date()
		
		mensualite = frappe.get_doc({
			"doctype": "Mensualité",
			"location_longue_duree_id": self.location.name,
			"mois_annee": "3-2024",  # Format avec tiret et mois sans zéro
			"date_echeance": today,
			"montant_loyer_locataire": 1500.0,
			"montant_loyer_proprietaire": 1200.0
		})
		mensualite.insert()
		
		self.assertEqual(mensualite.mois_annee, "03/2024")
	
	def test_invalid_month_year_format(self):
		"""Test de validation du format mois/année invalide"""
		today = datetime.now().date()
		
		mensualite = frappe.get_doc({
			"doctype": "Mensualité",
			"location_longue_duree_id": self.location.name,
			"mois_annee": "13/2024",  # Mois invalide
			"date_echeance": today,
			"montant_loyer_locataire": 1500.0,
			"montant_loyer_proprietaire": 1200.0
		})
		
		with self.assertRaises(frappe.ValidationError):
			mensualite.insert()
	
	def test_negative_amount_validation(self):
		"""Test de validation des montants négatifs"""
		today = datetime.now().date()
		
		mensualite = frappe.get_doc({
			"doctype": "Mensualité",
			"location_longue_duree_id": self.location.name,
			"mois_annee": "04/2024",
			"date_echeance": today,
			"montant_loyer_locataire": -1500.0,  # Montant négatif
			"montant_loyer_proprietaire": 1200.0
		})
		
		with self.assertRaises(frappe.ValidationError):
			mensualite.insert()
	
	def test_owner_rent_higher_than_tenant_validation(self):
		"""Test de validation quand le loyer propriétaire est supérieur au loyer locataire"""
		today = datetime.now().date()
		
		mensualite = frappe.get_doc({
			"doctype": "Mensualité",
			"location_longue_duree_id": self.location.name,
			"mois_annee": "05/2024",
			"date_echeance": today,
			"montant_loyer_locataire": 1200.0,
			"montant_loyer_proprietaire": 1500.0  # Supérieur au locataire
		})
		
		with self.assertRaises(frappe.ValidationError):
			mensualite.insert()
	
	def test_payment_details_validation(self):
		"""Test de validation des détails de paiement"""
		today = datetime.now().date()
		
		mensualite = frappe.get_doc({
			"doctype": "Mensualité",
			"location_longue_duree_id": self.location.name,
			"mois_annee": "06/2024",
			"date_echeance": today,
			"montant_loyer_locataire": 1500.0,
			"montant_loyer_proprietaire": 1200.0,
			"statut_paiement_locataire": "Payé"  # Sans date ni méthode
		})
		
		with self.assertRaises(frappe.ValidationError):
			mensualite.insert()
	
	def test_mark_tenant_payment_received(self):
		"""Test de marquage du paiement locataire comme reçu"""
		today = datetime.now().date()
		
		mensualite = frappe.get_doc({
			"doctype": "Mensualité",
			"location_longue_duree_id": self.location.name,
			"mois_annee": "07/2024",
			"date_echeance": today,
			"montant_loyer_locataire": 1500.0,
			"montant_loyer_proprietaire": 1200.0,
			"statut_paiement_locataire": "En attente"
		})
		mensualite.insert()
		
		result = mensualite.mark_tenant_payment_received(
			date_paiement=frappe.utils.nowdate(),
			methode_paiement="Virement",
			reference_paiement="REF123"
		)
		
		self.assertEqual(mensualite.statut_paiement_locataire, "Payé")
		self.assertEqual(mensualite.methode_paiement_locataire, "Virement")
		self.assertEqual(mensualite.reference_paiement_locataire, "REF123")
	
	def test_mark_owner_payment_sent(self):
		"""Test de marquage du paiement propriétaire comme envoyé"""
		today = datetime.now().date()
		
		mensualite = frappe.get_doc({
			"doctype": "Mensualité",
			"location_longue_duree_id": self.location.name,
			"mois_annee": "08/2024",
			"date_echeance": today,
			"montant_loyer_locataire": 1500.0,
			"montant_loyer_proprietaire": 1200.0,
			"statut_paiement_proprietaire": "En attente"
		})
		mensualite.insert()
		
		result = mensualite.mark_owner_payment_sent(
			date_paiement=frappe.utils.nowdate(),
			methode_paiement="Virement",
			reference_paiement="VIRT456"
		)
		
		self.assertEqual(mensualite.statut_paiement_proprietaire, "Payé")
		self.assertEqual(mensualite.methode_paiement_proprietaire, "Virement")
		self.assertEqual(mensualite.reference_paiement_proprietaire, "VIRT456")
	
	def test_payment_summary(self):
		"""Test de récupération du résumé des paiements"""
		today = datetime.now().date()
		
		mensualite = frappe.get_doc({
			"doctype": "Mensualité",
			"location_longue_duree_id": self.location.name,
			"mois_annee": "09/2024",
			"date_echeance": today,
			"montant_loyer_locataire": 1500.0,
			"montant_loyer_proprietaire": 1200.0
		})
		mensualite.insert()
		
		summary = mensualite.get_payment_summary()
		
		self.assertIn("mensualite", summary)
		self.assertIn("locataire", summary)
		self.assertIn("proprietaire", summary)
		self.assertIn("appartement", summary)
		
		self.assertEqual(summary["locataire"]["nom"], "Test Locataire Mensualité")
		self.assertEqual(summary["proprietaire"]["nom"], "Test Propriétaire Mensualité")
		self.assertEqual(summary["mensualite"]["marge_mensuelle"], 300.0)
	
	def test_overdue_status_check(self):
		"""Test de vérification du statut en retard"""
		yesterday = frappe.utils.add_days(frappe.utils.nowdate(), -1)
		
		mensualite = frappe.get_doc({
			"doctype": "Mensualité",
			"location_longue_duree_id": self.location.name,
			"mois_annee": "10/2024",
			"date_echeance": yesterday,  # Date d'échéance passée
			"montant_loyer_locataire": 1500.0,
			"montant_loyer_proprietaire": 1200.0,
			"statut_paiement_locataire": "En attente"
		})
		mensualite.insert()
		
		status = mensualite.check_overdue_status()
		
		self.assertEqual(status["statut_locataire"], "En retard")
	
	def tearDown(self):
		"""Nettoyage après chaque test"""
		frappe.db.delete("Paiement Locataire", {"mensualite_id": ["like", "MENS-%"]})
		frappe.db.delete("Paiement Propriétaire", {"mensualite_id": ["like", "MENS-%"]})
		frappe.db.delete("Mensualité", {"mois_annee": ["like", "%2024"]})
		frappe.db.delete("Location Longue Durée", {"locataire_nom": ["like", "Test%"]})
		frappe.db.delete("Appartement", {"adresse_complete": ["like", "Test%"]})
		frappe.db.delete("Propriétaire", {"nom_complet": ["like", "Test%"]})
		frappe.db.commit()