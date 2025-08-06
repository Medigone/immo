import frappe

def test_commission_creation():
    try:
        print("=== Test de création de commission ===")
        
        # Vérifier si des référents existent
        referents = frappe.get_all('Referent', limit=1)
        if not referents:
            print("Aucun référent trouvé")
            return
        
        # Vérifier si des locations courtes durée existent
        locations = frappe.get_all('Location Courte Duree', limit=1)
        if not locations:
            print("Aucune location courte durée trouvée")
            return
        
        print(f"Référent trouvé: {referents[0].name}")
        print(f"Location trouvée: {locations[0].name}")
        
        # Test de création d'une commission
        commission = frappe.new_doc('Commission')
        commission.referent_id = referents[0].name
        commission.location_courte_duree_id = locations[0].name
        commission.montant_commission = 100
        commission.pourcentage_commission = 5
        commission.statut_paiement = 'En attente'
        
        print("Tentative d'insertion de la commission...")
        commission.insert()
        print(f"Commission créée avec succès: {commission.name}")
        
    except Exception as e:
        print(f"Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_commission_creation()