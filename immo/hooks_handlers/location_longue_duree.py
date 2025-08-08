# Copyright (c) 2024, Frappe Technologies and Contributors
# See license.txt

import frappe
from frappe.utils import nowdate, add_months, getdate


def validate(doc, method):
	"""Validation des données avant sauvegarde"""
	# Vérification des chevauchements de dates
	check_date_overlap(doc)
	
	# Calcul automatique des marges
	calculate_margins(doc)
	
	# Validation des montants
	validate_amounts(doc)


def on_update(doc, method):
	"""Actions après mise à jour"""
	# Génère les mensualités automatiquement si nécessaire
	if doc.statut == "Actif" and not has_existing_mensualites(doc):
		generate_monthly_payments(doc)
	
	# Met à jour le statut de l'appartement
	update_apartment_status(doc)
	
	# Recalcule les marges si les montants ont changé
	if doc.has_value_changed("loyer_mensuel_locataire") or doc.has_value_changed("loyer_mensuel_proprietaire"):
		update_existing_mensualites_margins(doc)


def on_cancel(doc, method):
	"""Actions lors de l'annulation"""
	# Annule toutes les mensualités associées
	cancel_related_mensualites(doc)
	
	# Remet l'appartement en statut disponible
	reset_apartment_status(doc)


def check_date_overlap(doc):
	"""Vérifie les chevauchements de dates pour le même appartement"""
	if not doc.date_debut or not doc.date_fin:
		return
	
	# Recherche les locations existantes qui se chevauchent
	overlapping_locations = frappe.db.sql("""
		SELECT name, date_debut, date_fin, locataire_nom
		FROM `tabLocation Longue Durée`
		WHERE appartement_id = %s
			AND name != %s
			AND statut IN ('Actif', 'Confirmé')
			AND (
				(date_debut <= %s AND date_fin >= %s)
				OR (date_debut <= %s AND date_fin >= %s)
				OR (date_debut >= %s AND date_fin <= %s)
			)
	""", (doc.appartement_id, doc.name or '', doc.date_debut, doc.date_debut,
		  doc.date_fin, doc.date_fin, doc.date_debut, doc.date_fin), as_dict=True)
	
	if overlapping_locations:
		overlap_details = []
		for loc in overlapping_locations:
			overlap_details.append(f"{loc.locataire_nom} ({loc.date_debut} - {loc.date_fin})")
		
		frappe.throw(
			f"Conflit de dates détecté. Les périodes se chevauchent avec les locations existantes: {', '.join(overlap_details)}",
			title="Chevauchement de dates"
		)


def calculate_margins(doc):
	"""Calcule les marges automatiquement"""
	if doc.loyer_mensuel_locataire and doc.loyer_mensuel_proprietaire:
		# Marge mensuelle = différence entre loyer locataire et propriétaire
		doc.marge_mensuelle = doc.loyer_mensuel_locataire - doc.loyer_mensuel_proprietaire
		
		# Marge initiale = généralement égale à la marge mensuelle
		doc.marge_initiale = doc.marge_mensuelle
		
		# Calcul de la marge totale sur la période si les dates sont définies
		if doc.date_debut and doc.date_fin:
			months_count = get_months_between_dates(doc.date_debut, doc.date_fin)
			doc.marge_totale_prevue = doc.marge_mensuelle * months_count


def validate_amounts(doc):
	"""Valide les montants"""
	if doc.loyer_mensuel_locataire and doc.loyer_mensuel_locataire <= 0:
		frappe.throw("Le loyer mensuel locataire doit être positif")
	
	if doc.loyer_mensuel_proprietaire and doc.loyer_mensuel_proprietaire <= 0:
		frappe.throw("Le loyer mensuel propriétaire doit être positif")
	
	if (doc.loyer_mensuel_locataire and doc.loyer_mensuel_proprietaire and 
		doc.loyer_mensuel_locataire < doc.loyer_mensuel_proprietaire):
		frappe.throw("Le loyer locataire ne peut pas être inférieur au loyer propriétaire")


def has_existing_mensualites(doc):
	"""Vérifie s'il existe déjà des mensualités pour cette location"""
	existing_count = frappe.db.count("Mensualite", {
		"location_longue_duree_id": doc.name
	})
	return existing_count > 0


def generate_monthly_payments(doc):
	"""Génère automatiquement les mensualités pour la période"""
	if not doc.date_debut or not doc.date_fin:
		return
	
	current_date = getdate(doc.date_debut)
	end_date = getdate(doc.date_fin)
	
	while current_date <= end_date:
		# Format mois/année
		mois_annee = current_date.strftime("%m/%Y")
		
		# Vérifie si la mensualité existe déjà
		existing = frappe.db.exists("Mensualite", {
			"location_longue_duree_id": doc.name,
			"mois_annee": mois_annee
		})
		
		if not existing:
			# Calcule la date d'échéance (généralement le 1er du mois)
			date_echeance = current_date.replace(day=1)
			
			# Crée la mensualité
			mensualite = frappe.get_doc({
				"doctype": "Mensualite",
				"location_longue_duree_id": doc.name,
				"mois_annee": mois_annee,
				"date_echeance": date_echeance,
				"montant_loyer_locataire": doc.loyer_mensuel_locataire,
				"montant_loyer_proprietaire": doc.loyer_mensuel_proprietaire,
				"statut_paiement_locataire": "En attente",
				"statut_paiement_proprietaire": "En attente"
			})
			mensualite.insert(ignore_permissions=True)
		
		# Passe au mois suivant
		current_date = add_months(current_date, 1)


def update_apartment_status(doc):
	"""Met à jour le statut de l'appartement"""
	if doc.statut == "Actif":
		# Marque l'appartement comme non disponible
		frappe.db.set_value("Appartement", doc.appartement_id, "disponible", 0)
	elif doc.statut in ["Terminé", "Annulé"]:
		# Vérifie s'il n'y a pas d'autres locations actives
		other_active = frappe.db.exists("Location Longue Durée", {
			"appartement_id": doc.appartement_id,
			"statut": "Actif",
			"name": ["!=", doc.name]
		})
		
		if not other_active:
			frappe.db.set_value("Appartement", doc.appartement_id, "disponible", 1)


def update_existing_mensualites_margins(doc):
	"""Met à jour les marges des mensualités existantes"""
	# Met à jour toutes les mensualités futures
	frappe.db.sql("""
		UPDATE `tabMensualite`
		SET montant_loyer_locataire = %s,
			montant_loyer_proprietaire = %s,
			marge_mensuelle = %s
		WHERE location_longue_duree_id = %s
			AND date_echeance >= %s
			AND statut_paiement_locataire = 'En attente'
	""", (doc.loyer_mensuel_locataire, doc.loyer_mensuel_proprietaire,
		  doc.marge_mensuelle, doc.name, nowdate()))


def cancel_related_mensualites(doc):
	"""Annule toutes les mensualités associées"""
	mensualites = frappe.get_all("Mensualite", {
		"location_longue_duree_id": doc.name
	})
	
	for mensualite in mensualites:
		mens_doc = frappe.get_doc("Mensualite", mensualite.name)
		mens_doc.cancel()


def reset_apartment_status(doc):
	"""Remet l'appartement en statut disponible"""
	# Vérifie s'il n'y a pas d'autres locations actives
	other_active = frappe.db.exists("Location Longue Durée", {
		"appartement_id": doc.appartement_id,
		"statut": "Actif",
		"name": ["!=", doc.name]
	})
	
	if not other_active:
		frappe.db.set_value("Appartement", doc.appartement_id, "disponible", 1)


def get_months_between_dates(start_date, end_date):
	"""Calcule le nombre de mois entre deux dates"""
	start = getdate(start_date)
	end = getdate(end_date)
	
	months = (end.year - start.year) * 12 + (end.month - start.month)
	
	# Ajoute 1 si on inclut le mois de début
	if start.day <= end.day:
		months += 1
	
	return max(months, 1)  # Au minimum 1 mois