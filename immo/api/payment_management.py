# Copyright (c) 2024, Frappe Technologies and Contributors
# See license.txt

import frappe
from frappe import _
from frappe.utils import nowdate, getdate, add_months, flt
from datetime import datetime, timedelta


@frappe.whitelist()
def create_bulk_tenant_payments(location_longue_duree_id, start_month, end_month, payment_data):
	"""Crée des paiements locataire en lot pour plusieurs mois"""
	try:
		# Vérification de la location
		if not frappe.db.exists("Location Longue Durée", location_longue_duree_id):
			frappe.throw(_("Location longue durée non trouvée"))
		
		location = frappe.get_doc("Location Longue Durée", location_longue_duree_id)
		
		# Validation des dates
		start_date = getdate(start_month + "-01")
		end_date = getdate(end_month + "-01")
		
		if start_date > end_date:
			frappe.throw(_("La date de début doit être antérieure à la date de fin"))
		
		created_payments = []
		current_date = start_date
		
		while current_date <= end_date:
			mois_annee = f"{current_date.month:02d}/{current_date.year}"
			
			# Vérifie si une mensualité existe pour ce mois
			mensualite = frappe.db.get_value("Mensualite", {
				"location_longue_duree_id": location_longue_duree_id,
				"mois_annee": mois_annee
			}, "name")
			
			if not mensualite:
				# Crée la mensualité si elle n'existe pas
				mensualite_doc = frappe.get_doc({
					"doctype": "Mensualite",
					"location_longue_duree_id": location_longue_duree_id,
					"mois_annee": mois_annee,
					"loyer_locataire": location.loyer_locataire,
					"loyer_proprietaire": location.loyer_proprietaire,
					"marge_mensuelle": location.marge_mensuelle
				})
				mensualite_doc.insert()
				mensualite = mensualite_doc.name
			
			# Vérifie si un paiement existe déjà
			existing_payment = frappe.db.exists("Paiement Locataire", {
				"mensualite_id": mensualite,
				"type_paiement": "Loyer mensuel"
			})
			
			if not existing_payment:
				# Crée le paiement locataire
				payment_doc = frappe.get_doc({
					"doctype": "Paiement Locataire",
					"mensualite_id": mensualite,
					"location_longue_duree_id": location_longue_duree_id,
					"type_paiement": "Loyer mensuel",
					"montant": payment_data.get("montant", location.loyer_locataire),
					"montant_net": payment_data.get("montant_net", location.loyer_locataire),
					"date_paiement": payment_data.get("date_paiement", current_date),
					"methode_paiement": payment_data.get("methode_paiement", "Virement bancaire"),
					"statut": payment_data.get("statut", "En attente"),
					"reference_financiere": payment_data.get("reference_financiere", ""),
					"commentaires": payment_data.get("commentaires", f"Paiement automatique pour {mois_annee}")
				})
				payment_doc.insert()
				created_payments.append({
					"mois": mois_annee,
					"paiement_id": payment_doc.name,
					"mensualite_id": mensualite
				})
			
			current_date = add_months(current_date, 1)
		
		return {
			"success": True,
			"location_id": location_longue_duree_id,
			"created_payments": created_payments,
			"total_created": len(created_payments)
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur création paiements en lot: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def schedule_owner_payouts(location_longue_duree_id, start_month, end_month, payout_data):
	"""Programme des versements propriétaire pour plusieurs mois"""
	try:
		# Vérification de la location
		if not frappe.db.exists("Location Longue Durée", location_longue_duree_id):
			frappe.throw(_("Location longue durée non trouvée"))
		
		location = frappe.get_doc("Location Longue Durée", location_longue_duree_id)
		
		# Validation des dates
		start_date = getdate(start_month + "-01")
		end_date = getdate(end_month + "-01")
		
		if start_date > end_date:
			frappe.throw(_("La date de début doit être antérieure à la date de fin"))
		
		scheduled_payouts = []
		current_date = start_date
		
		while current_date <= end_date:
			mois_annee = f"{current_date.month:02d}/{current_date.year}"
			
			# Vérifie si une mensualité existe pour ce mois
			mensualite = frappe.db.get_value("Mensualite", {
				"location_longue_duree_id": location_longue_duree_id,
				"mois_annee": mois_annee
			}, "name")
			
			if mensualite:
				# Vérifie si un versement existe déjà
				existing_payout = frappe.db.exists("Paiement Propriétaire", {
					"mensualite_id": mensualite,
					"type_paiement": "Loyer mensuel"
				})
				
				if not existing_payout:
					# Calcule la date de versement (généralement quelques jours après le paiement locataire)
					payout_date = add_months(current_date, 0)
					if payout_data.get("delay_days"):
						payout_date = payout_date + timedelta(days=int(payout_data.get("delay_days", 0)))
					
					# Crée le versement propriétaire
					payout_doc = frappe.get_doc({
						"doctype": "Paiement Propriétaire",
						"mensualite_id": mensualite,
						"location_longue_duree_id": location_longue_duree_id,
						"type_paiement": "Loyer mensuel",
						"montant": payout_data.get("montant", location.loyer_proprietaire),
						"montant_net": payout_data.get("montant_net", location.loyer_proprietaire),
						"date_paiement": payout_date,
						"methode_paiement": payout_data.get("methode_paiement", "Virement bancaire"),
						"statut": "En attente",
						"commentaires": payout_data.get("commentaires", f"Versement programmé pour {mois_annee}")
					})
					payout_doc.insert()
					scheduled_payouts.append({
						"mois": mois_annee,
						"payout_id": payout_doc.name,
						"mensualite_id": mensualite,
						"date_prevue": payout_date
					})
			
			current_date = add_months(current_date, 1)
		
		return {
			"success": True,
			"location_id": location_longue_duree_id,
			"scheduled_payouts": scheduled_payouts,
			"total_scheduled": len(scheduled_payouts)
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur programmation versements: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_payment_status_summary(location_id=None, appartement_id=None, proprietaire_id=None, start_date=None, end_date=None):
	"""Récupère un résumé des statuts de paiement"""
	try:
		if not start_date:
			start_date = f"{getdate().year}-01-01"
		if not end_date:
			end_date = nowdate()
		
		# Construction des filtres
		filters = []
		if location_id:
			filters.append(f"(pl.location_longue_duree_id = '{location_id}' OR pl.location_courte_duree_id = '{location_id}')")
		if appartement_id:
			filters.append(f"(lld.appartement_id = '{appartement_id}' OR lcd.appartement_id = '{appartement_id}')")
		if proprietaire_id:
			filters.append(f"a.proprietaire_id = '{proprietaire_id}'")
		
		where_clause = " AND ".join(filters) if filters else "1=1"
		
		# Statistiques des paiements locataire
		tenant_payments = frappe.db.sql(f"""
			SELECT 
				COUNT(*) as total_paiements,
				SUM(pl.montant) as montant_total,
				SUM(pl.montant_net) as montant_net_total,
				COUNT(CASE WHEN pl.statut = 'Confirmé' THEN 1 END) as paiements_confirmes,
				COUNT(CASE WHEN pl.statut = 'En attente' THEN 1 END) as paiements_en_attente,
				COUNT(CASE WHEN pl.statut = 'Rejeté' THEN 1 END) as paiements_rejetes,
				SUM(CASE WHEN pl.statut = 'Confirmé' THEN pl.montant ELSE 0 END) as montant_confirme,
				SUM(CASE WHEN pl.statut = 'En attente' THEN pl.montant ELSE 0 END) as montant_en_attente
			FROM `tabPaiement Locataire` pl
			LEFT JOIN `tabMensualite` m ON pl.mensualite_id = m.name
			LEFT JOIN `tabLocation Longue Duree` lld ON (m.location_longue_duree_id = lld.name OR pl.location_longue_duree_id = lld.name)
			LEFT JOIN `tabLocation Courte Duree` lcd ON pl.location_courte_duree_id = lcd.name
			LEFT JOIN `tabAppartement` a ON (lld.appartement_id = a.name OR lcd.appartement_id = a.name)
			WHERE {where_clause}
				AND pl.date_paiement BETWEEN '{start_date}' AND '{end_date}'
				AND pl.docstatus != 2
		""", as_dict=True)
		
		# Statistiques des paiements propriétaire
		owner_payments = frappe.db.sql(f"""
			SELECT 
				COUNT(*) as total_versements,
				SUM(pp.montant) as montant_total_verse,
				SUM(pp.montant_net) as montant_net_total_verse,
				COUNT(CASE WHEN pp.statut = 'Payé' THEN 1 END) as versements_payes,
				COUNT(CASE WHEN pp.statut = 'En attente' THEN 1 END) as versements_en_attente,
				COUNT(CASE WHEN pp.statut = 'Rejeté' THEN 1 END) as versements_rejetes,
				SUM(CASE WHEN pp.statut = 'Payé' THEN pp.montant ELSE 0 END) as montant_paye,
				SUM(CASE WHEN pp.statut = 'En attente' THEN pp.montant ELSE 0 END) as montant_en_attente_versement
			FROM `tabPaiement Propriétaire` pp
			LEFT JOIN `tabMensualite` m ON pp.mensualite_id = m.name
			LEFT JOIN `tabLocation Longue Duree` lld ON (m.location_longue_duree_id = lld.name OR pp.location_longue_duree_id = lld.name)
			LEFT JOIN `tabLocation Courte Duree` lcd ON pp.location_courte_duree_id = lcd.name
			LEFT JOIN `tabAppartement` a ON (lld.appartement_id = a.name OR lcd.appartement_id = a.name)
			WHERE {where_clause}
				AND pp.date_paiement BETWEEN '{start_date}' AND '{end_date}'
				AND pp.docstatus != 2
		""", as_dict=True)
		
		tenant_data = tenant_payments[0] if tenant_payments else {}
		owner_data = owner_payments[0] if owner_payments else {}
		
		# Calculs des taux
		tenant_success_rate = (tenant_data.get('paiements_confirmes', 0) / tenant_data.get('total_paiements', 1) * 100) if tenant_data.get('total_paiements', 0) > 0 else 0
		owner_success_rate = (owner_data.get('versements_payes', 0) / owner_data.get('total_versements', 1) * 100) if owner_data.get('total_versements', 0) > 0 else 0
		
		return {
			"success": True,
			"periode": {
				"debut": start_date,
				"fin": end_date
			},
			"paiements_locataire": {
				"total_paiements": tenant_data.get('total_paiements', 0),
				"montant_total": tenant_data.get('montant_total', 0),
				"montant_net_total": tenant_data.get('montant_net_total', 0),
				"paiements_confirmes": tenant_data.get('paiements_confirmes', 0),
				"paiements_en_attente": tenant_data.get('paiements_en_attente', 0),
				"paiements_rejetes": tenant_data.get('paiements_rejetes', 0),
				"montant_confirme": tenant_data.get('montant_confirme', 0),
				"montant_en_attente": tenant_data.get('montant_en_attente', 0),
				"taux_succes": tenant_success_rate
			},
			"paiements_proprietaire": {
				"total_versements": owner_data.get('total_versements', 0),
				"montant_total_verse": owner_data.get('montant_total_verse', 0),
				"montant_net_total_verse": owner_data.get('montant_net_total_verse', 0),
				"versements_payes": owner_data.get('versements_payes', 0),
				"versements_en_attente": owner_data.get('versements_en_attente', 0),
				"versements_rejetes": owner_data.get('versements_rejetes', 0),
				"montant_paye": owner_data.get('montant_paye', 0),
				"montant_en_attente_versement": owner_data.get('montant_en_attente_versement', 0),
				"taux_succes": owner_success_rate
			}
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur résumé statuts paiement: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def reconcile_payments_with_mensualites(location_longue_duree_id):
	"""Réconcilie les paiements avec les mensualités pour une location"""
	try:
		# Vérification de la location
		if not frappe.db.exists("Location Longue Durée", location_longue_duree_id):
			frappe.throw(_("Location longue durée non trouvée"))
		
		reconciled = []
		errors = []
		
		# Récupère les paiements non associés à une mensualité
		unmatched_payments = frappe.get_all("Paiement Locataire", {
			"location_longue_duree_id": location_longue_duree_id,
			"mensualite_id": ["", "is", "not set"],
			"type_paiement": "Loyer mensuel",
			"statut": "Confirmé"
		}, ["name", "date_paiement", "montant"])
		
		for payment in unmatched_payments:
			try:
				# Détermine le mois/année du paiement
				payment_date = getdate(payment.date_paiement)
				mois_annee = f"{payment_date.month:02d}/{payment_date.year}"
				
				# Recherche une mensualité correspondante
				mensualite = frappe.db.get_value("Mensualite", {
					"location_longue_duree_id": location_longue_duree_id,
					"mois_annee": mois_annee
				}, "name")
				
				if mensualite:
					# Associe le paiement à la mensualité
					frappe.db.set_value("Paiement Locataire", payment.name, "mensualite_id", mensualite)
					
					# Met à jour la mensualité
					frappe.db.set_value("Mensualite", mensualite, {
						"statut_paiement_locataire": "Payé",
						"date_paiement_locataire": payment.date_paiement
					})
					
					reconciled.append({
						"paiement_id": payment.name,
						"mensualite_id": mensualite,
						"mois_annee": mois_annee,
						"montant": payment.montant
					})
				else:
					errors.append({
						"paiement_id": payment.name,
						"error": f"Aucune mensualité trouvée pour {mois_annee}"
					})
				
			except Exception as e:
				errors.append({
					"paiement_id": payment.name,
					"error": str(e)
				})
		
		return {
			"success": True,
			"location_id": location_longue_duree_id,
			"reconciled": reconciled,
			"errors": errors,
			"total_reconciled": len(reconciled),
			"total_errors": len(errors)
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur réconciliation paiements: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def get_overdue_payments(days_overdue=30):
	"""Récupère les paiements en retard"""
	try:
		days_overdue = int(days_overdue)
		cutoff_date = getdate() - timedelta(days=days_overdue)
		
		# Mensualités en retard (paiement locataire)
		overdue_tenant = frappe.db.sql("""
			SELECT 
				m.name as mensualite_id,
				m.mois_annee,
				m.loyer_locataire,
				lld.name as location_id,
				lld.locataire_nom,
				lld.locataire_email,
				a.adresse as appartement_adresse,
				p.nom_complet as proprietaire_nom,
				DATEDIFF(CURDATE(), STR_TO_DATE(CONCAT(m.mois_annee, '-01'), '%m/%Y-%d')) as jours_retard
			FROM `tabMensualite` m
			INNER JOIN `tabLocation Longue Durée` lld ON m.location_longue_duree_id = lld.name
			INNER JOIN `tabAppartement` a ON lld.appartement_id = a.name
			INNER JOIN `tabProprietaire` p ON a.proprietaire_id = p.name
			WHERE m.statut_paiement_locataire = 'En attente'
				AND STR_TO_DATE(CONCAT(m.mois_annee, '-01'), '%m/%Y-%d') <= %s
				AND m.docstatus != 2
				AND lld.statut = 'Actif'
			ORDER BY STR_TO_DATE(CONCAT(m.mois_annee, '-01'), '%m/%Y-%d') ASC
		""", (cutoff_date,), as_dict=True)
		
		# Versements en retard (paiement propriétaire)
		overdue_owner = frappe.db.sql("""
			SELECT 
				pp.name as paiement_id,
				pp.montant,
				pp.date_paiement,
				m.mois_annee,
				lld.name as location_id,
				a.adresse as appartement_adresse,
				p.nom_complet as proprietaire_nom,
				p.email as proprietaire_email,
				DATEDIFF(CURDATE(), pp.date_paiement) as jours_retard
			FROM `tabPaiement Proprietaire` pp
			LEFT JOIN `tabMensualite` m ON pp.mensualite_id = m.name
			LEFT JOIN `tabLocation Longue Durée` lld ON (m.location_longue_duree_id = lld.name OR pp.location_longue_duree_id = lld.name)
			LEFT JOIN `tabLocation Courte Duree` lcd ON pp.location_courte_duree_id = lcd.name
			LEFT JOIN `tabAppartement` a ON (lld.appartement_id = a.name OR lcd.appartement_id = a.name)
			LEFT JOIN `tabProprietaire` p ON a.proprietaire_id = p.name
			WHERE pp.statut = 'En attente'
				AND pp.date_paiement <= %s
				AND pp.docstatus != 2
			ORDER BY pp.date_paiement ASC
		""", (cutoff_date,), as_dict=True)
		
		return {
			"success": True,
			"cutoff_date": cutoff_date,
			"days_overdue": days_overdue,
			"overdue_tenant_payments": overdue_tenant,
			"overdue_owner_payments": overdue_owner,
			"total_overdue_tenant": len(overdue_tenant),
			"total_overdue_owner": len(overdue_owner)
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur paiements en retard: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def send_payment_reminders(reminder_type="tenant", days_overdue=30):
	"""Envoie des rappels de paiement"""
	try:
		overdue_data = get_overdue_payments(days_overdue)
		
		if not overdue_data.get("success"):
			return overdue_data
		
		reminders_sent = []
		errors = []
		
		if reminder_type == "tenant":
			for payment in overdue_data["overdue_tenant_payments"]:
				try:
					if payment.get("locataire_email"):
						subject = f"Rappel de paiement - {payment['appartement_adresse']}"
						message = f"""
						Bonjour {payment['locataire_nom']},
						
						Nous vous rappelons que votre loyer pour {payment['mois_annee']} est en retard de {payment['jours_retard']} jours.
						
						Montant dû: {payment['loyer_locataire']} €
						Appartement: {payment['appartement_adresse']}
						
						Merci de régulariser votre situation dans les plus brefs délais.
						
						Cordialement,
						L'équipe de gestion
						"""
						
						# Envoie l'email (à implémenter selon la configuration email)
						# frappe.sendmail(
						#     recipients=[payment['locataire_email']],
						#     subject=subject,
						#     message=message
						# )
						
						reminders_sent.append({
							"type": "tenant",
							"mensualite_id": payment["mensualite_id"],
							"email": payment["locataire_email"],
							"jours_retard": payment["jours_retard"]
						})
					
				except Exception as e:
					errors.append({
						"mensualite_id": payment["mensualite_id"],
						"error": str(e)
					})
		
		elif reminder_type == "owner":
			for payment in overdue_data["overdue_owner_payments"]:
				try:
					if payment.get("proprietaire_email"):
						subject = f"Retard de versement - {payment['appartement_adresse']}"
						message = f"""
						Bonjour {payment['proprietaire_nom']},
						
						Nous vous informons que votre versement prévu le {payment['date_paiement']} est en retard de {payment['jours_retard']} jours.
						
						Montant: {payment['montant']} €
						Appartement: {payment['appartement_adresse']}
						
						Nous travaillons à résoudre ce retard dans les plus brefs délais.
						
						Cordialement,
						L'équipe de gestion
						"""
						
						# Envoie l'email (à implémenter selon la configuration email)
						# frappe.sendmail(
						#     recipients=[payment['proprietaire_email']],
						#     subject=subject,
						#     message=message
						# )
						
						reminders_sent.append({
							"type": "owner",
							"paiement_id": payment["paiement_id"],
							"email": payment["proprietaire_email"],
							"jours_retard": payment["jours_retard"]
						})
					
				except Exception as e:
					errors.append({
						"paiement_id": payment["paiement_id"],
						"error": str(e)
					})
		
		return {
			"success": True,
			"reminder_type": reminder_type,
			"reminders_sent": reminders_sent,
			"errors": errors,
			"total_sent": len(reminders_sent),
			"total_errors": len(errors)
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur envoi rappels: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}