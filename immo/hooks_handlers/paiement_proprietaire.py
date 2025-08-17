# Copyright (c) 2024, Frappe Technologies and Contributors
# See license.txt

import frappe
from frappe.utils import nowdate, getdate, add_months


def on_update(doc, method):
	"""Actions après mise à jour du paiement propriétaire"""
	try:
		# Vérifier que le document existe en base et a un nom
		if not doc.name or doc.docstatus == 0:
			return
		
		# Met à jour le statut de la mensualité si confirmé
		if doc.status == "Payé" and doc.type_paiement == "Loyer mensuel":
			update_mensualite_status(doc)
		
		# Traite les paiements de référents pour les locations courte durée
		# DÉSACTIVÉ: if doc.status == "Payé" and doc.location_courte_duree_id:
		#	process_referent_payment(doc)
		
		# NOTE: Les statistiques du propriétaire ne sont plus mises à jour
		# car le dashboard HTML affiche ces informations en temps réel
		# via l'API get_proprietaire_dashboard_data
		
		# Met à jour les statistiques de la location
		update_location_payout_statistics(doc)
		
		# Met à jour les statistiques de l'appartement
		update_apartment_payout_statistics(doc)
		
		# Mettre à jour le statut des paiements de la location courte durée
		if doc.location_courte_duree_id:
			update_location_courte_duree_payment_status(doc)
		
	except Exception as e:
		frappe.log_error(f"Erreur dans on_update Paiement Proprietaire {doc.name}: {str(e)}")
		# Ne pas faire échouer la sauvegarde pour des erreurs de statistiques


def on_cancel(doc, method):
	"""Actions lors de l'annulation du paiement"""
	try:
		# Remet à jour le statut de la mensualité
		if doc.type_paiement == "Loyer mensuel" and doc.mensualite_id:
			revert_mensualite_status(doc)
		
		# NOTE: Les statistiques du propriétaire ne sont plus mises à jour
		# car le dashboard HTML affiche ces informations en temps réel
		
		# Met à jour les statistiques de la location
		update_location_payout_statistics(doc)
		
		# Met à jour les statistiques de l'appartement
		update_apartment_payout_statistics(doc)
		
		# Mettre à jour le statut des paiements de la location courte durée
		if doc.location_courte_duree_id:
			update_location_courte_duree_payment_status(doc)
		
	except Exception as e:
		frappe.log_error(f"Erreur dans on_cancel Paiement Proprietaire {doc.name}: {str(e)}")
		# Ne pas faire échouer l'annulation pour des erreurs de statistiques


def update_mensualite_status(doc):
	"""Met à jour le statut de paiement de la mensualité"""
	if not doc.mensualite_id:
		return
	
	try:
		# Met à jour le statut de paiement propriétaire de la mensualité
		frappe.db.set_value("Mensualite", doc.mensualite_id, {
			"statut_paiement_proprietaire": "Payé",
			"date_paiement_proprietaire": doc.date_paiement,
			"methode_paiement_proprietaire": doc.methode_paiement,
			"reference_paiement_proprietaire": doc.reference_financiere
		})
		
		# Vérifie si la mensualité est complètement payée (locataire + propriétaire)
		mensualite = frappe.get_doc("Mensualite", doc.mensualite_id)
		if (mensualite.statut_paiement_locataire == "Payé" and
			mensualite.statut_paiement_proprietaire == "Payé"):
			frappe.db.set_value("Mensualite", doc.mensualite_id, "statut_global", "Complète")
			
			# Génère automatiquement la mensualité suivante si configuré
			generate_next_mensualite_if_needed(mensualite)
			
	except Exception as e:
		frappe.log_error(f"Erreur lors de la mise à jour de la mensualité: {str(e)}")


def revert_mensualite_status(doc):
	"""Remet le statut de la mensualité lors de l'annulation"""
	try:
		frappe.db.set_value("Mensualite", doc.mensualite_id, {
			"statut_paiement_proprietaire": "En attente",
			"date_paiement_proprietaire": None,
			"methode_paiement_proprietaire": None,
			"reference_paiement_proprietaire": None,
			"statut_global": "En attente"
		})
		
	except Exception as e:
		frappe.log_error(f"Erreur lors de la remise à jour de la mensualité: {str(e)}")


def generate_next_mensualite_if_needed(mensualite):
	"""Génère la mensualité suivante si nécessaire"""
	try:
		# Récupère la location pour vérifier si elle est toujours active
		location = frappe.get_doc("Location Longue Duree", mensualite.location_longue_duree_id)
		
		if location.statut != "Actif":
			return
		
		# Calcule le mois suivant
		current_date = getdate(f"{mensualite.mois_annee.split('/')[1]}-{mensualite.mois_annee.split('/')[0]}-01")
		next_month_date = add_months(current_date, 1)
		next_mois_annee = f"{next_month_date.month:02d}/{next_month_date.year}"
		
		# Vérifie si la mensualité suivante n'existe pas déjà
		existing_next = frappe.db.exists("Mensualite", {
			"location_longue_duree_id": mensualite.location_longue_duree_id,
			"mois_annee": next_mois_annee
		})
		
		if not existing_next:
			# Vérifie si on n'a pas dépassé la date de fin de location
			if location.date_fin and next_month_date > getdate(location.date_fin):
				return
			
			# Crée la mensualité suivante
			next_mensualite = frappe.get_doc({
				"doctype": "Mensualite",
				"location_longue_duree_id": mensualite.location_longue_duree_id,
				"mois_annee": next_mois_annee,
				"loyer_locataire": mensualite.loyer_locataire,
				"loyer_proprietaire": mensualite.loyer_proprietaire,
				"marge_mensuelle": mensualite.marge_mensuelle,
				"statut_paiement_locataire": "En attente",
				"statut_paiement_proprietaire": "En attente",
				"statut_global": "En attente"
			})
			next_mensualite.insert()
			
	except Exception as e:
		frappe.log_error(f"Erreur lors de la génération de la mensualité suivante: {str(e)}")


def update_location_payout_statistics(doc):
	"""Met à jour les statistiques de versement de la location"""
	try:
		location_id = None
		location_type = None
		
		# Détermine l'ID de la location selon le type
		if doc.mensualite_id:
			# Récupère la location via la mensualité
			mensualite = frappe.get_doc("Mensualite", doc.mensualite_id)
			location_id = mensualite.location_longue_duree_id
			location_type = "Location Longue Duree"
		elif doc.location_longue_duree_id:
			location_id = doc.location_longue_duree_id
			location_type = "Location Longue Duree"
		elif doc.location_courte_duree_id:
			location_id = doc.location_courte_duree_id
			location_type = "Location Courte Duree"
		
		if not location_id:
			return
		
		# Calcule les statistiques de versement pour cette location
		if location_type == "Location Courte Duree":
			stats = frappe.db.sql("""
				SELECT 
					COUNT(*) as total_versements,
					SUM(montant) as montant_total_verse,
					SUM(montant) as montant_net_total_verse,
					0 as frais_totaux_versement,
					SUM(CASE WHEN status = 'Payé' THEN 1 ELSE 0 END) as versements_effectues,
					SUM(CASE WHEN status = 'Nouveau' THEN 1 ELSE 0 END) as versements_en_attente,
					AVG(montant) as montant_moyen_versement
				FROM `tabPaiement Propriétaire`
				WHERE location_courte_duree_id = %s
			""", (location_id,), as_dict=True)
		else:
			# Location Longue Duree
			stats = frappe.db.sql("""
				SELECT 
					COUNT(*) as total_versements,
					SUM(montant) as montant_total_verse,
					SUM(montant) as montant_net_total_verse,
					0 as frais_totaux_versement,
					SUM(CASE WHEN status = 'Payé' THEN 1 ELSE 0 END) as versements_effectues,
					SUM(CASE WHEN status = 'Nouveau' THEN 1 ELSE 0 END) as versements_en_attente,
					AVG(montant) as montant_moyen_versement
				FROM `tabPaiement Propriétaire`
				WHERE (
					(mensualite_id IN (
						SELECT name FROM `tabMensualite` 
						WHERE location_longue_duree_id = %s
					))
					OR location_longue_duree_id = %s
				)
			""", (location_id, location_id), as_dict=True)
		
		if stats:
			stat = stats[0]
			# Met à jour la location avec les nouvelles statistiques
			update_data = {
				"total_paiements_verses": stat.montant_total_verse or 0,
				"total_frais_versement": stat.frais_totaux_versement or 0,
				"nombre_paiements_proprietaire": stat.total_versements or 0,
				"taux_paiement_proprietaire": (stat.versements_effectues / stat.total_versements * 100) if stat.total_versements > 0 else 0
			}
			
			frappe.db.set_value(location_type, location_id, update_data)
			
	except Exception as e:
		frappe.log_error(f"Erreur lors de la mise à jour des statistiques de location: {str(e)}")
		# Ne pas faire échouer la sauvegarde pour des erreurs de statistiques


def update_apartment_payout_statistics(doc):
	"""Met à jour les statistiques de versement de l'appartement"""
	try:
		appartement_id = None
		
		# Récupère l'ID de l'appartement
		if doc.mensualite_id:
			mensualite = frappe.get_doc("Mensualite", doc.mensualite_id)
			location = frappe.get_doc("Location Longue Duree", mensualite.location_longue_duree_id)
			appartement_id = location.appartement_id
		elif doc.location_longue_duree_id:
			location = frappe.get_doc("Location Longue Duree", doc.location_longue_duree_id)
			appartement_id = location.appartement_id
		elif doc.location_courte_duree_id:
			location = frappe.get_doc("Location Courte Duree", doc.location_courte_duree_id)
			appartement_id = location.appartement_id
		
		if not appartement_id:
			return
		
		# Récupère le propriétaire de l'appartement
		appartement = frappe.get_doc("Appartement", appartement_id)
		proprietaire_id = appartement.proprietaire_id
		
		# Calcule les statistiques globales de versement pour cet appartement (via le propriétaire)
		stats = frappe.db.sql("""
			SELECT 
				SUM(montant) as total_verse_annee,
				SUM(montant) as total_net_verse_annee,
				0 as total_frais_versement_annee,
				COUNT(name) as nombre_versements_annee,
				AVG(montant) as montant_moyen_versement
			FROM `tabPaiement Propriétaire`
			WHERE proprietaire = %s
				AND status = 'Payé'
				AND (date_paiement IS NULL OR YEAR(date_paiement) = YEAR(CURDATE()))
		""", (proprietaire_id,), as_dict=True)
		
		if stats:
			stat = stats[0]
			# Met à jour l'appartement avec les nouvelles statistiques
			frappe.db.set_value("Appartement", appartement_id, {
				"total_verse_annee": stat.total_verse_annee or 0,
				"total_net_verse_annee": stat.total_net_verse_annee or 0,
				"total_frais_versement_annee": stat.total_frais_versement_annee or 0,
				"nombre_versements_proprietaire_annee": stat.nombre_versements_annee or 0
			})
			
	except Exception as e:
		frappe.log_error(f"Erreur lors de la mise à jour des statistiques d'appartement: {str(e)}")
		# Ne pas faire échouer la sauvegarde pour des erreurs de statistiques


def auto_schedule_payouts():
	"""Programme automatiquement les versements pour les mensualités payées"""
	try:
		# Recherche les mensualités avec paiement locataire confirmé mais sans versement propriétaire
		pending_payouts = frappe.db.sql("""
			SELECT 
				m.name as mensualite_id,
				m.location_longue_duree_id,
				m.loyer_proprietaire,
				m.date_paiement_locataire
			FROM `tabMensualite` m
			WHERE m.statut_paiement_locataire = 'Payé'
				AND m.statut_paiement_proprietaire = 'Nouveau'
				AND NOT EXISTS (
					SELECT 1 FROM `tabPaiement Propriétaire` pp 
					WHERE pp.mensualite_id = m.name
				)
		""", as_dict=True)
		
		for payout in pending_payouts:
			# Crée automatiquement un versement propriétaire
			payout_doc = frappe.get_doc({
				"doctype": "Paiement Propriétaire",
				"mensualite_id": payout.mensualite_id,
				"location_longue_duree_id": payout.location_longue_duree_id,
				"type_paiement": "Loyer mensuel",
				"montant": payout.loyer_proprietaire,
				"montant_net": payout.loyer_proprietaire,  # À ajuster selon les frais
				"date_paiement": add_months(getdate(payout.date_paiement_locataire), 0),  # Même mois
				"status": "Nouveau",
				"methode_paiement": "Virement bancaire",  # Par défaut
				"commentaires": "Versement automatiquement programmé"
			})
			payout_doc.insert()
			
	except Exception as e:
		frappe.log_error(f"Erreur lors de la programmation automatique des versements: {str(e)}")


def calculate_owner_performance_metrics(proprietaire_id, start_date=None, end_date=None):
	"""Calcule les métriques de performance pour un propriétaire"""
	try:
		if not start_date:
			start_date = f"{getdate().year}-01-01"
		if not end_date:
			end_date = nowdate()
		
		# Récupère d'abord les statistiques de base du propriétaire
		base_stats = frappe.db.sql("""
			SELECT 
				COUNT(DISTINCT a.name) as nombre_appartements,
				COUNT(DISTINCT lld.name) as nombre_locations_longues,
				COUNT(DISTINCT lcd.name) as nombre_locations_courtes
			FROM `tabProprietaire` p
			LEFT JOIN `tabAppartement` a ON p.name = a.proprietaire_id
			LEFT JOIN `tabLocation Longue Duree` lld ON a.name = lld.appartement_id
			LEFT JOIN `tabLocation Courte Duree` lcd ON a.name = lcd.appartement_id
			WHERE p.name = %s
			GROUP BY p.name
		""", (proprietaire_id,), as_dict=True)
		
		# Récupère les statistiques de paiement séparément
		payment_stats = frappe.db.sql("""
			SELECT 
				SUM(montant) as total_verse,
				SUM(montant_net) as total_net_verse,
				AVG(montant) as montant_moyen_versement,
				COUNT(name) as nombre_versements,
				SUM(CASE WHEN status = 'Payé' THEN montant ELSE 0 END) as montant_paye,
				SUM(CASE WHEN status = 'Payé' THEN 1 ELSE 0 END) as versements_payes,
				SUM(CASE WHEN status = 'Nouveau' THEN 1 ELSE 0 END) as versements_en_attente,
				SUM(CASE WHEN status = 'Annulé' THEN 1 ELSE 0 END) as versements_rejetes
			FROM (
				-- Paiements via mensualités
				SELECT pp.* FROM `tabPaiement Propriétaire` pp
				INNER JOIN `tabMensualite` m ON pp.mensualite_id = m.name
				INNER JOIN `tabLocation Longue Duree` lld ON m.location_longue_duree_id = lld.name
				INNER JOIN `tabAppartement` a ON lld.appartement_id = a.name
				WHERE a.proprietaire_id = %s
					AND (pp.date_paiement IS NULL OR pp.date_paiement BETWEEN %s AND %s)
				
				UNION ALL
				
				-- Paiements directs locations longue durée
				SELECT pp.* FROM `tabPaiement Propriétaire` pp
				INNER JOIN `tabLocation Longue Duree` lld ON pp.location_longue_duree_id = lld.name
				INNER JOIN `tabAppartement` a ON lld.appartement_id = a.name
				WHERE a.proprietaire_id = %s
					AND pp.mensualite_id IS NULL
					AND (pp.date_paiement IS NULL OR pp.date_paiement BETWEEN %s AND %s)
				
				UNION ALL
				
				-- Paiements locations courte durée
				SELECT pp.* FROM `tabPaiement Propriétaire` pp
				INNER JOIN `tabLocation Courte Duree` lcd ON pp.location_courte_duree_id = lcd.name
				INNER JOIN `tabAppartement` a ON lcd.appartement_id = a.name
				WHERE a.proprietaire_id = %s
					AND (pp.date_paiement IS NULL OR pp.date_paiement BETWEEN %s AND %s)
			) as all_payments
		""", (proprietaire_id, start_date, end_date, proprietaire_id, start_date, end_date, proprietaire_id, start_date, end_date), as_dict=True)
		
		# Combine les résultats
		if base_stats and payment_stats:
			metrics = [{
				**base_stats[0],
				**(payment_stats[0] if payment_stats[0].get('nombre_versements') else {
					'total_verse': 0, 'total_net_verse': 0, 'montant_moyen_versement': 0,
					'nombre_versements': 0, 'montant_paye': 0, 'versements_payes': 0,
					'versements_en_attente': 0, 'versements_rejetes': 0
				})
			}]
		else:
			metrics = []
		
		if metrics:
			metric = metrics[0]
			metric['taux_paiement'] = (metric.versements_payes / metric.nombre_versements * 100) if metric.nombre_versements > 0 else 0
			metric['taux_rejet'] = (metric.versements_rejetes / metric.nombre_versements * 100) if metric.nombre_versements > 0 else 0
			return metric
		
		return {}
	
	except Exception as e:
		frappe.log_error(f"Erreur lors du calcul des métriques propriétaire: {str(e)}")
		return {}


def update_location_courte_duree_payment_status(doc):
	"""Met à jour le statut des paiements de la location courte durée"""
	try:
		if doc.location_courte_duree_id:
			# Déclencher la mise à jour de la location courte durée
			# Cela va automatiquement appeler on_update qui calculera le statut des paiements
			frappe.db.set_value("Location Courte Duree", doc.location_courte_duree_id, "modified", frappe.utils.now())
			
	except Exception as e:
		frappe.log_error(f"Erreur lors de la mise à jour du statut des paiements de la location courte durée: {str(e)}")
