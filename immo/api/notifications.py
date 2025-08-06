# Copyright (c) 2024, Frappe Technologies and Contributors
# See license.txt

import frappe
from frappe import _
from frappe.utils import nowdate, getdate, add_days, cstr
from frappe.core.doctype.communication.email import make
import json


@frappe.whitelist()
def send_payment_reminder(payment_type, payment_id, reminder_type="standard"):
	"""Envoie un rappel de paiement"""
	try:
		if payment_type == "tenant":
			payment = frappe.get_doc("Paiement Locataire", payment_id)
			recipient_email = payment.email_locataire
			recipient_name = payment.nom_locataire
			amount = payment.montant_total
			payment_date = payment.date_echeance
			subject_prefix = "Rappel de paiement de loyer"
		else:
			payment = frappe.get_doc("Paiement Propriétaire", payment_id)
			recipient_email = payment.email_proprietaire
			recipient_name = payment.nom_proprietaire
			amount = payment.montant_net
			payment_date = payment.date_prevue
			subject_prefix = "Rappel de versement"
		
		if not recipient_email:
			return {
				"success": False,
				"error": "Adresse email manquante"
			}
		
		# Sélection du template selon le type de rappel
		if reminder_type == "urgent":
			subject = f"{subject_prefix} - URGENT - {payment.name}"
			template_name = f"urgent_{payment_type}_payment_reminder"
		elif reminder_type == "final":
			subject = f"{subject_prefix} - DERNIER RAPPEL - {payment.name}"
			template_name = f"final_{payment_type}_payment_reminder"
		else:
			subject = f"{subject_prefix} - {payment.name}"
			template_name = f"standard_{payment_type}_payment_reminder"
		
		# Préparation des données pour le template
		template_data = {
			"recipient_name": recipient_name,
			"payment_id": payment.name,
			"amount": amount,
			"payment_date": payment_date,
			"current_date": nowdate(),
			"payment_type": payment_type,
			"reminder_type": reminder_type
		}
		
		if payment_type == "tenant":
			template_data.update({
				"appartement_adresse": payment.appartement_adresse,
				"type_paiement": payment.type_paiement,
				"periode": payment.periode
			})
		else:
			template_data.update({
				"appartement_adresse": payment.appartement_adresse,
				"montant_brut": payment.montant_brut,
				"frais_gestion": payment.frais_gestion
			})
		
		# Envoi de l'email
		send_result = send_email_notification(
			recipient_email,
			subject,
			template_name,
			template_data
		)
		
		if send_result["success"]:
			# Mise à jour du statut de rappel
			payment.db_set("dernier_rappel", nowdate())
			payment.db_set("nombre_rappels", (payment.nombre_rappels or 0) + 1)
			
			# Log de l'activité
			frappe.get_doc({
				"doctype": "Communication",
				"communication_type": "Email",
				"subject": subject,
				"content": f"Rappel de paiement envoyé ({reminder_type})",
				"reference_doctype": payment.doctype,
				"reference_name": payment.name,
				"recipients": recipient_email,
				"sent_or_received": "Sent"
			}).insert(ignore_permissions=True)
		
		return send_result
		
	except Exception as e:
		frappe.log_error(f"Erreur envoi rappel paiement: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def send_bulk_payment_reminders(payment_type, filters=None, reminder_type="standard"):
	"""Envoie des rappels de paiement en masse"""
	try:
		if not filters:
			filters = {}
		
		# Construction de la requête selon le type de paiement
		if payment_type == "tenant":
			doctype = "Paiement Locataire"
			default_filters = {
				"statut": ["in", ["En attente", "Rejeté"]],
				"date_echeance": ["<", nowdate()]
			}
		else:
			doctype = "Paiement Propriétaire"
			default_filters = {
				"statut": ["in", ["En attente", "Rejeté"]],
				"date_prevue": ["<", nowdate()]
			}
		
		# Fusion des filtres
		final_filters = {**default_filters, **filters}
		
		# Récupération des paiements en retard
		overdue_payments = frappe.get_all(
			doctype,
			filters=final_filters,
			fields=["name", "email_locataire" if payment_type == "tenant" else "email_proprietaire"]
		)
		
		results = {
			"total_payments": len(overdue_payments),
			"sent_successfully": 0,
			"failed": 0,
			"errors": []
		}
		
		# Envoi des rappels
		for payment in overdue_payments:
			email_field = "email_locataire" if payment_type == "tenant" else "email_proprietaire"
			if payment.get(email_field):
				reminder_result = send_payment_reminder(
					payment_type,
					payment.name,
					reminder_type
				)
				
				if reminder_result["success"]:
					results["sent_successfully"] += 1
				else:
					results["failed"] += 1
					results["errors"].append({
						"payment_id": payment.name,
						"error": reminder_result.get("error")
					})
			else:
				results["failed"] += 1
				results["errors"].append({
					"payment_id": payment.name,
					"error": "Adresse email manquante"
				})
		
		return {
			"success": True,
			"results": results
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur envoi rappels en masse: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def send_commission_notification(commission_id, notification_type):
	"""Envoie une notification de commission"""
	try:
		commission = frappe.get_doc("Commission", commission_id)
		referent = frappe.get_doc("Referent", commission.referent_id)
		
		if not referent.email:
			return {
				"success": False,
				"error": "Adresse email du référent manquante"
			}
		
		# Sélection du template selon le type de notification
		if notification_type == "paid":
			subject = f"Commission payée - {commission.name}"
			template_name = "commission_paid_notification"
		elif notification_type == "rejected":
			subject = f"Commission rejetée - {commission.name}"
			template_name = "commission_rejected_notification"
		elif notification_type == "pending":
			subject = f"Nouvelle commission en attente - {commission.name}"
			template_name = "commission_pending_notification"
		else:
			return {
				"success": False,
				"error": "Type de notification invalide"
			}
		
		# Récupération des informations de la location
		location = frappe.get_doc("Location Courte Duree", commission.location_courte_duree_id)
		appartement = frappe.get_doc("Appartement", location.appartement_id)
		
		# Préparation des données pour le template
		template_data = {
			"referent_name": referent.nom_complet,
			"commission_id": commission.name,
			"commission_amount": commission.montant_commission,
			"commission_percentage": commission.pourcentage_commission,
			"location_id": location.name,
			"appartement_adresse": appartement.adresse,
			"location_dates": f"{location.date_debut} - {location.date_fin}",
			"total_margin": location.marge_totale,
			"current_date": nowdate(),
			"notification_type": notification_type
		}
		
		if notification_type == "paid":
			template_data.update({
				"payment_date": commission.date_paiement,
				"payment_method": commission.methode_paiement
			})
		elif notification_type == "rejected":
			template_data.update({
				"rejection_reason": commission.motif_rejet or "Non spécifié"
			})
		
		# Envoi de l'email
		send_result = send_email_notification(
			referent.email,
			subject,
			template_name,
			template_data
		)
		
		if send_result["success"]:
			# Log de l'activité
			frappe.get_doc({
				"doctype": "Communication",
				"communication_type": "Email",
				"subject": subject,
				"content": f"Notification de commission envoyée ({notification_type})",
				"reference_doctype": "Commission",
				"reference_name": commission.name,
				"recipients": referent.email,
				"sent_or_received": "Sent"
			}).insert(ignore_permissions=True)
		
		return send_result
		
	except Exception as e:
		frappe.log_error(f"Erreur envoi notification commission: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def send_monthly_summary(proprietaire_id=None, month=None, year=None):
	"""Envoie un résumé mensuel aux propriétaires"""
	try:
		if not month:
			month = getdate().month
		if not year:
			year = getdate().year
		
		# Période du rapport
		start_date = f"{year}-{month:02d}-01"
		end_date = f"{year}-{month:02d}-31"
		
		# Filtres pour les propriétaires
		filters = {}
		if proprietaire_id:
			filters["name"] = proprietaire_id
		
		proprietaires = frappe.get_all(
			"Proprietaire",
			filters=filters,
			fields=["name", "nom_complet", "email"]
		)
		
		results = {
			"total_proprietaires": len(proprietaires),
			"sent_successfully": 0,
			"failed": 0,
			"errors": []
		}
		
		for proprietaire in proprietaires:
			if not proprietaire.email:
				results["failed"] += 1
				results["errors"].append({
					"proprietaire_id": proprietaire.name,
					"error": "Adresse email manquante"
				})
				continue
			
			try:
				# Récupération des données du propriétaire pour le mois
				monthly_data = get_proprietaire_monthly_data(
					proprietaire.name,
					start_date,
					end_date
				)
				
				# Préparation du template
				subject = f"Résumé mensuel - {month:02d}/{year} - {proprietaire.nom_complet}"
				template_data = {
					"proprietaire_name": proprietaire.nom_complet,
					"month": month,
					"year": year,
					"period": f"{month:02d}/{year}",
					**monthly_data
				}
				
				# Envoi de l'email
				send_result = send_email_notification(
					proprietaire.email,
					subject,
					"monthly_summary_proprietaire",
					template_data
				)
				
				if send_result["success"]:
					results["sent_successfully"] += 1
				else:
					results["failed"] += 1
					results["errors"].append({
						"proprietaire_id": proprietaire.name,
						"error": send_result.get("error")
					})
				
			except Exception as e:
				results["failed"] += 1
				results["errors"].append({
					"proprietaire_id": proprietaire.name,
					"error": str(e)
				})
		
		return {
			"success": True,
			"results": results
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur envoi résumés mensuels: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


@frappe.whitelist()
def schedule_automatic_notifications():
	"""Programme les notifications automatiques"""
	try:
		results = {
			"payment_reminders": {},
			"monthly_summaries": {},
			"commission_notifications": {}
		}
		
		# 1. Rappels de paiement automatiques
		# Rappels standard (7 jours de retard)
		standard_reminder_date = add_days(nowdate(), -7)
		standard_filters = {
			"date_echeance": standard_reminder_date,
			"dernier_rappel": ["", "is", "not set"]
		}
		
		results["payment_reminders"]["standard_tenant"] = send_bulk_payment_reminders(
			"tenant", standard_filters, "standard"
		)
		
		results["payment_reminders"]["standard_owner"] = send_bulk_payment_reminders(
			"owner", standard_filters, "standard"
		)
		
		# Rappels urgents (15 jours de retard)
		urgent_reminder_date = add_days(nowdate(), -15)
		urgent_filters = {
			"date_echeance": urgent_reminder_date,
			"nombre_rappels": 1
		}
		
		results["payment_reminders"]["urgent_tenant"] = send_bulk_payment_reminders(
			"tenant", urgent_filters, "urgent"
		)
		
		results["payment_reminders"]["urgent_owner"] = send_bulk_payment_reminders(
			"owner", urgent_filters, "urgent"
		)
		
		# 2. Résumés mensuels (envoyés le 1er de chaque mois)
		if getdate().day == 1:
			previous_month = getdate().month - 1 if getdate().month > 1 else 12
			previous_year = getdate().year if getdate().month > 1 else getdate().year - 1
			
			results["monthly_summaries"] = send_monthly_summary(
				month=previous_month,
				year=previous_year
			)
		
		# 3. Notifications de commissions en attente (hebdomadaire)
		if getdate().weekday() == 0:  # Lundi
			pending_commissions = frappe.get_all(
				"Commission",
				filters={
					"statut": "En attente",
					"creation": [">=", add_days(nowdate(), -7)]
				},
				fields=["name"]
			)
			
			commission_results = {
				"total": len(pending_commissions),
				"sent": 0,
				"failed": 0
			}
			
			for commission in pending_commissions:
				notif_result = send_commission_notification(
					commission.name,
					"pending"
				)
				
				if notif_result["success"]:
					commission_results["sent"] += 1
				else:
					commission_results["failed"] += 1
			
			results["commission_notifications"] = commission_results
		
		return {
			"success": True,
			"results": results,
			"execution_date": nowdate()
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur notifications automatiques: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


def send_email_notification(recipient, subject, template_name, template_data):
	"""Fonction utilitaire pour envoyer des emails"""
	try:
		# Récupération du template d'email
		try:
			email_template = frappe.get_doc("Email Template", template_name)
			content = frappe.render_template(email_template.response, template_data)
		except frappe.DoesNotExistError:
			# Template par défaut si le template spécifique n'existe pas
			content = generate_default_email_content(template_name, template_data)
		
		# Envoi de l'email
		make(
			recipients=recipient,
			subject=subject,
			content=content,
			send_email=True
		)
		
		return {
			"success": True,
			"message": "Email envoyé avec succès"
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur envoi email: {str(e)}")
		return {
			"success": False,
			"error": str(e)
		}


def generate_default_email_content(template_name, data):
	"""Génère un contenu d'email par défaut"""
	if "payment_reminder" in template_name:
		return f"""
		<h3>Rappel de paiement</h3>
		<p>Bonjour {data.get('recipient_name', '')},</p>
		<p>Nous vous rappelons qu'un paiement de <strong>{data.get('amount', 0)} €</strong> 
		   était attendu le {data.get('payment_date', '')}.</p>
		<p>Référence: {data.get('payment_id', '')}</p>
		<p>Merci de régulariser votre situation dans les plus brefs délais.</p>
		<p>Cordialement,<br>L'équipe de gestion</p>
		"""
	
	elif "commission" in template_name:
		return f"""
		<h3>Notification de commission</h3>
		<p>Bonjour {data.get('referent_name', '')},</p>
		<p>Votre commission de <strong>{data.get('commission_amount', 0)} €</strong> 
		   ({data.get('commission_percentage', 0)}%) a été mise à jour.</p>
		<p>Référence: {data.get('commission_id', '')}</p>
		<p>Location: {data.get('appartement_adresse', '')} du {data.get('location_dates', '')}</p>
		<p>Cordialement,<br>L'équipe de gestion</p>
		"""
	
	elif "monthly_summary" in template_name:
		return f"""
		<h3>Résumé mensuel - {data.get('period', '')}</h3>
		<p>Bonjour {data.get('proprietaire_name', '')},</p>
		<p>Voici votre résumé d'activité pour le mois de {data.get('period', '')}:</p>
		<ul>
			<li>Revenus totaux: {data.get('total_revenus', 0)} €</li>
			<li>Charges: {data.get('total_charges', 0)} €</li>
			<li>Marge nette: {data.get('marge_nette', 0)} €</li>
		</ul>
		<p>Cordialement,<br>L'équipe de gestion</p>
		"""
	
	else:
		return f"""
		<h3>Notification</h3>
		<p>Bonjour,</p>
		<p>Vous avez reçu une nouvelle notification.</p>
		<p>Cordialement,<br>L'équipe de gestion</p>
		"""


def get_proprietaire_monthly_data(proprietaire_id, start_date, end_date):
	"""Récupère les données mensuelles d'un propriétaire"""
	try:
		# Revenus des locations longue durée
		long_term_data = frappe.db.sql("""
			SELECT 
				SUM(m.loyer_proprietaire) as revenus_longue_duree,
				SUM(m.marge_mensuelle) as marge_longue_duree,
				COUNT(m.name) as nombre_mensualites
			FROM `tabMensualite` m
			INNER JOIN `tabLocation Longue Durée` lld ON m.location_longue_duree_id = lld.name
			INNER JOIN `tabAppartement` a ON lld.appartement_id = a.name
			WHERE a.proprietaire_id = %s
				AND m.date_echeance BETWEEN %s AND %s
				AND m.docstatus != 2
		""", (proprietaire_id, start_date, end_date), as_dict=True)
		
		# Revenus des locations courte durée
		short_term_data = frappe.db.sql("""
			SELECT 
				SUM(lcd.total_proprietaire) as revenus_courte_duree,
				SUM(lcd.marge_totale) as marge_courte_duree,
				COUNT(lcd.name) as nombre_locations
			FROM `tabLocation Courte Duree` lcd
			INNER JOIN `tabAppartement` a ON lcd.appartement_id = a.name
			WHERE a.proprietaire_id = %s
				AND lcd.date_debut BETWEEN %s AND %s
				AND lcd.docstatus != 2
		""", (proprietaire_id, start_date, end_date), as_dict=True)
		
		# Charges
		charges_data = frappe.db.sql("""
			SELECT 
				SUM(ch.montant_proprietaire) as charges_proprietaire,
				COUNT(ch.name) as nombre_charges
			FROM `tabCharge` ch
			INNER JOIN `tabAppartement` a ON ch.appartement_id = a.name
			WHERE a.proprietaire_id = %s
				AND ch.date_charge BETWEEN %s AND %s
				AND ch.docstatus != 2
		""", (proprietaire_id, start_date, end_date), as_dict=True)
		
		# Compilation des données
		ld = long_term_data[0] if long_term_data else {}
		cd = short_term_data[0] if short_term_data else {}
		ch = charges_data[0] if charges_data else {}
		
		return {
			"revenus_longue_duree": ld.get("revenus_longue_duree", 0) or 0,
			"revenus_courte_duree": cd.get("revenus_courte_duree", 0) or 0,
			"total_revenus": (ld.get("revenus_longue_duree", 0) or 0) + (cd.get("revenus_courte_duree", 0) or 0),
			"marge_longue_duree": ld.get("marge_longue_duree", 0) or 0,
			"marge_courte_duree": cd.get("marge_courte_duree", 0) or 0,
			"total_charges": ch.get("charges_proprietaire", 0) or 0,
			"marge_nette": ((ld.get("marge_longue_duree", 0) or 0) + (cd.get("marge_courte_duree", 0) or 0)) - (ch.get("charges_proprietaire", 0) or 0),
			"nombre_mensualites": ld.get("nombre_mensualites", 0) or 0,
			"nombre_locations": cd.get("nombre_locations", 0) or 0,
			"nombre_charges": ch.get("nombre_charges", 0) or 0
		}
		
	except Exception as e:
		frappe.log_error(f"Erreur récupération données mensuelles propriétaire: {str(e)}")
		return {}