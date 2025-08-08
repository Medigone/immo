# Guide d'utilisation - Paiements Bloc

## Vue d'ensemble

Ce guide explique comment créer et gérer des paiements bloc depuis l'interface de Location Bloc dans l'application Immo.

## Création d'un paiement bloc

### Méthode 1 : Depuis l'interface Location Bloc

1. **Ouvrir une Location Bloc**
   - Naviguer vers la liste des Locations Bloc
   - Ouvrir une location bloc existante avec le statut "Confirmé" ou "Actif"

2. **Utiliser le bouton d'action**
   - Dans l'interface de la Location Bloc, cliquer sur le menu "Actions"
   - Sélectionner "Créer Paiement Bloc"
   - Confirmer l'action dans la boîte de dialogue

3. **Vérification automatique**
   - Le système vérifie automatiquement que la location bloc est dans un état valide
   - Un nouveau paiement bloc est créé avec les informations pré-remplies
   - Redirection automatique vers le nouveau paiement bloc

### Méthode 2 : Création manuelle

1. **Nouveau document**
   - Aller dans la liste "Paiement Bloc"
   - Cliquer sur "Nouveau"
   - Remplir manuellement tous les champs requis

## Champs automatiquement remplis

Lors de la création depuis Location Bloc, les champs suivants sont automatiquement remplis :

- **Location Bloc** : Référence vers la location bloc source
- **Propriétaire** : Copié depuis la location bloc
- **Appartement** : Copié depuis la location bloc
- **Type de paiement** : Copié depuis la location bloc (ou "Unique" par défaut)
- **Montant du paiement** : Égal au montant total propriétaire de la location bloc
- **Date de paiement** : Date du jour
- **Statut** : "En attente" par défaut

## Gestion des paiements

### Statuts disponibles

- **En attente** : Paiement créé mais pas encore effectué
- **Payé** : Paiement confirmé et effectué
- **Rejeté** : Paiement refusé ou échoué
- **Annulé** : Paiement annulé

### Types de paiement

- **Avance** : Paiement anticipé
- **Acompte** : Paiement partiel
- **Solde** : Paiement final
- **Unique** : Paiement en une seule fois

### Méthodes de paiement

- Virement bancaire
- Chèque
- Espèces
- Carte bancaire
- PayPal
- Autre

## Fonctionnalités avancées

### Bouton "Voir Paiements"

- Disponible dans l'interface Location Bloc
- Affiche tous les paiements liés à cette location bloc
- Filtre automatique sur la liste des paiements

### Validation automatique

- Vérification du statut de la location bloc avant création
- Seules les locations "Confirmé" ou "Actif" peuvent générer des paiements
- Messages d'erreur explicites en cas de problème

### Interface utilisateur

- Boutons contextuels selon l'état du document
- Messages de confirmation pour les actions importantes
- Indicateurs visuels pour le statut des opérations
- Redirection automatique après création

## Workflow recommandé

1. **Créer une Location Bloc**
   - Définir les dates et conditions
   - Confirmer la location bloc

2. **Générer le paiement**
   - Utiliser le bouton "Créer Paiement Bloc"
   - Vérifier les informations pré-remplies
   - Ajuster si nécessaire (méthode, référence, notes)

3. **Traiter le paiement**
   - Mettre à jour le statut selon l'avancement
   - Ajouter les références de paiement
   - Documenter dans les notes si nécessaire

4. **Suivi et reporting**
   - Utiliser "Voir Paiements" pour le suivi
   - Consulter les métriques de la location bloc
   - Générer des rapports si nécessaire

## Bonnes pratiques

- **Toujours confirmer** la location bloc avant de créer des paiements
- **Documenter** les références de paiement pour la traçabilité
- **Mettre à jour** les statuts en temps réel
- **Utiliser les notes** pour des informations complémentaires
- **Vérifier** la cohérence entre location bloc et paiements

## Dépannage

### Erreurs courantes

- **"La location bloc doit être confirmée"** : Changer le statut de la location bloc
- **Bouton non visible** : Vérifier que le document est sauvegardé et a un statut valide
- **Redirection échouée** : Vérifier les permissions sur le DocType Paiement Bloc

### Support

Pour toute question ou problème, consulter :
- La documentation technique dans `/docs/`
- Les logs système en cas d'erreur
- L'administrateur système pour les questions de permissions