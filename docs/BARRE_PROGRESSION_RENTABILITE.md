# Barre de Progression de Rentabilité - Location Bloc

## Vue d'ensemble

Une barre de progression visuelle a été ajoutée au formulaire `Location Bloc` pour afficher de manière intuitive la rentabilité de l'opération immobilière.

## Fonctionnalités

### Affichage Visuel
- **Barre de progression colorée** : Reflète le pourcentage de rentabilité
- **Indicateur numérique** : Affiche le pourcentage exact
- **Échelle de couleurs** : Code couleur selon le niveau de performance

### Code Couleur de Rentabilité

| Rentabilité | Couleur | Signification |
|-------------|---------|---------------|
| ≥ 20% | 🟢 Vert | Excellente rentabilité |
| 15-19% | 🔵 Bleu | Très bonne rentabilité |
| 10-14% | 🟡 Jaune | Bonne rentabilité |
| 5-9% | 🟠 Orange | Rentabilité modérée |
| < 5% | 🔴 Rouge | Faible rentabilité |

## Calcul de la Rentabilité

La rentabilité est calculée automatiquement selon la formule :

```
Rentabilité (%) = (Marge Totale / Montant Total Propriétaire) × 100
```

Où :
- **Marge Totale** = Total Encaissé - Montant Total Propriétaire
- **Total Encaissé** = Somme des montants des sous-locations confirmées/terminées
- **Montant Total Propriétaire** = Coût d'acquisition du bloc

## Mise à Jour Automatique

La barre de progression se met à jour automatiquement :
- Lors du rafraîchissement du formulaire
- Quand de nouvelles sous-locations sont créées
- Lors de la modification des montants

## Emplacement

La barre de progression apparaît dans le **dashboard** du formulaire `Location Bloc`, juste après les indicateurs de statut de paiement.

## Exemple d'Utilisation

### Scénario
- Montant payé au propriétaire : 10 000 €
- Total encaissé via sous-locations : 12 500 €
- Marge totale : 2 500 €
- **Rentabilité : 25%** → Barre verte (excellente rentabilité)

### Affichage
```
📈 Rentabilité de l'opération                    25.0%
████████████████████████████████████████████████████
[                    25.0%                         ]
Faible                                      Excellente
```

## Avantages

1. **Visualisation immédiate** de la performance
2. **Aide à la prise de décision** pour de futures opérations
3. **Suivi en temps réel** de la rentabilité
4. **Interface intuitive** avec code couleur
5. **Motivation** pour optimiser les revenus

## Notes Techniques

- La barre est limitée à 100% de largeur même si la rentabilité dépasse 100%
- Les pourcentages négatifs affichent une barre rouge vide
- L'animation de transition rend l'affichage plus fluide
- Compatible avec tous les navigateurs modernes