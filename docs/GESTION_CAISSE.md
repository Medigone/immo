# Fonctionnalité Gestion de Caisse

## Vue d'ensemble

La fonctionnalité **Gestion de Caisse** permet de centraliser et tracer tous les mouvements financiers de l'application immobilière. Elle offre une vision en temps réel de la trésorerie avec un suivi automatique des entrées et sorties liées aux différentes transactions.

## Architecture

### Nouveaux DocTypes

#### 1. Caisse
- **Description**: Compte principal de trésorerie (DocType unique/singleton)
- **Type**: Singleton (une seule instance autorisée)
- **Champs principaux**:
  - `nom_caisse`: Nom de la caisse (Data) - "Caisse Principale" par défaut
  - `solde_actuel`: Solde disponible (Currency)
  - `devise`: Devise (Select) - EUR par défaut
  - `date_creation`: Date de création (Datetime)
  - `date_derniere_maj`: Date dernière mise à jour (Datetime)



#### 2. Mouvement Caisse
- **Description**: Journal de tous les mouvements financiers
- **Champs principaux**:
  - `naming_series`: Série de nommage (MV-.YYYY.-.#####)
  - `type_mouvement`: Type (Select) - Entrée, Sortie
  - `type_transaction`: Type de transaction (Select):
    - Paiement locataire (Entrée +)
    - Paiement propriétaire (Sortie -)
    - Commission référent (Sortie -)
    - Charge (Sortie -)
    - Paiement bloc (Sortie -)
    - Apport manuel (Entrée +)
    - Retrait manuel (Sortie -)
  - `montant`: Montant (Currency)
  - `date_mouvement`: Date du mouvement (Datetime)
  - `reference_doctype`: Type de document source (Select)
  - `reference_docname`: Nom du document source (Data)
  - `description`: Description (Text)
  - `solde_avant`: Solde avant mouvement (Currency, read-only)
  - `solde_apres`: Solde après mouvement (Currency, read-only)
  - `reference_externe`: Référence externe (Data)
  - `notes`: Notes (Text)

#### 3. Apport Caisse
- **Description**: Gestion des apports manuels en caisse
- **Champs principaux**:
  - `naming_series`: Série de nommage (APPORT-.YYYY.-.#####)
  - `montant`: Montant (Currency)
  - `date_apport`: Date d'apport (Date)
  - `reference_apport`: Référence (Data)
  - `motif`: Motif de l'apport (Text)
  - `status`: Statut (Select) - En attente, Confirmé, Annulé
  - `date_validation`: Date de validation (Datetime)
  - `commentaires`: Commentaires (Text)

#### 4. Retrait Caisse
- **Description**: Gestion des retraits manuels de caisse
- **Champs principaux**:
  - `naming_series`: Série de nommage (RETRAIT-.YYYY.-.#####)
  - `montant`: Montant (Currency)
  - `date_retrait`: Date de retrait (Date)
  - `reference_retrait`: Référence (Data)
  - `motif`: Motif du retrait (Text)
  - `status`: Statut (Select) - En attente, Confirmé, Annulé
  - `date_validation`: Date de validation (Datetime)
  - `validateur`: Validateur (Link → User)
  - `commentaires`: Commentaires (Text)

### Modifications des DocTypes existants

#### Ajout de hooks dans les DocTypes financiers

**Charge**:
- Hook `after_insert` et `on_update` pour créer mouvement caisse (sortie -)
- Validation du solde suffisant avant paiement

**Commission**:
- Hook `on_update` pour créer mouvement caisse (sortie -) quand statut = "Payé"
- Validation du solde suffisant avant paiement

**Paiement Bloc**:
- Hook `after_insert` et `on_update` pour créer mouvement caisse (sortie -)
- Validation du solde suffisant avant paiement

**Paiement Locataire**:
- Hook `on_update` pour créer mouvement caisse (entrée +) quand statut = "Confirmé"

**Paiement Propriétaire**:
- Hook `on_update` pour créer mouvement caisse (sortie -) quand statut = "Envoyé"
- Validation du solde suffisant avant paiement

## Workflow

### 1. Initialisation de la caisse
1. Créer une caisse principale
2. Définir le solde initial via un apport
3. Configurer les permissions et responsables

### 2. Mouvements automatiques
1. **Paiement locataire confirmé** → Création automatique d'un mouvement d'entrée
2. **Paiement propriétaire envoyé** → Création automatique d'un mouvement de sortie
3. **Commission payée** → Création automatique d'un mouvement de sortie
4. **Charge payée** → Création automatique d'un mouvement de sortie
5. **Paiement bloc effectué** → Création automatique d'un mouvement de sortie

### 3. Mouvements manuels
1. Créer un apport ou retrait
2. Valider le montant et la méthode
3. Confirmer l'opération
4. Mise à jour automatique du solde

### 4. Validation et contrôles
1. Vérification du solde avant toute sortie
2. Validation des montants (positifs uniquement)
3. Traçabilité complète des opérations
4. Réconciliation automatique des soldes

## Fonctionnalités clés

### Validations automatiques
- Vérification du solde suffisant avant les sorties
- Validation des montants positifs
- Contrôle de cohérence des références
- Prévention des doublons de mouvements

### Calculs automatiques
- Mise à jour du solde en temps réel
- Calcul des soldes avant/après mouvement
- Statistiques de trésorerie
- Prévisions de cash-flow

### Dashboard et reporting
- Vue d'ensemble du solde actuel
- Historique des mouvements
- Graphiques des entrées/sorties
- Alertes de solde faible
- Rapports de trésorerie

## API disponibles

### Caisse
```python
# Obtenir le solde actuel
get_solde_caisse()

# Vérifier si le solde est suffisant
validate_solde_suffisant(montant)

# Obtenir les statistiques de caisse
get_caisse_statistics(periode=None)
```

### Mouvement Caisse
```python
# Créer un mouvement de caisse
create_mouvement_caisse(type_mouvement, montant, type_transaction, reference_doctype, reference_docname, description)

# Obtenir l'historique des mouvements
get_historique_mouvements(date_debut=None, date_fin=None, type_mouvement=None)

# Calculer le bilan financier
get_balance_sheet(periode=None)

# Réconcilier les soldes
reconcile_solde_caisse()
```

### Apport/Retrait Caisse
```python
# Créer un apport
create_apport_caisse(montant, methode, motif, reference=None)

# Créer un retrait
create_retrait_caisse(montant, methode, motif, reference=None)

# Valider un apport/retrait
validate_operation_caisse(operation_id, operation_type)
```

## Hooks et intégrations

### Hooks Frappe
```python
# hooks.py
doc_events = {
    "Paiement Locataire": {
        "on_update": "immo.hooks_handlers.caisse.on_paiement_locataire_update"
    },
    "Paiement Proprietaire": {
        "on_update": "immo.hooks_handlers.caisse.on_paiement_proprietaire_update"
    },
    "Commission": {
        "on_update": "immo.hooks_handlers.caisse.on_commission_update"
    },
    "Charge": {
        "after_insert": "immo.hooks_handlers.caisse.on_charge_insert",
        "on_update": "immo.hooks_handlers.caisse.on_charge_update"
    },
    "Paiement Bloc": {
        "after_insert": "immo.hooks_handlers.caisse.on_paiement_bloc_insert",
        "on_update": "immo.hooks_handlers.caisse.on_paiement_bloc_update"
    }
}
```

### Handlers de caisse
```python
# immo/hooks_handlers/caisse.py
def on_paiement_locataire_update(doc, method):
    """Créer mouvement d'entrée quand paiement confirmé"""
    if doc.statut == "Confirmé" and not has_mouvement_caisse(doc.doctype, doc.name):
        create_mouvement_caisse(
            type_mouvement="Entrée",
            montant=doc.montant,
            type_transaction="Paiement locataire",
            reference_doctype=doc.doctype,
            reference_docname=doc.name,
            description=f"Paiement locataire {doc.name}"
        )

def on_paiement_proprietaire_update(doc, method):
    """Créer mouvement de sortie quand paiement envoyé"""
    if doc.status == "Envoyé" and not has_mouvement_caisse(doc.doctype, doc.name):
        # Vérifier le solde suffisant
        if not validate_solde_suffisant(doc.montant):
            frappe.throw("Solde insuffisant en caisse")
        
        create_mouvement_caisse(
            type_mouvement="Sortie",
            montant=doc.montant,
            type_transaction="Paiement propriétaire",
            reference_doctype=doc.doctype,
            reference_docname=doc.name,
            description=f"Paiement propriétaire {doc.name}"
        )
```

## Permissions et sécurité

### Rôles
- **Gestionnaire Caisse**: Accès complet à tous les DocTypes
- **Comptable**: Lecture/écriture sur mouvements et apports/retraits
- **Utilisateur Immo**: Lecture seule sur solde et mouvements

### Permissions spéciales
- Seuls les gestionnaires peuvent créer/modifier des caisses
- Les apports/retraits nécessitent une validation
- Les mouvements automatiques ne peuvent pas être modifiés manuellement

## Installation et configuration

### 1. Création des DocTypes
```bash
# Les nouveaux DocTypes sont créés automatiquement
bench migrate
```

### 2. Configuration initiale
```python
# La caisse principale sera créée automatiquement (singleton)
# Configurer la caisse principale
caisse = frappe.get_single("Caisse")
caisse.nom_caisse = "Caisse Principale"
caisse.solde_actuel = 0
caisse.devise = "EUR"
caisse.statut = "Actif"
caisse.save()

# Créer un apport initial si nécessaire
apport = frappe.new_doc("Apport Caisse")
apport.montant = 10000  # Montant initial
apport.methode_apport = "Virement bancaire"
apport.motif = "Apport initial"
apport.statut = "Confirmé"
apport.insert()
```

### 3. Configuration des hooks
```python
# Ajouter les hooks dans hooks.py
# Redémarrer le serveur
bench restart
```

## Utilisation

### Exemple de workflow complet

1. **Initialiser la caisse**:
```python
# Accéder à la caisse singleton
caisse = frappe.get_single("Caisse")
print(f"Solde actuel: {caisse.solde_actuel} EUR")
```

2. **Paiement locataire** (automatique):
```python
# Le paiement locataire confirmé crée automatiquement un mouvement d'entrée
paiement = frappe.get_doc("Paiement Locataire", "PL-2024-00001")
paiement.statut = "Confirmé"
paiement.save()
# → Mouvement d'entrée créé automatiquement
```

3. **Paiement propriétaire** (automatique avec validation):
```python
# Le paiement propriétaire vérifie le solde avant création du mouvement
paiement = frappe.get_doc("Paiement Proprietaire", "PP-2024-00001")
paiement.status = "Envoyé"
paiement.save()
# → Vérification du solde puis mouvement de sortie
```

4. **Apport manuel**:
```python
apport = frappe.new_doc("Apport Caisse")
apport.montant = 5000
apport.methode_apport = "Virement bancaire"
apport.motif = "Apport de trésorerie"
apport.statut = "Confirmé"
apport.insert()
# → Mouvement d'entrée créé automatiquement
```

5. **Consulter l'historique**:
```python
mouvements = get_historique_mouvements(
    date_debut="2024-01-01",
    date_fin="2024-12-31",
    type_mouvement="Entrée"
)
```

## Avantages

- **Centralisation**: Tous les mouvements financiers en un seul endroit
- **Automatisation**: Création automatique des mouvements lors des transactions
- **Traçabilité**: Historique complet avec références aux documents sources
- **Contrôle**: Validation du solde avant les sorties
- **Reporting**: Tableaux de bord et rapports en temps réel
- **Sécurité**: Permissions granulaires et validation des opérations
- **Flexibilité**: Gestion des apports/retraits manuels
- **Intégration**: Compatible avec tous les DocTypes financiers existants

## Métriques et KPI

### Dashboard principal
- Solde actuel avec indicateur visuel
- Évolution du solde sur 30 jours
- Total des entrées/sorties du mois
- Nombre de mouvements par type
- Alertes de solde faible

### Rapports disponibles
- Bilan de trésorerie mensuel/annuel
- Analyse des flux de trésorerie
- Répartition des mouvements par type
- Prévisions de trésorerie
- Réconciliation des soldes

## Support et maintenance

### Logs et debugging
- Tous les mouvements sont tracés dans les logs Frappe
- Fonction de réconciliation en cas d'incohérence
- Outils de diagnostic des soldes

### Sauvegarde et restauration
- Les données de caisse sont incluses dans les sauvegardes standard
- Procédures de restauration des soldes
- Archivage des anciens mouvements

Pour toute question ou problème, consulter les logs système ou contacter l'équipe de développement.