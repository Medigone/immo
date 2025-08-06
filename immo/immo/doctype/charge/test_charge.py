# Copyright (c) 2024, Frappe Technologies and Contributors
# See license.txt

import frappe
import unittest
from frappe.utils import nowdate, add_days


class TestCharge(unittest.TestCase):
	"""Tests pour le doctype Charge"""
	
	def setUp(self):
		"""Configuration des données de test"""
		# Crée un propriétaire de test
		self.proprietaire = frappe.get_doc({
			"doctype": "Proprietaire",
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
	
	def test_create_charge_proprietaire(self):
		"""Test de création d'une charge à 100% propriétaire"""
		charge = frappe.get_doc({
			"doctype": "Charge",
			"appartement_id": self.appartement.name,
			"type_charge": "Travaux",
			"categorie": "Ponctuelle",
			"description": "Réparation plomberie",
			"montant": 500,
			"date_charge": nowdate(),
			"fournisseur": "Plombier Test",
			"repartition_locataire": 0,
			"repartition_proprietaire": 100,
			"statut": "En attente"
		})
		charge.insert()
		
		self.assertEqual(charge.montant_locataire, 0)
		self.assertEqual(charge.montant_proprietaire, 500)
		self.assertIsNotNone(charge.date_creation)
		self.assertEqual(charge.cree_par, frappe.session.user)
	
	def test_create_charge_repartie(self):
		"""Test de création d'une charge répartie"""
		charge = frappe.get_doc({
			"doctype": "Charge",
			"appartement_id": self.appartement.name,
			"location_longue_duree_id": self.location_longue.name,
			"type_charge": "Charges locatives",
			"categorie": "Récurrente",
			"description": "Charges de copropriété",
			"montant": 200,
			"date_charge": nowdate(),
			"repartition_locataire": 60,
			"repartition_proprietaire": 40,
			"statut": "En attente"
		})
		charge.insert()
		
		self.assertEqual(charge.montant_locataire, 120)  # 200 * 60%
		self.assertEqual(charge.montant_proprietaire, 80)  # 200 * 40%
	
	def test_validation_repartition_total(self):
		"""Test de validation de la répartition totale"""
		with self.assertRaises(frappe.ValidationError):
			charge = frappe.get_doc({
				"doctype": "Charge",
				"appartement_id": self.appartement.name,
				"type_charge": "Travaux",
				"categorie": "Ponctuelle",
				"description": "Test",
				"montant": 100,
				"date_charge": nowdate(),
				"repartition_locataire": 70,
				"repartition_proprietaire": 40,  # Total = 110%
				"statut": "En attente"
			})
			charge.insert()
	
	def test_validation_negative_amount(self):
		"""Test de validation avec montant négatif"""
		with self.assertRaises(frappe.ValidationError):
			charge = frappe.get_doc({
				"doctype": "Charge",
				"appartement_id": self.appartement.name,
				"type_charge": "Travaux",
				"categorie": "Ponctuelle",
				"description": "Test",
				"montant": -100,
				"date_charge": nowdate(),
				"statut": "En attente"
			})
			charge.insert()
	
	def test_validation_future_date(self):
		"""Test de validation avec date future"""
		with self.assertRaises(frappe.ValidationError):
			charge = frappe.get_doc({
				"doctype": "Charge",
				"appartement_id": self.appartement.name,
				"type_charge": "Travaux",
				"categorie": "Ponctuelle",
				"description": "Test",
				"montant": 100,
				"date_charge": add_days(nowdate(), 1),
				"statut": "En attente"
			})
			charge.insert()
	
	def test_validation_payment_details_required(self):
		"""Test de validation des détails de paiement obligatoires"""
		with self.assertRaises(frappe.ValidationError):
			charge = frappe.get_doc({
				"doctype": "Charge",
				"appartement_id": self.appartement.name,
				"type_charge": "Travaux",
				"categorie": "Ponctuelle",
				"description": "Test",
				"montant": 100,
				"date_charge": nowdate(),
				"statut": "Payée"  # Statut payée sans date ni méthode
			})
			charge.insert()
	
	def test_validation_location_appartement_mismatch(self):
		"""Test de validation de cohérence location-appartement"""
		# Crée un autre appartement
		autre_appartement = frappe.get_doc({
			"doctype": "Appartement",
			"proprietaire_id": self.proprietaire.name,
			"adresse": "456 Autre Rue",
			"ville": "Lyon",
			"code_postal": "69001",
			"surface": 30,
			"nombre_pieces": 1,
			"statut": "Disponible"
		})
		autre_appartement.insert()
		
		with self.assertRaises(frappe.ValidationError):
			charge = frappe.get_doc({
				"doctype": "Charge",
				"appartement_id": autre_appartement.name,  # Appartement différent
				"location_longue_duree_id": self.location_longue.name,  # Location sur autre appartement
				"type_charge": "Charges locatives",
				"categorie": "Récurrente",
				"description": "Test",
				"montant": 100,
				"date_charge": nowdate(),
				"statut": "En attente"
			})
			charge.insert()
	
	def test_validate_charge(self):
		"""Test de validation d'une charge"""
		charge = frappe.get_doc({
			"doctype": "Charge",
			"appartement_id": self.appartement.name,
			"type_charge": "Entretien",
			"categorie": "Ponctuelle",
			"description": "Nettoyage",
			"montant": 150,
			"date_charge": nowdate(),
			"statut": "En attente"
		})
		charge.insert()
		
		result = charge.validate_charge()
		
		self.assertEqual(charge.statut, "Validée")
		self.assertIn("validée", result["message"])
	
	def test_mark_as_paid(self):
		"""Test de marquage d'une charge comme payée"""
		charge = frappe.get_doc({
			"doctype": "Charge",
			"appartement_id": self.appartement.name,
			"type_charge": "Assurance",
			"categorie": "Récurrente",
			"description": "Assurance habitation",
			"montant": 300,
			"date_charge": nowdate(),
			"statut": "En attente"
		})
		charge.insert()
		
		# Valide d'abord la charge
		charge.validate_charge()
		
		# Marque comme payée
		result = charge.mark_as_paid(
			payment_date=nowdate(),
			payment_method="Virement bancaire",
			payment_reference="REF123"
		)
		
		self.assertEqual(charge.statut, "Payée")
		self.assertEqual(charge.date_paiement, nowdate())
		self.assertEqual(charge.methode_paiement, "Virement bancaire")
		self.assertEqual(charge.reference_paiement, "REF123")
		self.assertIn("payée", result["message"])
	
	def test_mark_as_reimbursed(self):
		"""Test de marquage d'une charge comme remboursée"""
		charge = frappe.get_doc({
			"doctype": "Charge",
			"appartement_id": self.appartement.name,
			"type_charge": "Travaux",
			"categorie": "Urgente",
			"description": "Réparation urgente",
			"montant": 800,
			"date_charge": nowdate(),
			"statut": "En attente"
		})
		charge.insert()
		
		# Valide et marque comme payée
		charge.validate_charge()
		charge.mark_as_paid()
		
		# Marque comme remboursée
		result = charge.mark_as_reimbursed(
			reimbursement_date=nowdate(),
			reimbursement_method="Chèque",
			reimbursement_reference="CHQ456"
		)
		
		self.assertEqual(charge.statut, "Remboursée")
		self.assertEqual(charge.methode_paiement, "Chèque")
		self.assertEqual(charge.reference_paiement, "CHQ456")
		self.assertIn("remboursée", result["message"])
	
	def test_reject_charge(self):
		"""Test de rejet d'une charge"""
		charge = frappe.get_doc({
			"doctype": "Charge",
			"appartement_id": self.appartement.name,
			"type_charge": "Autre",
			"categorie": "Ponctuelle",
			"description": "Charge douteuse",
			"montant": 100,
			"date_charge": nowdate(),
			"statut": "En attente"
		})
		charge.insert()
		
		reason = "Facture non conforme"
		result = charge.reject_charge(reason)
		
		self.assertEqual(charge.statut, "Rejetée")
		self.assertIn(reason, charge.commentaires)
		self.assertIn("rejetée", result["message"])
	
	def test_get_charge_details(self):
		"""Test de récupération des détails complets de la charge"""
		charge = frappe.get_doc({
			"doctype": "Charge",
			"appartement_id": self.appartement.name,
			"location_longue_duree_id": self.location_longue.name,
			"type_charge": "Charges locatives",
			"categorie": "Récurrente",
			"description": "Charges mensuelles",
			"montant": 250,
			"date_charge": nowdate(),
			"fournisseur": "Syndic Test",
			"numero_facture": "FAC001",
			"repartition_locataire": 80,
			"repartition_proprietaire": 20,
			"statut": "Validée"
		})
		charge.insert()
		
		details = charge.get_charge_details()
		
		self.assertIn("charge", details)
		self.assertIn("appartement", details)
		self.assertIn("proprietaire", details)
		self.assertIn("location_longue_duree", details)
		self.assertEqual(details["charge"]["montant"], 250)
		self.assertEqual(details["charge"]["montant_locataire"], 200)
		self.assertEqual(details["charge"]["montant_proprietaire"], 50)
		self.assertEqual(details["proprietaire"]["nom_complet"], "Jean Dupont")
		self.assertEqual(details["location_longue_duree"]["locataire_nom"], "Marie Martin")
	
	def test_calculate_charges_statistics(self):
		"""Test de calcul des statistiques des charges"""
		# Crée plusieurs charges
		charge1 = frappe.get_doc({
			"doctype": "Charge",
			"appartement_id": self.appartement.name,
			"type_charge": "Travaux",
			"categorie": "Ponctuelle",
			"description": "Travaux 1",
			"montant": 500,
			"date_charge": nowdate(),
			"repartition_locataire": 0,
			"repartition_proprietaire": 100,
			"statut": "Validée"
		})
		charge1.insert()
		
		charge2 = frappe.get_doc({
			"doctype": "Charge",
			"appartement_id": self.appartement.name,
			"type_charge": "Charges locatives",
			"categorie": "Récurrente",
			"description": "Charges 1",
			"montant": 200,
			"date_charge": nowdate(),
			"repartition_locataire": 70,
			"repartition_proprietaire": 30,
			"statut": "Payée"
		})
		charge2.insert()
		
		stats = charge1.calculate_charges_statistics(appartement_id=self.appartement.name)
		
		self.assertEqual(stats["total_charges"], 2)
		self.assertEqual(stats["montant_total"], 700)
		self.assertEqual(stats["montant_locataire_total"], 140)  # 200 * 70%
		self.assertEqual(stats["montant_proprietaire_total"], 560)  # 500 + (200 * 30%)
		self.assertIn("Travaux", stats["repartition_par_type"])
		self.assertIn("Charges locatives", stats["repartition_par_type"])
		self.assertIn("Ponctuelle", stats["repartition_par_categorie"])
		self.assertIn("Récurrente", stats["repartition_par_categorie"])
		self.assertIn("Validée", stats["repartition_par_statut"])
		self.assertIn("Payée", stats["repartition_par_statut"])
	
	def test_get_pending_charges(self):
		"""Test de récupération des charges en attente"""
		# Crée des charges avec différents statuts
		charge1 = frappe.get_doc({
			"doctype": "Charge",
			"appartement_id": self.appartement.name,
			"type_charge": "Travaux",
			"categorie": "Ponctuelle",
			"description": "En attente",
			"montant": 300,
			"date_charge": nowdate(),
			"statut": "En attente"
		})
		charge1.insert()
		
		charge2 = frappe.get_doc({
			"doctype": "Charge",
			"appartement_id": self.appartement.name,
			"type_charge": "Entretien",
			"categorie": "Récurrente",
			"description": "Validée",
			"montant": 150,
			"date_charge": nowdate(),
			"statut": "Validée"
		})
		charge2.insert()
		
		charge3 = frappe.get_doc({
			"doctype": "Charge",
			"appartement_id": self.appartement.name,
			"type_charge": "Assurance",
			"categorie": "Récurrente",
			"description": "Payée",
			"montant": 200,
			"date_charge": nowdate(),
			"statut": "Payée"
		})
		charge3.insert()
		
		pending = charge1.get_pending_charges(appartement_id=self.appartement.name)
		
		self.assertEqual(len(pending), 2)  # En attente + Validée
		statuts = [c["statut"] for c in pending]
		self.assertIn("En attente", statuts)
		self.assertIn("Validée", statuts)
		self.assertNotIn("Payée", statuts)
	
	def test_get_pending_charges_by_proprietaire(self):
		"""Test de récupération des charges en attente par propriétaire"""
		charge = frappe.get_doc({
			"doctype": "Charge",
			"appartement_id": self.appartement.name,
			"type_charge": "Taxes",
			"categorie": "Récurrente",
			"description": "Taxe foncière",
			"montant": 600,
			"date_charge": nowdate(),
			"statut": "En attente"
		})
		charge.insert()
		
		pending = charge.get_pending_charges(proprietaire_id=self.proprietaire.name)
		
		self.assertEqual(len(pending), 1)
		self.assertEqual(pending[0]["description"], "Taxe foncière")
		self.assertEqual(pending[0]["appartement_id"], self.appartement.name)
	
	def test_validation_mark_paid_without_validation(self):
		"""Test d'erreur lors du marquage comme payée sans validation"""
		charge = frappe.get_doc({
			"doctype": "Charge",
			"appartement_id": self.appartement.name,
			"type_charge": "Travaux",
			"categorie": "Ponctuelle",
			"description": "Test",
			"montant": 100,
			"date_charge": nowdate(),
			"statut": "En attente"
		})
		charge.insert()
		
		with self.assertRaises(frappe.ValidationError):
			charge.mark_as_paid()
	
	def test_validation_mark_reimbursed_without_payment(self):
		"""Test d'erreur lors du marquage comme remboursée sans paiement"""
		charge = frappe.get_doc({
			"doctype": "Charge",
			"appartement_id": self.appartement.name,
			"type_charge": "Travaux",
			"categorie": "Ponctuelle",
			"description": "Test",
			"montant": 100,
			"date_charge": nowdate(),
			"statut": "Validée"
		})
		charge.insert()
		
		with self.assertRaises(frappe.ValidationError):
			charge.mark_as_reimbursed()
	
	def test_validation_reject_paid_charge(self):
		"""Test d'erreur lors du rejet d'une charge payée"""
		charge = frappe.get_doc({
			"doctype": "Charge",
			"appartement_id": self.appartement.name,
			"type_charge": "Travaux",
			"categorie": "Ponctuelle",
			"description": "Test",
			"montant": 100,
			"date_charge": nowdate(),
			"statut": "En attente"
		})
		charge.insert()
		
		# Valide et marque comme payée
		charge.validate_charge()
		charge.mark_as_paid()
		
		with self.assertRaises(frappe.ValidationError):
			charge.reject_charge("Test de rejet")
	
	def test_default_repartition_values(self):
		"""Test des valeurs par défaut de répartition"""
		charge = frappe.get_doc({
			"doctype": "Charge",
			"appartement_id": self.appartement.name,
			"type_charge": "Travaux",
			"categorie": "Ponctuelle",
			"description": "Test répartition par défaut",
			"montant": 400,
			"date_charge": nowdate(),
			"statut": "En attente"
			# Pas de répartition spécifiée
		})
		charge.insert()
		
		self.assertEqual(charge.repartition_locataire, 0)
		self.assertEqual(charge.repartition_proprietaire, 100)
		self.assertEqual(charge.montant_locataire, 0)
		self.assertEqual(charge.montant_proprietaire, 400)