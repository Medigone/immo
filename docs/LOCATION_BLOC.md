# Fonctionnalité Location Bloc

## Vue d'ensemble

La fonctionnalité **Location Bloc** permet de gérer des paiements d'avance aux propriétaires d'appartements pour une période donnée, puis de re-louer l'appartement à plusieurs locataires sur une base journalière.

## Architecture

### Nouveaux DocTypes

#### 1. Location Bloc
- **Description**: Gère la réservation d'un appartement pour une période avec paiement d'avance au propriétaire
- **Champs principaux**:
  - `appartement_id`: Lien vers l'appartement
  - `proprietaire_id`: Lien vers le propriétaire
  - `date_debut_bloc` / `date_fin_bloc`: Période de la location bloc
  - `montant_total_proprietaire`: Montant total à payer au propriétaire
  - `type_paiement`: Unique ou Échelonné
  - `statut`: En attente, Confirmé, Actif, Terminé, Annulé

#### 2. Paiement Bloc
- **Description**: Gère les paiements effectués au propriétaire dans le cadre d'une location bloc
- **Champs principaux**:
  - `location_bloc_id`: Lien vers la location bloc
  - `montant_paiement`: Montant du paiement
  - `date_paiement`: Date du paiement
  - `statut`: En attente, Payé, Annulé
  - `methode_paiement`: Virement, Chèque, Espèces, etc.

### Modifications existantes

#### Location Courte Duree
- **Nouveaux champs**:
  - `type_location`: Directe ou Sous-location
  - `location_bloc_id`: Lien vers la location bloc (si sous-location)
  - `marge_sur_bloc`: Marge réalisée sur la location bloc
  - `quote_part_bloc`: Quote-part de la location bloc

## Workflow

### 1. Création d'une Location Bloc
1. Sélectionner un appartement et une période
2. Définir le montant total à payer au propriétaire
3. Choisir le type de paiement (unique ou échelonné)
4. Valider la disponibilité de l'appartement

### 2. Gestion des Paiements
1. Créer un ou plusieurs paiements bloc
2. Marquer les paiements comme payés
3. Suivre l'échéancier de paiement

### 3. Sous-locations
1. Créer des locations courte durée en mode "Sous-location"
2. Lier à la location bloc correspondante
3. Calcul automatique des marges et quotes-parts

## Fonctionnalités clés

### Validations automatiques
- Vérification de la disponibilité de l'appartement
- Validation des dates (pas de chevauchement)
- Contrôle des montants de paiement
- Cohérence entre location bloc et sous-locations

### Calculs automatiques
- Nombre de nuits total
- Prix propriétaire par nuit
- Métriques de performance (taux d'occupation, rentabilité)
- Marges sur les sous-locations

### Dashboard et reporting
- Vue d'ensemble des locations bloc
- Calendrier d'occupation
- Suivi des paiements
- Métriques de performance

## API disponibles

### Location Bloc
- `get_bloc_dashboard_data(location_bloc_id)`: Données du dashboard
- `create_paiement_bloc(...)`: Création d'un paiement
- `get_available_periods(appartement_id)`: Périodes disponibles
- `get_bloc_performance_metrics(...)`: Métriques de performance

### Paiement Bloc
- `validate_paiement_amount(...)`: Validation du montant
- `get_paiement_schedule(location_bloc_id)`: Échéancier de paiement
- `mark_paiement_as_paid(paiement_id)`: Marquer comme payé
- `get_paiement_statistics(...)`: Statistiques des paiements

## Installation

1. Les nouveaux DocTypes sont automatiquement créés lors de l'installation
2. Exécuter la migration pour ajouter les champs personnalisés:
   ```bash
   bench migrate
   ```

## Utilisation

### Exemple de workflow complet

1. **Créer une location bloc**:
   ```python
   location_bloc = frappe.new_doc("Location Bloc")
   location_bloc.appartement_id = "APP-001"
   location_bloc.date_debut_bloc = "2024-07-01"
   location_bloc.date_fin_bloc = "2024-08-31"
   location_bloc.montant_total_proprietaire = 3000
   location_bloc.type_paiement = "Échelonné"
   location_bloc.insert()
   ```

2. **Créer un paiement**:
   ```python
   paiement = frappe.new_doc("Paiement Bloc")
   paiement.location_bloc_id = location_bloc.name
   paiement.montant_paiement = 1500
   paiement.date_paiement = "2024-06-15"
   paiement.insert()
   ```

3. **Créer une sous-location**:
   ```python
   sous_location = frappe.new_doc("Location Courte Duree")
   sous_location.type_location = "Sous-location"
   sous_location.location_bloc_id = location_bloc.name
   sous_location.date_debut = "2024-07-15"
   sous_location.date_fin = "2024-07-20"
   sous_location.insert()
   ```

## Avantages

- **Flexibilité**: Gestion des paiements d'avance et re-location
- **Automatisation**: Calculs automatiques des marges et métriques
- **Traçabilité**: Suivi complet des paiements et occupations
- **Intégration**: Compatible avec le système existant
- **Performance**: Métriques détaillées pour l'analyse

## Support

Pour toute question ou problème, consulter les logs Frappe ou contacter l'équipe de développement.