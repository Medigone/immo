# Copyright (c) 2024, Frappe Technologies and Contributors
# See license.txt

import frappe
from frappe.utils import nowdate, getdate, date_diff


def validate(doc, method):
	"""Validation des données avant sauvegarde"""
	# Vérification des chevauchements de dates
	check_date_overlap(doc)
	
	# Calcul automatique des marges et montants
	calculate_amounts_and_margins(doc)
	
	# Validation des montants
	validate_amounts(doc)
	
	# Validation des dates
	validate_dates(doc)


def on_update(doc, method):
	"""Actions après mise à jour"""
	# Met à jour le statut de l'appartement
	update_apartment_status(doc)
	
	# Recalcule les commissions si nécessaire
	if doc.statut == "Confirmé":
		update_related_commissions(doc)


def on_cancel(doc, method):
	"""Actions lors de l'annulation"""
	# Annule les commissions associées
	cancel_related_commissions(doc)
	
	# Remet l'appartement en statut disponible
	reset_apartment_status(doc)


def check_date_overlap(doc):
	"""Vérifie les chevauchements de dates pour le même appartement"""
	if not doc.date_debut or not doc.date_fin:
		return
	
	# Recherche les réservations existantes qui se chevauchent
	overlapping_bookings = frappe.db.sql("""
		SELECT name, date_debut, date_fin, locataire_nom
		FROM `tabLocation Courte Durée`
		WHERE appartement_id = %s
			AND name != %s
			AND statut IN ('Confirmé', 'En cours')
			AND (
				(date_debut <= %s AND date_fin >= %s)
				OR (date_debut <= %s AND date_fin >= %s)
				OR (date_debut >= %s AND date_fin <= %s)
			)
	""", (doc.appartement_id, doc.name or '', doc.date_debut, doc.date_debut,
		  doc.date_fin, doc.date_fin, doc.date_debut, doc.date_fin), as_dict=True)
	
	if overlapping_bookings:
		overlap_details = []
		for booking in overlapping_bookings:
			overlap_details.append(f"{booking.locataire_nom} ({booking.date_debut} - {booking.date_fin})")
		
		frappe.throw(
			f"Conflit de dates détecté. Les périodes se chevauchent avec les réservations existantes: {', '.join(overlap_details)}",
			title="Chevauchement de dates"
		)
	
	# Vérifie aussi les conflits avec les locations longue durée
	overlapping_long_term = frappe.db.sql("""
		SELECT name, date_debut, date_fin, locataire_nom
		FROM `tabLocation Longue Durée`
		WHERE appartement_id = %s
			AND statut = 'Actif'
			AND (
				(date_debut <= %s AND date_fin >= %s)
				OR (date_debut <= %s AND date_fin >= %s)
				OR (date_debut >= %s AND date_fin <= %s)
			)
	""", (doc.appartement_id, doc.date_debut, doc.date_debut,
		  doc.date_fin, doc.date_fin, doc.date_debut, doc.date_fin), as_dict=True)
	
	if overlapping_long_term:
		frappe.throw(
			f"Conflit avec une location longue durée active pour cet appartement",
			title="Appartement non disponible"
		)


def calculate_amounts_and_margins(doc):
	"""Calcule automatiquement les montants et marges"""
	if not doc.date_debut or not doc.date_fin or not doc.prix_par_nuit:
		return
	
	# Calcule le nombre de nuits
	nights = date_diff(doc.date_fin, doc.date_debut)
	if nights <= 0:
		frappe.throw("La date de fin doit être postérieure à la date de début")
	
	doc.nombre_nuits = nights
	
	# Calcule le montant total locataire
	doc.montant_total_locataire = doc.prix_par_nuit * nights
	
	# Récupère le prix propriétaire par défaut si pas défini
	if not doc.prix_par_nuit_proprietaire:
		# Récupère le prix par défaut du propriétaire
		appartement = frappe.get_doc("Appartement", doc.appartement_id)
		proprietaire = frappe.get_doc("Proprietaire", appartement.proprietaire_id)
		
		if proprietaire.prix_par_nuit_defaut:
			doc.prix_par_nuit_proprietaire = proprietaire.prix_par_nuit_defaut
		else:
			# Par défaut, 80% du prix locataire
			doc.prix_par_nuit_proprietaire = doc.prix_par_nuit * 0.8
	
	# Calcule le montant total propriétaire
	doc.montant_total_proprietaire = doc.prix_par_nuit_proprietaire * nights
	
	# Calcule la marge
	doc.marge_totale = doc.montant_total_locataire - doc.montant_total_proprietaire
	
	# Calcule la marge par nuit
	if nights > 0:
		doc.marge_par_nuit = doc.marge_totale / nights


def validate_amounts(doc):
	"""Valide les montants"""
	if doc.prix_par_nuit and doc.prix_par_nuit <= 0:
		frappe.throw("Le prix par nuit doit être positif")
	
	if doc.prix_par_nuit_proprietaire and doc.prix_par_nuit_proprietaire <= 0:
		frappe.throw("Le prix par nuit propriétaire doit être positif")
	
	if (doc.prix_par_nuit and doc.prix_par_nuit_proprietaire and 
		doc.prix_par_nuit < doc.prix_par_nuit_proprietaire):
		frappe.throw("Le prix locataire ne peut pas être inférieur au prix propriétaire")


def validate_dates(doc):
	"""Valide les dates"""
	if doc.date_debut and doc.date_fin:
		if getdate(doc.date_debut) >= getdate(doc.date_fin):
			frappe.throw("La date de fin doit être postérieure à la date de début")
	
	# Vérifie que les dates ne sont pas trop dans le passé (sauf pour les statuts terminés)
	if doc.statut not in ["Terminé", "Annulé"] and doc.date_debut:
		if getdate(doc.date_debut) < getdate(nowdate()):
			# Permet les réservations qui commencent aujourd'hui
			if getdate(doc.date_debut) < getdate(nowdate()):
				frappe.msgprint(
					"Attention: La date de début est dans le passé",
					title="Date dans le passé",
					indicator="orange"
				)


def update_apartment_status(doc):
	"""Met à jour le statut de l'appartement"""
	if doc.statut == "Confirmé":
		# Pour les locations courtes, on ne change pas le statut global de l'appartement
		# mais on peut ajouter une logique de disponibilité par période
		pass
	elif doc.statut in ["Terminé", "Annulé"]:
		# Vérifie s'il n'y a pas d'autres réservations actives pour aujourd'hui
		today = nowdate()
		active_bookings = frappe.db.exists("Location Courte Durée", {
			"appartement_id": doc.appartement_id,
			"statut": ["in", ["Confirmé", "En cours"]],
			"date_debut": ["<=", today],
			"date_fin": [">=", today],
			"name": ["!=", doc.name]
		})
		
		# Vérifie aussi les locations longue durée
		long_term_active = frappe.db.exists("Location Longue Durée", {
			"appartement_id": doc.appartement_id,
			"statut": "Actif"
		})
		
		if not active_bookings and not long_term_active:
			frappe.db.set_value("Appartement", doc.appartement_id, "statut", "Disponible")


def update_related_commissions(doc):
	"""Met à jour les commissions associées"""
	# Recherche les commissions liées à cette location
	commissions = frappe.get_all("Commission", {
		"location_courte_duree_id": doc.name
	})
	
	for commission in commissions:
		comm_doc = frappe.get_doc("Commission", commission.name)
		# Recalcule le montant de la commission basé sur la nouvelle marge
		if comm_doc.pourcentage_commission and doc.marge_totale:
			comm_doc.montant_commission = (doc.marge_totale * comm_doc.pourcentage_commission) / 100
			comm_doc.save(ignore_permissions=True)


def cancel_related_commissions(doc):
	"""Annule les commissions associées"""
	commissions = frappe.get_all("Commission", {
		"location_courte_duree_id": doc.name,
		"docstatus": 1
	})
	
	for commission in commissions:
		comm_doc = frappe.get_doc("Commission", commission.name)
		if comm_doc.docstatus == 1:
			comm_doc.cancel()


def reset_apartment_status(doc):
	"""Remet l'appartement en statut disponible si nécessaire"""
	# Vérifie s'il n'y a pas d'autres réservations actives
	today = nowdate()
	active_bookings = frappe.db.exists("Location Courte Durée", {
		"appartement_id": doc.appartement_id,
		"statut": ["in", ["Confirmé", "En cours"]],
		"date_debut": ["<=", today],
		"date_fin": [">=", today],
		"name": ["!=", doc.name]
	})
	
	# Vérifie aussi les locations longue durée
	long_term_active = frappe.db.exists("Location Longue Durée", {
		"appartement_id": doc.appartement_id,
		"statut": "Actif"
	})
	
	if not active_bookings and not long_term_active:
		frappe.db.set_value("Appartement", doc.appartement_id, "statut", "Disponible")


def calculate_dynamic_pricing(doc):
	"""Calcule le prix dynamique basé sur les règles de tarification"""
	# Cette fonction peut être étendue pour implémenter des règles de pricing dynamique
	# basées sur la saison, la demande, les événements locaux, etc.
	
	# Pour l'instant, applique les règles de base
	if not doc.prix_par_nuit and doc.appartement_id:
		# Récupère le prix de base de l'appartement ou du propriétaire
		appartement = frappe.get_doc("Appartement", doc.appartement_id)
		proprietaire = frappe.get_doc("Proprietaire", appartement.proprietaire_id)
		
		base_price = proprietaire.prix_par_nuit_defaut or 50  # Prix par défaut
		
		# Applique des ajustements saisonniers (exemple simple)
		if doc.date_debut:
			start_date = getdate(doc.date_debut)
			# Haute saison (juillet-août)
			if start_date.month in [7, 8]:
				base_price *= 1.3
			# Moyenne saison (mai-juin, septembre)
			elif start_date.month in [5, 6, 9]:
				base_price *= 1.1
		
		doc.prix_par_nuit = base_price