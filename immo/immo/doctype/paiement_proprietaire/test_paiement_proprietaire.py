# Copyright (c) 2024, Frappe Technologies and Contributors
# See license.txt

import frappe
import unittest
from frappe.utils import nowdate, add_days


class TestPaiementProprietaire(unittest.TestCase):
	"""Tests pour le doctype Paiement Propriétaire"""
	
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
		
		# Crée une mensualité de test
		self.mensualite = frappe.get_doc({
			"doctype": "Mensualite",
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
			"doctype": "Paiement Propriétaire",
			"mensualite_id": self.mensualite.name,
			"location_longue_duree_id": self.location_longue.name,
			"type_paiement": "Loyer mensuel",
			"montant": 900,
			"date_paiement": nowdate(),
			"methode_paiement": "Virement bancaire",
			"statut": "En attente"
		})
		paiement.insert()
		
		self.assertEqual(paiement.montant_net, 900)
		self.assertEqual(paiement.location_longue_duree_id, self.location_longue.name)
		self.assertIsNotNone(paiement.date_creation)
	
	def test_create_paiement_location_courte(self):
		"""Test de création d'un paiement pour une location courte durée"""
		paiement = frappe.get_doc({
			"doctype": "Paiement Propriétaire",
			"location_courte_duree_id": self.location_courte.name,
			"type_paiement": "Séjour court",
			"montant": 350,
			"date_paiement": nowdate(),
			"methode_paiement": "Virement bancaire",
			"statut": "En attente"
		})
		paiement.insert()
		
		self.assertEqual(paiement.montant, 350)
		self.assertEqual(paiement.location_courte_duree_id, self.location_courte.name)
	
	def test_calculate_net_amount_with_fees(self):
		"""Test du calcul du montant net avec frais de transaction"""
		paiement = frappe.get_doc({
			"doctype": "Paiement Propriétaire",
			"location_courte_duree_id": self.location_courte.name,
			"type_paiement": "Séjour court",
			"montant": 350,
			"frais_transaction": 10,
			"date_paiement": nowdate(),
			"methode_paiement": "Virement bancaire",
			"statut": "En attente"
		})
		paiement.insert()
		
		self.assertEqual(paiement.montant_net, 340)  # 350 - 10
	
	def test_validation_no_reference(self):
		"""Test de validation sans référence de location"""
		with self.assertRaises(frappe.ValidationError):
			paiement = frappe.get_doc({
				"doctype": "Paiement Propriétaire",
				"type_paiement": "Loyer mensuel",
				"montant": 900,
				"date_paiement": nowdate(),
				"methode_paiement": "Virement bancaire",
				"statut": "En attente"
			})
			paiement.insert()
	
	def test_validation_negative_amount(self):
		"""Test de validation avec montant négatif"""
		with self.assertRaises(frappe.ValidationError):
			paiement = frappe.get_doc({
				"doctype": "Paiement Propriétaire",
				"location_courte_duree_id": self.location_courte.name,
				"type_paiement": "Séjour court",
				"montant": -100,
				"date_paiement": nowdate(),
				"methode_paiement": "Virement bancaire",
				"statut": "En attente"
			})
			paiement.insert()
	
	def test_schedule_payment(self):
		"""Test de programmation d'un paiement"""
		paiement = frappe.get_doc({
			"doctype": "Paiement Propriétaire",
			"mensualite_id": self.mensualite.name,
			"location_longue_duree_id": self.location_longue.name,
			"type_paiement": "Loyer mensuel",
			"montant": 900,
			"date_paiement": nowdate(),
			"methode_paiement": "Virement bancaire",
			"statut": "En attente"
		})
		paiement.insert()
		
		scheduled_date = add_days(nowdate(), 5)
		result = paiement.schedule_payment(scheduled_date)
		
		self.assertEqual(paiement.statut, "Programmé")
		self.assertEqual(paiement.date_paiement, scheduled_date)
		self.assertIn("programmé", result["message"])
	
	def test_mark_as_sent(self):
		"""Test de marquage d'un paiement comme envoyé"""
		paiement = frappe.get_doc({
			"doctype": "Paiement Propriétaire",
			"location_courte_duree_id": self.location_courte.name,
			"type_paiement": "Séjour court",
			"montant": 350,
			"date_paiement": add_days(nowdate(), 2),
			"methode_paiement": "Virement bancaire",
			"statut": "Programmé"
		})
		paiement.insert()
		
		result = paiement.mark_as_sent()
		
		self.assertEqual(paiement.statut, "Envoyé")
		self.assertEqual(paiement.date_paiement, nowdate())  # Date mise à jour
		self.assertIn("envoyé", result["message"])
	
	def test_confirm_receipt(self):
		"""Test de confirmation de réception d'un paiement"""
		paiement = frappe.get_doc({
			"doctype": "Paiement Propriétaire",
			"mensualite_id": self.mensualite.name,
			"location_longue_duree_id": self.location_longue.name,
			"type_paiement": "Loyer mensuel",
			"montant": 900,
			"date_paiement": nowdate(),
			"methode_paiement": "Virement bancaire",
			"statut": "Envoyé"
		})
		paiement.insert()
		
		result = paiement.confirm_receipt()
		
		self.assertEqual(paiement.statut, "Reçu")
		self.assertIsNotNone(paiement.date_validation)
		self.assertEqual(paiement.valide_par, frappe.session.user)
		self.assertIn("confirmée", result["message"])
	
	def test_reject_payment(self):
		"""Test de rejet d'un paiement"""
		paiement = frappe.get_doc({
			"doctype": "Paiement Propriétaire",
			"location_courte_duree_id": self.location_courte.name,
			"type_paiement": "Séjour court",
			"montant": 350,
			"date_paiement": nowdate(),
			"methode_paiement": "Virement bancaire",
			"statut": "En attente"
		})
		paiement.insert()
		
		reason = "Problème de compte bancaire"
		result = paiement.reject_payment(reason)
		
		self.assertEqual(paiement.statut, "Rejeté")
		self.assertIn(reason, paiement.commentaires)
		self.assertIn("rejeté", result["message"])
	
	def test_update_mensualite_status(self):
		"""Test de mise à jour du statut de la mensualité"""
		paiement = frappe.get_doc({
			"doctype": "Paiement Propriétaire",
			"mensualite_id": self.mensualite.name,
			"location_longue_duree_id": self.location_longue.name,
			"type_paiement": "Loyer mensuel",
			"montant": 900,
			"date_paiement": nowdate(),
			"methode_paiement": "Virement bancaire",
			"reference_paiement": "REF456",
			"statut": "En attente"
		})
		paiement.insert()
		
		# Confirme la réception du paiement
		paiement.confirm_receipt()
		
		# Vérifie que la mensualité a été mise à jour
		mensualite = frappe.get_doc("Mensualite", self.mensualite.name)
		self.assertEqual(mensualite.statut_paiement_proprietaire, "Payé")
		self.assertEqual(mensualite.date_paiement_proprietaire, paiement.date_paiement)
		self.assertEqual(mensualite.methode_paiement_proprietaire, paiement.methode_paiement)
		self.assertEqual(mensualite.reference_paiement_proprietaire, paiement.reference_paiement)
	
	def test_get_payment_details(self):
		"""Test de récupération des détails complets du paiement"""
		paiement = frappe.get_doc({
			"doctype": "Paiement Propriétaire",
			"mensualite_id": self.mensualite.name,
			"location_longue_duree_id": self.location_longue.name,
			"type_paiement": "Loyer mensuel",
			"montant": 900,
			"date_paiement": nowdate(),
			"methode_paiement": "Virement bancaire",
			"statut": "Reçu"
		})
		paiement.insert()
		
		details = paiement.get_payment_details()
		
		self.assertIn("paiement", details)
		self.assertIn("location_longue_duree", details)
		self.assertIn("proprietaire", details)
		self.assertIn("mensualite", details)
		self.assertEqual(details["paiement"]["montant"], 900)
		self.assertEqual(details["proprietaire"]["nom_complet"], "Jean Dupont")
		self.assertEqual(details["location_longue_duree"]["locataire_nom"], "Marie Martin")
		self.assertEqual(details["mensualite"]["mois_annee"], "01/2024")
	
	def test_calculate_payment_statistics(self):
		"""Test de calcul des statistiques de paiement"""
		# Crée plusieurs paiements envoyés/reçus
		paiement1 = frappe.get_doc({
			"doctype": "Paiement Propriétaire",
			"location_courte_duree_id": self.location_courte.name,
			"type_paiement": "Séjour court",
			"montant": 350,
			"frais_transaction": 5,
			"date_paiement": nowdate(),
			"methode_paiement": "Virement bancaire",
			"statut": "Envoyé"
		})
		paiement1.insert()
		
		paiement2 = frappe.get_doc({
			"doctype": "Paiement Propriétaire",
			"mensualite_id": self.mensualite.name,
			"location_longue_duree_id": self.location_longue.name,
			"type_paiement": "Loyer mensuel",
			"montant": 900,
			"frais_transaction": 3,
			"date_paiement": nowdate(),
			"methode_paiement": "Chèque",
			"statut": "Reçu"
		})
		paiement2.insert()
		
		stats = paiement1.calculate_payment_statistics()
		
		self.assertEqual(stats["total_paiements"], 2)
		self.assertEqual(stats["montant_total"], 1250)
		self.assertEqual(stats["montant_net_total"], 1242)  # 1250 - 8 frais
		self.assertEqual(stats["frais_total"], 8)
		self.assertIn("Séjour court", stats["repartition_par_type"])
		self.assertIn("Loyer mensuel", stats["repartition_par_type"])
		self.assertIn("Virement bancaire", stats["repartition_par_methode"])
		self.assertIn("Chèque", stats["repartition_par_methode"])
		self.assertIn("Envoyé", stats["repartition_par_statut"])
		self.assertIn("Reçu", stats["repartition_par_statut"])
	
	def test_get_pending_payments(self):
		"""Test de récupération des paiements en attente"""
		# Crée des paiements en attente et programmés
		paiement1 = frappe.get_doc({
			"doctype": "Paiement Propriétaire",
			"location_courte_duree_id": self.location_courte.name,
			"type_paiement": "Séjour court",
			"montant": 350,
			"date_paiement": nowdate(),
			"methode_paiement": "Virement bancaire",
			"statut": "En attente"
		})
		paiement1.insert()
		
		paiement2 = frappe.get_doc({
			"doctype": "Paiement Propriétaire",
			"mensualite_id": self.mensualite.name,
			"location_longue_duree_id": self.location_longue.name,
			"type_paiement": "Loyer mensuel",
			"montant": 900,
			"date_paiement": add_days(nowdate(), 3),
			"methode_paiement": "Virement bancaire",
			"statut": "Programmé"
		})
		paiement2.insert()
		
		# Crée un paiement envoyé (ne doit pas apparaître)
		paiement3 = frappe.get_doc({
			"doctype": "Paiement Propriétaire",
			"location_courte_duree_id": self.location_courte.name,
			"type_paiement": "Séjour court",
			"montant": 300,
			"date_paiement": nowdate(),
			"methode_paiement": "Virement bancaire",
			"statut": "Envoyé"
		})
		paiement3.insert()
		
		pending = paiement1.get_pending_payments(self.proprietaire.name)
		
		self.assertEqual(len(pending), 2)
		statuts = [p["statut"] for p in pending]
		self.assertIn("En attente", statuts)
		self.assertIn("Programmé", statuts)
		self.assertNotIn("Envoyé", statuts)
	
	def test_validation_received_payment_modification(self):
		"""Test de validation empêchant la modification d'un paiement reçu"""
		paiement = frappe.get_doc({
			"doctype": "Paiement Propriétaire",
			"location_courte_duree_id": self.location_courte.name,
			"type_paiement": "Séjour court",
			"montant": 350,
			"date_paiement": nowdate(),
			"methode_paiement": "Virement bancaire",
			"statut": "En attente"
		})
		paiement.insert()
		
		# Confirme la réception
		paiement.confirm_receipt()
		
		# Tente de modifier le statut
		with self.assertRaises(frappe.ValidationError):
			paiement.statut = "En attente"
			paiement.save()
	
	def test_reject_received_payment(self):
		"""Test de rejet d'un paiement déjà reçu"""
		paiement = frappe.get_doc({
			"doctype": "Paiement Propriétaire",
			"location_courte_duree_id": self.location_courte.name,
			"type_paiement": "Séjour court",
			"montant": 350,
			"date_paiement": nowdate(),
			"methode_paiement": "Virement bancaire",
			"statut": "Reçu"
		})
		paiement.insert()
		
		with self.assertRaises(frappe.ValidationError):
			paiement.reject_payment("Test de rejet")
	
	def test_validation_future_payment_date_for_sent(self):
		"""Test de validation de date future pour paiement envoyé"""
		with self.assertRaises(frappe.ValidationError):
			paiement = frappe.get_doc({
				"doctype": "Paiement Propriétaire",
				"location_courte_duree_id": self.location_courte.name,
				"type_paiement": "Séjour court",
				"montant": 350,
				"date_paiement": add_days(nowdate(), 1),
				"methode_paiement": "Virement bancaire",
				"statut": "Envoyé"
			})
			paiement.insert()
	
	def test_reschedule_sent_payment(self):
		"""Test de reprogrammation d'un paiement envoyé"""
		paiement = frappe.get_doc({
			"doctype": "Paiement Propriétaire",
			"location_courte_duree_id": self.location_courte.name,
			"type_paiement": "Séjour court",
			"montant": 350,
			"date_paiement": nowdate(),
			"methode_paiement": "Virement bancaire",
			"statut": "Envoyé"
		})
		paiement.insert()
		
		with self.assertRaises(frappe.ValidationError):
			paiement.schedule_payment(add_days(nowdate(), 5))