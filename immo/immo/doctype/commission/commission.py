# Copyright (c) 2024, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class Commission(Document):
	"""Doctype pour gérer les commissions des référents"""
	
	def validate(self):
		"""Validation des données de la commission"""
		self.validate_referent_status()
		self.validate_location_status()
		self.validate_commission_amount()
		self.validate_payment_details()
	
	def validate_referent_status(self):
		"""Valide que le référent est actif"""
		if self.referent_id:
			referent = frappe.get_doc("Referent", self.referent_id)
			if not referent.actif:
				frappe.throw(_("Le référent {0} n'est pas actif").format(referent.nom_complet))
	
	def validate_location_status(self):
		"""Valide que la location courte durée existe et n'est pas annulée"""
		if self.location_courte_duree_id:
			location = frappe.get_doc("Location Courte Duree", self.location_courte_duree_id)
			if location.statut == "Annulé":
				frappe.throw(_("Impossible de créer une commission pour une location annulée"))
	
	def validate_commission_amount(self):
		"""Valide le montant de la commission"""
		if self.montant_commission is not None and self.montant_commission < 0:
			frappe.throw(_("Le montant de la commission ne peut pas être négatif"))
		
		if self.pourcentage_commission is not None:
			if self.pourcentage_commission < 0 or self.pourcentage_commission > 100:
				frappe.throw(_("Le pourcentage de commission doit être entre 0 et 100"))
	
	def validate_payment_details(self):
		"""Valide les détails de paiement"""
		if self.statut_paiement == "Payé":
			if not self.date_paiement:
				frappe.throw(_("La date de paiement est obligatoire pour un statut 'Payé'"))
			if not self.methode_paiement:
				frappe.throw(_("La méthode de paiement est obligatoire pour un statut 'Payé'"))
	
	def before_save(self):
		"""Actions avant sauvegarde"""
		# Calcule automatiquement le montant si pas défini
		if not self.montant_commission and self.location_courte_duree_id:
			self.calculate_commission_amount()
	
	def calculate_commission_amount(self):
		"""Calcule le montant de la commission basé sur la location"""
		location = frappe.get_doc("Location Courte Duree", self.location_courte_duree_id)
		referent = frappe.get_doc("Referent", self.referent_id)
		
		# Utilise le pourcentage de la commission ou celui par défaut du référent
		percentage = self.pourcentage_commission or referent.pourcentage_commission_defaut
		
		# Calcule la commission sur la marge totale de la location
		if location.marge_totale:
			self.montant_commission = location.marge_totale * (percentage / 100)
			self.pourcentage_commission = percentage
	
	def on_update(self):
		"""Actions après mise à jour"""
		# Met à jour la commission dans la location courte durée
		if self.location_courte_duree_id:
			location = frappe.get_doc("Location Courte Duree", self.location_courte_duree_id)
			location.commission_referent = self.montant_commission
			location.save()
	
	def on_cancel(self):
		"""Actions lors de l'annulation"""
		# Remet à zéro la commission dans la location
		if self.location_courte_duree_id:
			location = frappe.get_doc("Location Courte Duree", self.location_courte_duree_id)
			location.commission_referent = 0
			location.save()
	
	@frappe.whitelist()
	def mark_as_paid(self, date_paiement, methode_paiement, reference_paiement=None):
		"""Marque la commission comme payée"""
		self.statut_paiement = "Payé"
		self.date_paiement = date_paiement
		self.methode_paiement = methode_paiement
		if reference_paiement:
			self.reference_paiement = reference_paiement
		self.save()
		
		return {
			"message": _("Commission marquée comme payée"),
			"commission_id": self.name
		}
	
	@frappe.whitelist()
	def get_commission_details(self):
		"""Récupère les détails complets de la commission"""
		location = frappe.get_doc("Location Courte Duree", self.location_courte_duree_id)
		referent = frappe.get_doc("Referent", self.referent_id)
		appartement = frappe.get_doc("Appartement", location.appartement_id)
		
		return {
			"commission": {
				"name": self.name,
				"montant_commission": self.montant_commission,
				"pourcentage_commission": self.pourcentage_commission,
				"date_creation": self.date_creation,
				"statut_paiement": self.statut_paiement,
				"date_paiement": self.date_paiement,
				"methode_paiement": self.methode_paiement
			},
			"referent": {
				"nom_complet": referent.nom_complet,
				"email": referent.email,
				"telephone": referent.telephone
			},
			"location": {
				"locataire_nom": location.locataire_nom,
				"date_debut": location.date_debut,
				"date_fin": location.date_fin,
				"nombre_nuits": location.nombre_nuits,
				"montant_total_locataire": location.montant_total_locataire,
				"marge_totale": location.marge_totale
			},
			"appartement": {
				"adresse_complete": appartement.adresse_complete,
				"nombre_pieces": appartement.nombre_pieces
			}
		}
	
	@frappe.whitelist()
	def calculate_net_margin_after_commission(self):
		"""Calcule la marge nette après déduction de la commission"""
		location = frappe.get_doc("Location Courte Duree", self.location_courte_duree_id)
		
		marge_brute = location.marge_totale or 0
		commission = self.montant_commission or 0
		marge_nette = marge_brute - commission
		
		return {
			"marge_brute": marge_brute,
			"commission_referent": commission,
			"marge_nette": marge_nette,
			"pourcentage_commission": (commission / marge_brute * 100) if marge_brute > 0 else 0
		}
	
	@frappe.whitelist()
	def send_payment_notification(self):
		"""Envoie une notification de paiement au référent"""
		if self.statut_paiement != "Payé":
			frappe.throw(_("La commission doit être marquée comme payée"))
		
		referent = frappe.get_doc("Referent", self.referent_id)
		
		if referent.email:
			# Envoie un email de notification
			frappe.sendmail(
				recipients=[referent.email],
				subject=f"Paiement de commission - {self.name}",
				message=f"""
				Bonjour {referent.nom_complet},
				
				Votre commission {self.name} d'un montant de {self.montant_commission}€ 
				a été payée le {self.date_paiement} par {self.methode_paiement}.
				
				Référence de paiement: {self.reference_paiement or 'N/A'}
				
				Cordialement,
				L'équipe de gestion immobilière
				"""
			)
			
			return {"message": _("Notification envoyée à {0}").format(referent.email)}
		else:
			return {"message": _("Aucun email configuré pour le référent")}