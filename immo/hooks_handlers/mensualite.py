# Copyright (c) 2024, Frappe Technologies and Contributors
# See license.txt

import frappe
from frappe.utils import nowdate, getdate, add_months


def validate(doc, method):
	"""Validation des données avant sauvegarde"""
	# Calcul automatique de la marge
	calculate_margin(doc)
	
	# Validation des montants
	validate_amounts(doc)
	
	# Validation du format mois/année
	validate_month_year_format(doc)
	
	# Validation de l'unicité
	validate_uniqueness(doc)


def on_update(doc, method):
	"""Actions après mise à jour"""
	# Met à jour les statistiques de la location
	update_location_statistics(doc)
	
	# Génère automatiquement la mensualité suivante si nécessaire
	if doc.statut_paiement_locataire == "Payé" and doc.statut_paiement_proprietaire == "Payé":
		generate_next_mensualite(doc)
	
	# Met à jour les marges réelles de la location
	update_location_real_margins(doc)


def on_cancel(doc, method):
	"""Actions lors de l'annulation"""
	# Annule les paiements associés
	cancel_related_payments(doc)
	
	# Met à jour les statistiques de la location
	update_location_statistics(doc)


def calculate_margin(doc):
	"""Calcule la marge mensuelle"""
	if doc.montant_loyer_locataire and doc.montant_loyer_proprietaire:
		doc.marge_mensuelle = doc.montant_loyer_locataire - doc.montant_loyer_proprietaire
		
		# Calcule aussi la marge nette après charges si applicable
		if hasattr(doc, 'charges_locataire') and doc.charges_locataire:
			doc.marge_nette = doc.marge_mensuelle - doc.charges_locataire
		else:
			doc.marge_nette = doc.marge_mensuelle


def validate_amounts(doc):
	"""Valide les montants"""
	if doc.montant_loyer_locataire and doc.montant_loyer_locataire <= 0:
		frappe.throw("Le montant du loyer locataire doit être positif")
	
	if doc.montant_loyer_proprietaire and doc.montant_loyer_proprietaire <= 0:
		frappe.throw("Le montant du loyer propriétaire doit être positif")
	
	if (doc.montant_loyer_locataire and doc.montant_loyer_proprietaire and 
		doc.montant_loyer_locataire < doc.montant_loyer_proprietaire):
		frappe.throw("Le loyer locataire ne peut pas être inférieur au loyer propriétaire")


def validate_month_year_format(doc):
	"""Valide et normalise le format mois/année"""
	if doc.mois_annee:
		try:
			# Vérifie le format MM/YYYY
			parts = doc.mois_annee.split('/')
			if len(parts) != 2:
				raise ValueError("Format invalide")
			
			mois = int(parts[0])
			annee = int(parts[1])
			
			if mois < 1 or mois > 12:
				raise ValueError("Mois invalide")
			
			if annee < 2020 or annee > 2050:
				raise ValueError("Année invalide")
			
			# Normalise le format (ajoute un 0 devant le mois si nécessaire)
			doc.mois_annee = f"{mois:02d}/{annee}"
			
		except (ValueError, IndexError):
			frappe.throw(
				"Format de mois/année invalide. Utilisez le format MM/YYYY (ex: 01/2024)",
				title="Format invalide"
			)


def validate_uniqueness(doc):
	"""Valide l'unicité de la mensualité pour une location et un mois donné"""
	if doc.location_longue_duree_id and doc.mois_annee:
		existing = frappe.db.exists("Mensualite", {
			"location_longue_duree_id": doc.location_longue_duree_id,
			"mois_annee": doc.mois_annee,
			"name": ["!=", doc.name or ""]
		})
		
		if existing:
			frappe.throw(
				f"Une mensualité existe déjà pour {doc.mois_annee} sur cette location",
				title="Mensualité en double"
			)


def update_location_statistics(doc):
	"""Met à jour les statistiques de la location"""
	if not doc.location_longue_duree_id:
		return
	
	# Calcule les statistiques globales de la location
	stats = frappe.db.sql("""
		SELECT 
			COUNT(*) as total_mensualites,
			SUM(CASE WHEN statut_paiement_locataire = 'Payé' THEN 1 ELSE 0 END) as paiements_locataire,
			SUM(CASE WHEN statut_paiement_proprietaire = 'Payé' THEN 1 ELSE 0 END) as paiements_proprietaire,
			SUM(marge_mensuelle) as marge_totale_realisee,
			AVG(marge_mensuelle) as marge_moyenne,
			SUM(montant_loyer_locataire) as total_encaisse,
			SUM(montant_loyer_proprietaire) as total_verse
		FROM `tabMensualite`
		WHERE location_longue_duree_id = %s
	""", (doc.location_longue_duree_id,), as_dict=True)
	
	if stats:
		stat = stats[0]
		# Met à jour la location avec les nouvelles statistiques
		frappe.db.set_value("Location Longue Durée", doc.location_longue_duree_id, {
			"marge_totale_realisee": stat.marge_totale_realisee or 0,
			"total_encaisse": stat.total_encaisse or 0,
			"total_verse_proprietaire": stat.total_verse or 0,
			"taux_paiement_locataire": (stat.paiements_locataire / stat.total_mensualites * 100) if stat.total_mensualites > 0 else 0,
			"taux_paiement_proprietaire": (stat.paiements_proprietaire / stat.total_mensualites * 100) if stat.total_mensualites > 0 else 0
		})


def generate_next_mensualite(doc):
	"""Génère automatiquement la mensualité suivante"""
	if not doc.location_longue_duree_id or not doc.mois_annee:
		return
	
	# Récupère les informations de la location
	location = frappe.get_doc("Location Longue Durée", doc.location_longue_duree_id)
	
	# Vérifie si la location est encore active
	if location.statut != "Actif":
		return
	
	# Calcule le mois suivant
	try:
		mois, annee = map(int, doc.mois_annee.split('/'))
		next_date = getdate(f"{annee}-{mois:02d}-01")
		next_date = add_months(next_date, 1)
		next_mois_annee = f"{next_date.month:02d}/{next_date.year}"
		
		# Vérifie si on n'a pas dépassé la date de fin de location
		if location.date_fin and next_date > getdate(location.date_fin):
			return
		
		# Vérifie si la mensualité suivante n'existe pas déjà
		existing = frappe.db.exists("Mensualite", {
			"location_longue_duree_id": doc.location_longue_duree_id,
			"mois_annee": next_mois_annee
		})
		
		if not existing:
			# Crée la mensualité suivante
			next_mensualite = frappe.get_doc({
				"doctype": "Mensualite",
				"location_longue_duree_id": doc.location_longue_duree_id,
				"mois_annee": next_mois_annee,
				"date_echeance": next_date,
				"montant_loyer_locataire": location.loyer_mensuel_locataire,
				"montant_loyer_proprietaire": location.loyer_mensuel_proprietaire,
				"statut_paiement_locataire": "En attente",
				"statut_paiement_proprietaire": "En attente"
			})
			next_mensualite.insert(ignore_permissions=True)
			
	except (ValueError, IndexError):
		# Erreur de format de date, on ignore
		pass


def update_location_real_margins(doc):
	"""Met à jour les marges réelles de la location"""
	if not doc.location_longue_duree_id:
		return
	
	# Calcule la marge réelle moyenne basée sur les mensualités payées
	real_margin_stats = frappe.db.sql("""
		SELECT 
			AVG(marge_mensuelle) as marge_reelle_moyenne,
			SUM(marge_mensuelle) as marge_reelle_totale
		FROM `tabMensualite`
		WHERE location_longue_duree_id = %s
			AND statut_paiement_locataire = 'Payé'
			AND statut_paiement_proprietaire = 'Payé'
	""", (doc.location_longue_duree_id,), as_dict=True)
	
	if real_margin_stats and real_margin_stats[0].marge_reelle_moyenne:
		frappe.db.set_value("Location Longue Durée", doc.location_longue_duree_id, {
			"marge_reelle_moyenne": real_margin_stats[0].marge_reelle_moyenne,
			"marge_reelle_totale": real_margin_stats[0].marge_reelle_totale or 0
		})


def cancel_related_payments(doc):
	"""Annule les paiements associés à cette mensualité"""
	# Annule les paiements locataire
	locataire_payments = frappe.get_all("Paiement Locataire", {
		"mensualite_id": doc.name
	})
	
	for payment in locataire_payments:
		pay_doc = frappe.get_doc("Paiement Locataire", payment.name)
		pay_doc.cancel()
	
	# Annule les paiements propriétaire
	proprietaire_payments = frappe.get_all("Paiement Propriétaire", {
		"mensualite_id": doc.name
	})
	
	for payment in proprietaire_payments:
		pay_doc = frappe.get_doc("Paiement Propriétaire", payment.name)
		if pay_doc.docstatus != 2:
			pay_doc.cancel()


def calculate_charges_impact(doc):
	"""Calcule l'impact des charges sur la marge"""
	if not doc.location_longue_duree_id:
		return
	
	# Récupère les charges validées pour cette mensualité
	charges = frappe.db.sql("""
		SELECT 
			SUM(montant_locataire) as total_charges_locataire,
			SUM(montant_proprietaire) as total_charges_proprietaire
		FROM `tabCharge`
		WHERE appartement_id = (
			SELECT appartement_id 
			FROM `tabLocation Longue Durée` 
			WHERE name = %s
		)
		AND statut = 'Validée'
		AND MONTH(date_charge) = %s
		AND YEAR(date_charge) = %s

	""", (doc.location_longue_duree_id, 
		  int(doc.mois_annee.split('/')[0]), 
		  int(doc.mois_annee.split('/')[1])), as_dict=True)
	
	if charges and charges[0]:
		charge_data = charges[0]
		doc.charges_locataire = charge_data.total_charges_locataire or 0
		doc.charges_proprietaire = charge_data.total_charges_proprietaire or 0
		
		# Recalcule la marge nette
		if doc.marge_mensuelle:
			doc.marge_nette = doc.marge_mensuelle - doc.charges_locataire + doc.charges_proprietaire


def send_payment_reminders(doc):
	"""Envoie des rappels de paiement si nécessaire"""
	if not doc.date_echeance:
		return
	
	today = getdate(nowdate())
	echeance = getdate(doc.date_echeance)
	
	# Rappel si l'échéance est dépassée et le paiement locataire n'est pas fait
	if today > echeance and doc.statut_paiement_locataire == "En attente":
		# Logique d'envoi de rappel (à implémenter selon les besoins)
		pass
	
	# Rappel pour le paiement propriétaire si le locataire a payé
	if doc.statut_paiement_locataire == "Payé" and doc.statut_paiement_proprietaire == "En attente":
		# Logique d'envoi de notification au propriétaire (à implémenter)
		pass