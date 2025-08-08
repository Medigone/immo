# Guide de Vérification - Suppression Paiement Bloc

## ✅ État de la Configuration

Tous les tests automatiques ont confirmé que la suppression d'un Paiement Bloc **devrait** mettre à jour automatiquement le Location Bloc associé.

### Hooks Configurés
- ✅ `on_trash`: `immo.hooks_handlers.paiement_bloc.on_trash`
- ✅ `on_update`: `immo.hooks_handlers.paiement_bloc.on_update`
- ✅ `validate`: `immo.hooks_handlers.paiement_bloc.validate`

### Logique de Mise à Jour
- ✅ Calcul SQL correct du montant total payé
- ✅ Mise à jour des champs `montant_total_paye`, `solde_restant`, `pourcentage_paye`
- ✅ Gestion d'erreur avec rollback
- ✅ Logs d'audit pour traçabilité

## 🔍 Si le Problème Persiste

Si après suppression d'un Paiement Bloc, le Location Bloc n'est pas mis à jour, vérifiez :

### 1. Application Installée
```bash
cd /home/wezri/frappe-bench
bench --site [VOTRE_SITE] list-apps
```
Vérifiez que `immo` apparaît dans la liste.

### 2. Hooks Chargés
```bash
cd /home/wezri/frappe-bench
bench restart
```
Redémarrez Frappe pour recharger les hooks.

### 3. Logs d'Erreur
```bash
cd /home/wezri/frappe-bench
bench --site [VOTRE_SITE] logs
```
Recherchez des erreurs liées à `Paiement Bloc` ou `Location Bloc`.

### 4. Test Manuel

1. **Avant suppression** :
   - Notez les valeurs de `montant_total_paye`, `solde_restant`, `pourcentage_paye` du Location Bloc
   - Notez le `montant_paiement` du Paiement Bloc à supprimer

2. **Suppression** :
   - Supprimez le Paiement Bloc via l'interface Frappe

3. **Après suppression** :
   - Rechargez la page du Location Bloc
   - Vérifiez que :
     - `montant_total_paye` a diminué du montant supprimé
     - `solde_restant` a augmenté du montant supprimé
     - `pourcentage_paye` a été recalculé

### 5. Vérification Base de Données

Si le problème persiste, vérifiez directement en base :

```sql
-- Vérifier les paiements restants pour un Location Bloc
SELECT 
    name, 
    montant_paiement, 
    date_paiement 
FROM `tabPaiement Bloc` 
WHERE location_bloc_id = 'VOTRE_LOCATION_BLOC_ID';

-- Vérifier les totaux du Location Bloc
SELECT 
    name,
    montant_total_proprietaire,
    montant_total_paye,
    solde_restant,
    pourcentage_paye
FROM `tabLocation Bloc` 
WHERE name = 'VOTRE_LOCATION_BLOC_ID';
```

## 🛠️ Dépannage Avancé

### Forcer la Mise à Jour

Si nécessaire, vous pouvez forcer la mise à jour d'un Location Bloc :

```python
# Via bench console
from immo.hooks_handlers.paiement_bloc import update_location_bloc_payment_status

# Créer un objet mock
class MockPaiement:
    def __init__(self, location_bloc_id):
        self.location_bloc_id = location_bloc_id
        self.name = "MANUAL_UPDATE"
        self.montant_paiement = 0

mock = MockPaiement("VOTRE_LOCATION_BLOC_ID")
update_location_bloc_payment_status(mock)
frappe.db.commit()
```

### Recalcul Complet

Pour recalculer tous les Location Blocs :

```python
# Via bench console
location_blocs = frappe.get_all("Location Bloc", fields=["name"])

for bloc in location_blocs:
    doc = frappe.get_doc("Location Bloc", bloc.name)
    doc.update_payment_tracking()
    print(f"Mis à jour: {bloc.name}")

frappe.db.commit()
```

## 📞 Support

Si le problème persiste après ces vérifications, fournissez :
- Les logs d'erreur Frappe
- Les valeurs avant/après suppression
- Le nom du site Frappe utilisé
- La version de Frappe et ERPNext