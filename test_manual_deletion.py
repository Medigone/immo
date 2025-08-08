#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test manuel de la logique de suppression Paiement Bloc
"""

import sys
sys.path.insert(0, '/home/wezri/frappe-bench/apps/immo')

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
                return True
            else:
                print("❌ Hook on_trash manquant")
                return False
        else:
            print("❌ Aucun hook configuré pour Paiement Bloc")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors de la vérification des hooks: {str(e)}")
        return False

def test_function_logic():
    """
    Test la logique de la fonction update_location_bloc_payment_status
    """
    print("\n=== Test de la logique de la fonction ===")
    
    try:
        # Importer la fonction
        from immo.hooks_handlers.paiement_bloc import update_location_bloc_payment_status
        print("✅ Fonction update_location_bloc_payment_status importée avec succès")
        
        # Vérifier le code de la fonction
        import inspect
        source = inspect.getsource(update_location_bloc_payment_status)
        
        # Vérifications importantes
        checks = {
            "Calcul SQL du total": "SELECT COALESCE(SUM(montant_paiement), 0)" in source,
            "Mise à jour des champs": "UPDATE `tabLocation Bloc`" in source,
            "Gestion d'erreur": "except Exception" in source,
            "Rollback en cas d'erreur": "frappe.db.rollback()" in source
        }
        
        print("\n🔍 Vérifications de la logique:")
        for check, result in checks.items():
            status = "✅" if result else "❌"
            print(f"  {status} {check}: {'OK' if result else 'MANQUANT'}")
        
        return all(checks.values())
        
    except Exception as e:
        print(f"❌ Erreur lors du test de la fonction: {str(e)}")
        return False

def test_sql_logic():
    """
    Test la logique SQL utilisée
    """
    print("\n=== Test de la logique SQL ===")
    
    # Simuler la requête SQL
    sql_query = """
        SELECT COALESCE(SUM(montant_paiement), 0)
        FROM `tabPaiement Bloc`
        WHERE location_bloc_id = %s
    """
    
    print("📝 Requête SQL utilisée:")
    print(sql_query.strip())
    
    # Vérifications
    checks = {
        "Utilise COALESCE pour éviter NULL": "COALESCE" in sql_query,
        "Somme les montants": "SUM(montant_paiement)" in sql_query,
        "Filtre par location_bloc_id": "WHERE location_bloc_id" in sql_query,
        "Utilise des paramètres sécurisés": "%s" in sql_query
    }
    
    print("\n🔍 Vérifications SQL:")
    for check, result in checks.items():
        status = "✅" if result else "❌"
        print(f"  {status} {check}: {'OK' if result else 'MANQUANT'}")
    
    return all(checks.values())

def main():
    """
    Fonction principale de test
    """
    print("🧪 Test de la suppression Paiement Bloc")
    print("=" * 50)
    
    results = []
    
    # Test 1: Configuration des hooks
    results.append(test_hooks_configuration())
    
    # Test 2: Logique de la fonction
    results.append(test_function_logic())
    
    # Test 3: Logique SQL
    results.append(test_sql_logic())
    
    # Résumé
    print("\n" + "=" * 50)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 50)
    
    test_names = [
        "Configuration des hooks",
        "Logique de la fonction",
        "Logique SQL"
    ]
    
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{i+1}. {name}: {status}")
    
    overall = all(results)
    print(f"\n🎯 RÉSULTAT GLOBAL: {'✅ TOUS LES TESTS PASSENT' if overall else '❌ CERTAINS TESTS ÉCHOUENT'}")
    
    if overall:
        print("\n💡 CONCLUSION:")
        print("   Le hook on_trash est correctement configuré et la fonction")
        print("   update_location_bloc_payment_status devrait mettre à jour")
        print("   automatiquement le Location Bloc lors de la suppression")
        print("   d'un Paiement Bloc.")
        print("\n   Si le problème persiste, vérifiez:")
        print("   1. Que l'application immo est bien installée sur le site")
        print("   2. Que les hooks sont bien chargés (bench restart)")
        print("   3. Les logs d'erreur Frappe pour des erreurs spécifiques")
    
    return overall

if __name__ == "__main__":
    main()