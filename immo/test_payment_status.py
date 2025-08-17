#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de test pour vérifier le calcul du statut des paiements
dans Location Courte Durée
"""

import frappe


def test_payment_status_calculation():
	"""Teste le calcul du statut des paiements"""
	try:
		print("🧪 Test du calcul du statut des paiements...")
		
		# Récupérer une location courte durée existante
		locations = frappe.get_all("Location Courte Duree", 
			fields=["name", "montant_total_locataire", "montant_total_proprietaire"],
			limit=1)
		
		if not locations:
			print("❌ Aucune location courte durée trouvée")
			return
		
		location = locations[0]
		print(f"📍 Location testée: {location.name}")
		print(f"💰 Montant total locataire: {location.montant_total_locataire}")
		print(f"💰 Montant total propriétaire: {location.montant_total_proprietaire}")
		
		# Appeler la méthode de calcul
		doc = frappe.get_doc("Location Courte Duree", location.name)
		result = doc.refresh_payment_status()
		
		print("✅ Résultat du calcul:")
		print(f"   - Montant payé locataire: {result.get('montant_paye_locataire', 0)}")
		print(f"   - Montant restant locataire: {result.get('montant_restant_locataire', 0)}")
		print(f"   - Statut locataire: {result.get('statut_paiement_locataire', 'N/A')}")
		print(f"   - Montant payé propriétaire: {result.get('montant_paye_proprietaire', 0)}")
		print(f"   - Montant restant propriétaire: {result.get('montant_restant_proprietaire', 0)}")
		print(f"   - Statut propriétaire: {result.get('statut_paiement_proprietaire', 'N/A')}")
		
		print("🎉 Test terminé avec succès!")
		
	except Exception as e:
		print(f"❌ Erreur lors du test: {str(e)}")
		frappe.log_error(f"Erreur test statut paiements: {str(e)}")


def test_payment_creation():
	"""Teste la création d'un paiement et la mise à jour automatique"""
	try:
		print("\n🧪 Test de création de paiement...")
		
		# Récupérer une location courte durée
		locations = frappe.get_all("Location Courte Duree", 
			fields=["name", "montant_total_locataire"],
			limit=1)
		
		if not locations:
			print("❌ Aucune location courte durée trouvée")
			return
		
		location = locations[0]
		print(f"📍 Location testée: {location.name}")
		
		# Créer un paiement locataire de test
		paiement_data = {
			"doctype": "Paiement Locataire",
			"location_courte_duree_id": location.name,
			"status": "Payé",
			"type_paiement": "Court Séjour",
			"montant": 100.00,
			"date_paiement": frappe.utils.today(),
			"methode_paiement": "Virement",
			"reference_paiement": "TEST-001"
		}
		
		paiement = frappe.get_doc(paiement_data)
		paiement.insert()
		print(f"✅ Paiement créé: {paiement.name}")
		
		# Vérifier que le statut a été mis à jour
		frappe.db.commit()
		
		# Recharger la location
		location_doc = frappe.get_doc("Location Courte Durée", location.name)
		print(f"💰 Montant payé locataire après paiement: {location_doc.montant_paye_locataire}")
		print(f"💰 Montant restant locataire après paiement: {location_doc.montant_restant_locataire}")
		print(f"📊 Statut locataire après paiement: {location_doc.statut_paiement_locataire}")
		
		# Nettoyer le paiement de test
		paiement.delete()
		frappe.db.commit()
		print("🧹 Paiement de test supprimé")
		
		print("🎉 Test de création terminé avec succès!")
		
	except Exception as e:
		print(f"❌ Erreur lors du test de création: {str(e)}")
		frappe.log_error(f"Erreur test création paiement: {str(e)}")


if __name__ == "__main__":
	print("🚀 Démarrage des tests du statut des paiements...")
	
	test_payment_status_calculation()
	test_payment_creation()
	
	print("\n🏁 Tous les tests sont terminés!")
