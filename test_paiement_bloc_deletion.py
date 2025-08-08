#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de suppression d'un Paiement Bloc et vérification de la mise à jour du Location Bloc
"""

import frappe
from frappe.utils import flt

def test_paiement_bloc_deletion():
    """
    Test la suppression d'un Paiement Bloc et vérifie que le Location Bloc est mis à jour
    """
    print("\n=== Test de suppression Paiement Bloc ===")
    
    # 1. Trouver un Location Bloc existant avec des paiements
    location_blocs = frappe.get_all("Location Bloc", 
                                   filters={"montant_total_paye": [">=", 0]},
                                   fields=["name", "montant_total_paye", "solde_restant", "pourcentage_paye"],
                                   limit=5)
    
    if not location_blocs:
        print("❌ Aucun Location Bloc trouvé")
        return
    
    print(f"📋 Location Blocs trouvés: {len(location_blocs)}")
    for bloc in location_blocs:
        print(f"  - {bloc.name}: Payé={bloc.montant_total_paye}, Solde={bloc.solde_restant}, %={bloc.pourcentage_paye}")
    
    # 2. Trouver des Paiement Bloc pour le premier Location Bloc
    location_bloc_id = location_blocs[0].name
    paiements = frappe.get_all("Paiement Bloc",
                              filters={"location_bloc_id": location_bloc_id},
                              fields=["name", "montant_paiement", "date_paiement"])
    
    print(f"\n💳 Paiements pour Location Bloc {location_bloc_id}:")
    if not paiements:
        print("  Aucun paiement trouvé")
        return
    
    for paiement in paiements:
        print(f"  - {paiement.name}: {paiement.montant_paiement}€ le {paiement.date_paiement}")
    
    # 3. Sauvegarder l'état avant suppression
    location_bloc_avant = frappe.get_doc("Location Bloc", location_bloc_id)
    print(f"\n📊 État AVANT suppression:")
    print(f"  - Montant total payé: {location_bloc_avant.montant_total_paye}€")
    print(f"  - Solde restant: {location_bloc_avant.solde_restant}€")
    print(f"  - Pourcentage payé: {location_bloc_avant.pourcentage_paye}%")
    
    # 4. Supprimer le premier paiement
    paiement_a_supprimer = paiements[0]
    montant_supprime = paiement_a_supprimer.montant_paiement
    
    print(f"\n🗑️ Suppression du paiement {paiement_a_supprimer.name} ({montant_supprime}€)...")
    
    try:
        # Supprimer le document
        frappe.delete_doc("Paiement Bloc", paiement_a_supprimer.name)
        frappe.db.commit()
        print("✅ Paiement supprimé avec succès")
        
        # 5. Vérifier l'état après suppression
        location_bloc_apres = frappe.get_doc("Location Bloc", location_bloc_id)
        print(f"\n📊 État APRÈS suppression:")
        print(f"  - Montant total payé: {location_bloc_apres.montant_total_paye}€")
        print(f"  - Solde restant: {location_bloc_apres.solde_restant}€")
        print(f"  - Pourcentage payé: {location_bloc_apres.pourcentage_paye}%")
        
        # 6. Vérifier que les calculs sont corrects
        montant_attendu = flt(location_bloc_avant.montant_total_paye) - flt(montant_supprime)
        solde_attendu = flt(location_bloc_avant.solde_restant) + flt(montant_supprime)
        
        print(f"\n🔍 Vérification des calculs:")
        print(f"  - Montant attendu: {montant_attendu}€ (actuel: {location_bloc_apres.montant_total_paye}€)")
        print(f"  - Solde attendu: {solde_attendu}€ (actuel: {location_bloc_apres.solde_restant}€)")
        
        if abs(flt(location_bloc_apres.montant_total_paye) - montant_attendu) < 0.01:
            print("✅ Montant total payé correctement mis à jour")
        else:
            print("❌ Erreur dans le calcul du montant total payé")
            
        if abs(flt(location_bloc_apres.solde_restant) - solde_attendu) < 0.01:
            print("✅ Solde restant correctement mis à jour")
        else:
            print("❌ Erreur dans le calcul du solde restant")
            
    except Exception as e:
        print(f"❌ Erreur lors de la suppression: {str(e)}")
        frappe.db.rollback()

def check_hooks_configuration():
    """
    Vérifie que les hooks sont bien configurés
    """
    print("\n=== Vérification de la configuration des hooks ===")
    
    # Vérifier les hooks dans hooks.py
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

if __name__ == "__main__":
    # Initialiser Frappe
    frappe.init(site="localhost")
    frappe.connect()
    
    try:
        check_hooks_configuration()
        test_paiement_bloc_deletion()
    except Exception as e:
        print(f"❌ Erreur générale: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        frappe.destroy()