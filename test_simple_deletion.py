#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test simple de suppression d'un Paiement Bloc
"""

import os
import sys

# Ajouter le chemin de Frappe
sys.path.insert(0, '/home/wezri/frappe-bench/apps/frappe')
sys.path.insert(0, '/home/wezri/frappe-bench/apps/immo')

import frappe
from frappe.utils import flt

def test_hooks_configuration():
    """
    Vérifie que les hooks sont bien configurés
    """
    print("\n=== Vérification de la configuration des hooks ===")
    
    try:
        # Importer les hooks
        from immo.hooks import doc_events
        
        if "Paiement Bloc" in doc_events:
            hooks_paiement = doc_events["Paiement Bloc"]
            print(f"📋 Hooks configurés pour Paiement Bloc: {list(hooks_paiement.keys())}")
            
            if "on_trash" in hooks_paiement:
                print(f"✅ Hook on_trash configuré: {hooks_paiement['on_trash']}")
            else:
                print("❌ Hook on_trash manquant")
                
            if "on_update" in hooks_paiement:
                print(f"✅ Hook on_update configuré: {hooks_paiement['on_update']}")
            else:
                print("❌ Hook on_update manquant")
        else:
            print("❌ Aucun hook configuré pour Paiement Bloc")
            
    except Exception as e:
        print(f"❌ Erreur lors de la vérification des hooks: {str(e)}")

def test_deletion_logic():
    """
    Test la logique de suppression sans utiliser Frappe
    """
    print("\n=== Test de la logique de suppression ===")
    
    try:
        # Initialiser Frappe
        frappe.init(site="imo.intrapro.net")
        frappe.connect()
        
        # Trouver des Location Blocs avec des paiements
        location_blocs = frappe.get_all("Location Bloc", 
                                       filters={"montant_total_paye": [">=", 0]},
                                       fields=["name", "montant_total_paye", "solde_restant"],
                                       limit=3)
        
        if not location_blocs:
            print("❌ Aucun Location Bloc trouvé")
            return
        
        print(f"📋 Location Blocs trouvés: {len(location_blocs)}")
        for bloc in location_blocs:
            print(f"  - {bloc.name}: Payé={bloc.montant_total_paye}€, Solde={bloc.solde_restant}€")
            
            # Trouver les paiements pour ce bloc
            paiements = frappe.get_all("Paiement Bloc",
                                      filters={"location_bloc_id": bloc.name},
                                      fields=["name", "montant_paiement"],
                                      limit=3)
            
            if paiements:
                print(f"    💳 Paiements: {len(paiements)}")
                for p in paiements:
                    print(f"      - {p.name}: {p.montant_paiement}€")
            else:
                print(f"    💳 Aucun paiement")
        
        # Test de la fonction de mise à jour
        if location_blocs and frappe.get_all("Paiement Bloc", filters={"location_bloc_id": location_blocs[0].name}, limit=1):
            print(f"\n🧪 Test de la fonction update_location_bloc_payment_status")
            
            # Importer la fonction
            from immo.hooks_handlers.paiement_bloc import update_location_bloc_payment_status
            
            # Créer un objet mock pour tester
            class MockPaiement:
                def __init__(self, location_bloc_id, name, montant):
                    self.location_bloc_id = location_bloc_id
                    self.name = name
                    self.montant_paiement = montant
            
            mock_paiement = MockPaiement(location_blocs[0].name, "TEST", 100)
            
            # Tester la fonction
            print(f"   Appel de update_location_bloc_payment_status pour {mock_paiement.location_bloc_id}")
            update_location_bloc_payment_status(mock_paiement)
            print(f"   ✅ Fonction exécutée sans erreur")
        
    except Exception as e:
        print(f"❌ Erreur lors du test: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            frappe.destroy()
        except:
            pass

if __name__ == "__main__":
    test_hooks_configuration()
    test_deletion_logic()