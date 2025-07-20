# 📋 Plan d'exécution - Rental Manager App (immo)

## 🎯 Vue d'ensemble
Application de gestion d'appartements en location avec Frappe (backend) et Vue.js (frontend)
**App existante** : `immo` (déjà créée et configurée)

---

## 📅 Phase 1 : Création des Doctypes

### Tâche 1.1 : Doctype Owner
- [x] Créer le doctype `Owner` avec les champs :
  - `name` (Auto)
  - `full_name` (Data)
  - `payout_method` (Data)
- [x] Ajouter les validations métier
- [x] Créer les fixtures pour les rôles et permissions

### Tâche 1.2 : Doctype Apartment
- [x] Créer le doctype `Apartment` avec les champs :
  - `name` (Auto)
  - `owner` (Link → Owner)
  - `address` (Data)
  - `description` (Small Text)
  - `default_price_per_night` (Currency)
  - `custom_price` (Currency)
  - `is_available` (Check)
- [x] Ajouter les validations métier
- [x] Configurer les permissions

### Tâche 1.3 : Doctype Booking
- [x] Créer le doctype `Booking` avec les champs :
  - `apartment` (Link → Apartment)
  - `guest` (Link → User)
  - `start_date` (Date)
  - `end_date` (Date)
  - `status` (Select: Pending, Confirmed, Cancelled)
  - `price_to_owner` (Currency)
  - `my_price` (Currency)
  - `margin` (Currency, Calculé)
  - `total_nights` (Int, Calculé)
- [x] Implémenter la méthode `validate()` avec calculs automatiques
- [x] Ajouter la logique de prévention des chevauchements

### Tâche 1.4 : Doctype Maintenance Charge
- [x] Créer le doctype `Maintenance Charge`
- [x] Configurer les champs et validations

### Tâche 1.5 : Doctype Pricing Rule
- [x] Créer le doctype `Pricing Rule`
- [x] Implémenter la logique de tarification dynamique

### Tâche 1.6 : Doctype Owner Payout
- [x] Créer le doctype `Owner Payout`
- [x] Configurer la génération automatique après réservation

---

## 📅 Phase 2 : Logique Backend et API

### Tâche 2.1 : Implémentation des hooks
- [ ] Créer les hooks pour la gestion des réservations
- [ ] Implémenter la logique de prévention des chevauchements
- [ ] Configurer la génération automatique des paiements

### Tâche 2.2 : API REST
- [ ] Créer le dossier `immo/api/`
- [ ] Implémenter `get_available_apartments(from_date, to_date)`
- [ ] Implémenter `make_booking(apartment_id, user_id, start_date, end_date)`
- [ ] Implémenter `get_user_bookings(user_id)`
- [ ] Implémenter `get_owner_apartments(owner_id)`
- [ ] Implémenter `get_payouts(owner_id)`
- [ ] Ajouter la sécurisation avec `frappe.whitelist()` et `frappe.session.user`

### Tâche 2.3 : Services et utilitaires
- [ ] Créer le dossier `immo/services/`
- [ ] Implémenter les services de calcul de prix
- [ ] Créer les utilitaires de validation

---

## 📅 Phase 3 : Frontend Vue.js

### Tâche 3.1 : Configuration du projet Vue.js
- [ ] Initialiser le projet Vue.js dans `immo/frontend/`
- [ ] Configurer les dépendances (axios, vue-router, vuex)
- [ ] Configurer le build et le déploiement

### Tâche 3.2 : Services API
- [ ] Créer `src/services/api.js`
- [ ] Implémenter l'authentification via `/api/method/login`
- [ ] Configurer la gestion des sessions avec `sid`
- [ ] Créer les méthodes pour tous les endpoints API

### Tâche 3.3 : Store et gestion d'état
- [ ] Créer `src/store/user.js`
- [ ] Implémenter la gestion de l'état utilisateur
- [ ] Configurer la persistance des données

### Tâche 3.4 : Composants Vue.js
- [ ] Créer `src/components/ApartmentList.vue`
- [ ] Créer `src/components/BookingForm.vue`
- [ ] Créer `src/components/Calendar.vue`
- [ ] Créer `src/components/OwnerDashboard.vue`

### Tâche 3.5 : Pages Vue.js
- [ ] Créer `src/pages/Home.vue`
- [ ] Créer `src/pages/Login.vue`
- [ ] Créer `src/pages/OwnerPanel.vue`
- [ ] Créer `src/pages/BookingHistory.vue`

### Tâche 3.6 : Application principale
- [ ] Créer `src/App.vue`
- [ ] Configurer le routing
- [ ] Implémenter la navigation

---

## 📅 Phase 4 : Tests et validation

### Tâche 4.1 : Tests unitaires
- [ ] Créer les tests pour les doctypes
- [ ] Tester les validations métier
- [ ] Tester les calculs automatiques

### Tâche 4.2 : Tests API
- [ ] Tester tous les endpoints REST
- [ ] Valider la sécurisation
- [ ] Tester les permissions utilisateur

### Tâche 4.3 : Tests frontend
- [ ] Tester les composants Vue.js
- [ ] Valider l'intégration avec l'API
- [ ] Tester l'authentification

---

## 📅 Phase 5 : Déploiement et configuration production

### Tâche 5.1 : Configuration serveur
- [ ] Configurer l'app sur le serveur de production
- [ ] Vérifier les permissions et rôles
- [ ] Tester la connectivité

### Tâche 5.2 : Build et déploiement frontend
- [ ] Configurer le build de production Vue.js
- [ ] Déployer sur le serveur https://imo.intrapro.net
- [ ] Configurer le reverse proxy si nécessaire

### Tâche 5.3 : Tests de production
- [ ] Tester toutes les fonctionnalités en production
- [ ] Valider les performances
- [ ] Vérifier la sécurité

---

## 📅 Phase 6 : Documentation et formation

### Tâche 6.1 : Documentation technique
- [ ] Documenter l'architecture
- [ ] Créer un guide d'installation
- [ ] Documenter les API

### Tâche 6.2 : Documentation utilisateur
- [ ] Créer un guide utilisateur
- [ ] Documenter les workflows
- [ ] Créer des tutoriels vidéo si nécessaire

---

## ⏱️ Estimation du temps

- **Phase 1** : 3-4 jours
- **Phase 2** : 2-3 jours
- **Phase 3** : 4-5 jours
- **Phase 4** : 2-3 jours
- **Phase 5** : 1-2 jours
- **Phase 6** : 1-2 jours

**Total estimé** : 13-19 jours

---

## 🚨 Points d'attention

1. **Sécurité** : Toujours valider les permissions utilisateur
2. **Performance** : Optimiser les requêtes de base de données
3. **UX** : Interface intuitive et responsive
4. **Backup** : Sauvegarder régulièrement les données
5. **Monitoring** : Surveiller les performances en production

---

## ✅ Critères de validation

- [ ] Tous les doctypes créés et fonctionnels
- [ ] API REST sécurisée et testée
- [ ] Frontend Vue.js responsive et intuitif
- [ ] Tests unitaires et d'intégration passants
- [ ] Déploiement en production réussi
- [ ] Documentation complète
- [ ] Formation utilisateur effectuée 