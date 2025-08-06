# Copyright (c) 2024, Frappe Technologies and Contributors
# See license.txt

import frappe
import unittest
from frappe.utils import nowdate, add_days


class TestPaiementLocataire(unittest.TestCase):
	"""Tests pour le doctype Paiement Locataire"""
	
	def setUp(self):
		"""Configuration des données de test"""
		# Crée un propriétaire de test
		self.proprietaire = frappe.get_doc({
			"doctype": "Propriétaire",
			"nom_complet": "Jean Dupont",
			"email": "jean.dupont@test.com",
			"telephone": "0123456789"
		})
		self.proprietaire.insert()
		
		# Crée un appartement de test
		self.appartement = frappe.get_doc({
			"doctype": "Appartement",
			"proprietaire_id": self.proprietaire.name,
			"adresse": "123 Rue de Test",
			"ville": "Paris",
			"code_postal": "75001",
			"surface": 50,
			"nombre_pieces": 2,
			"statut": "Disponible"
		})
		self.appartement.insert()
		
		# Crée une location longue durée de test
		self.location_longue = frappe.get_doc({
			"doctype": "Location Longue Durée",
			"appartement_id": self.appartement.name,
			"locataire_nom": "Marie Martin",
			"locataire_email": "marie.martin@test.com",
			"date_debut": nowdate(),
			"date_fin": add_days(nowdate(), 365),
			"loyer_mensuel_locataire": 1000,
			"loyer_mensuel_proprietaire": 900,
			"statut": "Actif"
		})
		self.location_longue.insert()
		
		# Crée une mensualité de test
		self.mensualite = frappe.get_doc({
			"doctype": "Mensualité",
			"location_longue_duree_id": self.location_longue.name,
			"mois_annee": "01/2024",
			"date_echeance": nowdate(),
			"montant_loyer_locataire": 1000,
			"montant_loyer_proprietaire": 900
		})
		self.mensualite.insert()
		
		# Crée une location courte durée de test
		self.location_courte = frappe.get_doc({
			"doctype": "Location Courte Durée",
			"appartement_id": self.appartement.name,
			"locataire_nom": "Paul Durand",
			"locataire_email": "paul.durand@test.com",
			"date_debut": add_days(nowdate(), 30),
			"date_fin": add_days(nowdate(), 35),
			"prix_par_nuit": 80,
			"statut": "Confirmé"
		})
		self.location_courte.insert()
	
	def tearDown(self):
		"""Nettoyage après les tests"""
		# Supprime les documents de test
		frappe.db.rollback()
	
	def test_create_paiement_mensualite(self):
		"""Test de création d'un paiement pour une mensualité"""
		paiement = frappe.get_doc({
			"doctype": "Paiement Locataire",
			"mensualite_id": self.mensualite.name,
			"location_longue_duree_id": self.location_longue.name,
			"type_paiement": "Loyer mensuel",
			"montant": 1000,
			"date_paiement": nowdate(),
			"methode_paiement": "Virement bancaire",
			"statut": "En attente"
		})
		paiement.insert()
		
		self.assertEqual(paiement.montant_net, 1000)
		self.assertEqual(paiement.location_longue_duree_id, self.location_longue.name)
	
	def test_create_paiement_location_courte(self):
		"""Test de création d'un paiement pour une location courte durée"""
		paiement = frappe.get_doc({
			"doctype": "Paiement Locataire",
			"location_courte_duree_id": self.location_courte.name,
			"type_paiement": "Séjour court",
			"montant": 400,
			"date_paiement": nowdate(),
			"methode_paiement": "Carte bancaire",
			"statut": "En attente"
		})
		paiement.insert()
		
		self.assertEqual(paiement.montant, 400)
		self.assertEqual(paiement.location_courte_duree_id, self.location_courte.name)
	
	def test_calculate_net_amount_with_fees(self):
		"""Test du calcul du montant net avec frais de transaction"""
		paiement = frappe.get_doc({
			"doctype": "Paiement Locataire",
			"location_courte_duree_id": self.location_courte.name,
			"type_paiement": "Séjour court",
			"montant": 400,
			"frais_transaction": 15,
			"date_paiement": nowdate(),
			"methode_paiement": "Carte bancaire",
			"statut": "En attente"
		})
		paiement.insert()
		
		self.assertEqual(paiement.montant_net, 385)  # 400 - 15
	
	def test_validation_no_reference(self):
		"""Test de validation sans référence de location"""
		with self.assertRaises(frappe.ValidationError):
			paiement = frappe.get_doc({
				"doctype": "Paiement Locataire",
				"type_paiement": "Loyer mensuel",
				"montant": 1000,
				"date_paiement": nowdate(),
				"methode_paiement": "Virement bancaire",
				"statut": "En attente"
			})
			paiement.insert()
	
	def test_validation_negative_amount(self):
		"""Test de validation avec montant négatif"""
		with self.assertRaises(frappe.ValidationError):
			paiement = frappe.get_doc({
				"doctype": "Paiement Locataire",
				"location_courte_duree_id": self.location_courte.name,
				"type_paiement": "Séjour court",
				"montant": -100,
				"date_paiement": nowdate(),
				"methode_paiement": "Carte bancaire",
				"statut": "En attente"
			})
			paiement.insert()
	
	def test_validation_future_payment_date(self):
		"""Test de validation avec date de paiement dans le futur"""
		with self.assertRaises(frappe.ValidationError):
			paiement = frappe.get_doc({
				"doctype": "Paiement Locataire",
				"location_courte_duree_id": self.location_courte.name,
				"type_paiement": "Séjour court",
				"montant": 400,
				"date_paiement": add_days(nowdate(), 1),
				"methode_paiement": "Carte bancaire",
				"statut": "En attente"
			})
			paiement.insert()
	
	def test_confirm_payment(self):
		"""Test de confirmation d'un paiement"""
		paiement = frappe.get_doc({
			"doctype": "Paiement Locataire",
			"mensualite_id": self.mensualite.name,
			"location_longue_duree_id": self.location_longue.name,
			"type_paiement": "Loyer mensuel",
			"montant": 1000,
			"date_paiement": nowdate(),
			"methode_paiement": "Virement bancaire",
			"statut": "En attente"
		})
		paiement.insert()
		
		result = paiement.confirm_payment()
		
		self.assertEqual(paiement.statut, "Confirmé")
		self.assertIsNotNone(paiement.date_validation)
		self.assertEqual(paiement.valide_par, frappe.session.user)
		self.assertIn("confirmé", result["message"])
	
	def test_reject_payment(self):
		"""Test de rejet d'un paiement"""
		paiement = frappe.get_doc({
			"doctype": "Paiement Locataire",
			"location_courte_duree_id": self.location_courte.name,
			"type_paiement": "Séjour court",
			"montant": 400,
			"date_paiement": nowdate(),
			"methode_paiement": "Carte bancaire",
			"statut": "En attente"
		})
		paiement.insert()
		
		reason = "Paiement insuffisant"
		result = paiement.reject_payment(reason)
		
		self.assertEqual(paiement.statut, "Rejeté")
		self.assertIn(reason, paiement.commentaires)
		self.assertIn("rejeté", result["message"])
	
	def test_update_mensualite_status(self):
		"""Test de mise à jour du statut de la mensualité"""
		paiement = frappe.get_doc({
			"doctype": "Paiement Locataire",
			"mensualite_id": self.mensualite.name,
			"location_longue_duree_id": self.location_longue.name,
			"type_paiement": "Loyer mensuel",
			"montant": 1000,
			"date_paiement": nowdate(),
			"methode_paiement": "Virement bancaire",
			"reference_paiement": "REF123",
			"statut": "En attente"
		})
		paiement.insert()
		
		# Confirme le paiement
		paiement.confirm_payment()
		
		# Vérifie que la mensualité a été mise à jour
		mensualite = frappe.get_doc("Mensualité", self.mensualite.name)
		self.assertEqual(mensualite.statut_paiement_locataire, "Payé")
		self.assertEqual(mensualite.date_paiement_locataire, paiement.date_paiement)
		self.assertEqual(mensualite.methode_paiement_locataire, paiement.methode_paiement)
		self.assertEqual(mensualite.reference_paiement_locataire, paiement.reference_paiement)
	
	def test_get_payment_details(self):
		"""Test de récupération des détails complets du paiement"""
		paiement = frappe.get_doc({
			"doctype": "Paiement Locataire",
			"mensualite_id": self.mensualite.name,
			"location_longue_duree_id": self.location_longue.name,
			"type_paiement": "Loyer mensuel",
			"montant": 1000,
			"date_paiement": nowdate(),
			"methode_paiement": "Virement bancaire",
			"statut": "Confirmé"
		})
		paiement.insert()
		
		details = paiement.get_payment_details()
		
		self.assertIn("paiement", details)
		self.assertIn("location_longue_duree", details)
		self.assertIn("mensualite", details)
		self.assertEqual(details["paiement"]["montant"], 1000)
		self.assertEqual(details["location_longue_duree"]["locataire_nom"], "Marie Martin")
		self.assertEqual(details["mensualite"]["mois_annee"], "01/2024")
	
	def test_calculate_payment_statistics(self):
		"""Test de calcul des statistiques de paiement"""
		# Crée plusieurs paiements confirmés
		paiement1 = frappe.get_doc({
			"doctype": "Paiement Locataire",
			"location_courte_duree_id": self.location_courte.name,
			"type_paiement": "Séjour court",
			"montant": 400,
			"frais_transaction": 10,
			"date_paiement": nowdate(),
			"methode_paiement": "Carte bancaire",
			"statut": "Confirmé"
		})
		paiement1.insert()
		
		paiement2 = frappe.get_doc({
			"doctype": "Paiement Locataire",
			"mensualite_id": self.mensualite.name,
			"location_longue_duree_id": self.location_longue.name,
			"type_paiement": "Loyer mensuel",
			"montant": 1000,
			"frais_transaction": 5,
			"date_paiement": nowdate(),
			"methode_paiement": "Virement bancaire",
			"statut": "Confirmé"
		})
		paiement2.insert()
		
		stats = paiement1.calculate_payment_statistics()
		
		self.assertEqual(stats["total_paiements"], 2)
		self.assertEqual(stats["montant_total"], 1400)
		self.assertEqual(stats["montant_net_total"], 1385)  # 1400 - 15 frais
		self.assertEqual(stats["frais_total"], 15)
		self.assertIn("Séjour court", stats["repartition_par_type"])
		self.assertIn("Loyer mensuel", stats["repartition_par_type"])
		self.assertIn("Carte bancaire", stats["repartition_par_methode"])
		self.assertIn("Virement bancaire", stats["repartition_par_methode"])
	
	def test_validation_confirmed_payment_modification(self):
		"""Test de validation empêchant la modification d'un paiement confirmé"""
		paiement = frappe.get_doc({
			"doctype": "Paiement Locataire",
			"location_courte_duree_id": self.location_courte.name,
			"type_paiement": "Séjour court",
			"montant": 400,
			"date_paiement": nowdate(),
			"methode_paiement": "Carte bancaire",
			"statut": "En attente"
		})
		paiement.insert()
		
		# Confirme le paiement
		paiement.confirm_payment()
		
		# Tente de modifier le statut
		with self.assertRaises(frappe.ValidationError):
			paiement.statut = "En attente"
			paiement.save()
	
	def test_reject_confirmed_payment(self):
		"""Test de rejet d'un paiement déjà confirmé"""
		paiement = frappe.get_doc({
			"doctype": "Paiement Locataire",
			"location_courte_duree_id": self.location_courte.name,
			"type_paiement": "Séjour court",
			"montant": 400,
			"date_paiement": nowdate(),
			"methode_paiement": "Carte bancaire",
			"statut": "Confirmé"
		})
		paiement.insert()
		
		with self.assertRaises(frappe.ValidationError):
			paiement.reject_payment("Test de rejet")