# 🏢 Rental Manager App (Frappe + Vue.js)

## 🎯 Objectif
Créer une application de gestion d’appartements en location avec Frappe comme backend et Vue.js comme frontend. L’app permet de gérer les propriétaires, appartements, réservations, charges de maintenance, marges, et paiements aux propriétaires.

---

## 📦 Structure de l’application

### Doctypes à créer

#### 1. Owner
- `name` (Auto)
- `user` (Link → User)
- `default_price_per_night` (Currency)
- `payout_method` (Data)

#### 2. Apartment
- `name` (Auto)
- `owner` (Link → Owner)
- `address` (Data)
- `description` (Small Text)
- `custom_price` (Currency)
- `is_available` (Check)

#### 3. Booking
- `apartment` (Link → Apartment)
- `guest` (Link → User)
- `start_date` (Date)
- `end_date` (Date)
- `status` (Select: Pending, Confirmed, Cancelled)
- `price_to_owner` (Currency)
- `my_price` (Currency)
- `margin` (Currency, Calculé : `my_price - price_to_owner`)
- `total_nights` (Int, Calculé)

#### 4. Maintenance Charge
- `apartment` (Link → Apartment)
- `date` (Date)
- `description` (Data)
- `amount` (Currency)
- `is_paid` (Check)

#### 5. Pricing Rule
- `apartment` (Link → Apartment)
- `from_date` (Date)
- `to_date` (Date)
- `custom_price` (Currency)

#### 6. Owner Payout
- `owner` (Link → Owner)
- `booking` (Link → Booking)
- `amount_due` (Currency)
- `status` (Select: Pending, Paid)
- `payout_date` (Date)

---

## 🧠 Logique Backend

### Booking.validate()
- Calcul automatique :
  - `total_nights`
  - `price_to_owner` (basé sur `Owner.default_price_per_night` ou `Pricing Rule`)
  - `my_price` (markup dynamique)
  - `margin`

### Hooks
- Empêche les chevauchements de réservations pour un même appartement.

### Après création de réservation confirmée :
- Crée automatiquement un `Owner Payout` avec le bon montant.

---

## 🔐 Permissions

- **Propriétaire** : peut voir ses appartements et paiements uniquement.
- **Invité (User)** : peut créer des réservations.

---

## 🌐 API REST à exposer

Dans `rental_manager/api` :

- `get_available_apartments(from_date, to_date)`
- `make_booking(apartment_id, user_id, start_date, end_date)`
- `get_user_bookings(user_id)`
- `get_owner_apartments(owner_id)`
- `get_payouts(owner_id)`

> ⚠️ Utiliser `frappe.whitelist()` + sécurisation avec `frappe.session.user`.

---

## 🖼️ Frontend Vue.js

### Structure suggérée

```
src/
├── components/
│   ├── ApartmentList.vue
│   ├── BookingForm.vue
│   ├── Calendar.vue
│   └── OwnerDashboard.vue
├── pages/
│   ├── Home.vue
│   ├── Login.vue
│   ├── OwnerPanel.vue
│   └── BookingHistory.vue
├── services/
│   └── api.js
├── store/
│   └── user.js
└── App.vue
```

- Auth via `/api/method/login`
- Session `sid` stockée dans cookie ou localStorage
- Utiliser `axios` pour les appels API

---

## 🧩 Bonnes pratiques Frappe

- Validation métier dans `validate()`
- `frappe.get_all`, `frappe.db.get_value`, `frappe.new_doc()` pour accès DB
- Organisation modulaire : `api/`, `utils/`, `services/`
- Fixtures pour les rôles et permissions
- Ajout de tests (unitaires et API)

## Regles

- voici le site pour la migration et le build: imo.intrapro.net
- Le serveur est configuré en production et servi sur le port 80 a l'adresse : https://imo.intrapro.net