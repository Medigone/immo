# Copyright (c) 2024, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from datetime import datetime
import calendar


class Mensualite(Document):
	"""Doctype pour gérer les mensualités des locations longue durée"""
	
	def validate(self):
		"""Validation des données de la mensualité"""
		self.validate_location_status()
		self.validate_amounts()
		self.validate_payment_details()
		self.validate_month_year_format()
	
	def validate_location_status(self):
		"""Valide que la location longue durée existe et est active"""
		if self.location_longue_duree_id:
			location = frappe.get_doc("Location Longue Durée", self.location_longue_duree_id)
			if location.statut != "Actif":
				frappe.throw(_("La location doit être active pour créer des mensualités"))
	
	def validate_amounts(self):
		"""Valide les montants des loyers"""
		if self.montant_loyer_locataire is not None and self.montant_loyer_locataire <= 0:
			frappe.throw(_("Le montant du loyer locataire doit être positif"))
		
		if self.montant_loyer_proprietaire is not None and self.montant_loyer_proprietaire <= 0:
			frappe.throw(_("Le montant du loyer propriétaire doit être positif"))
		
		if (self.montant_loyer_locataire and self.montant_loyer_proprietaire and 
			self.montant_loyer_proprietaire >= self.montant_loyer_locataire):
			frappe.throw(_("Le loyer propriétaire doit être inférieur au loyer locataire"))
	
	def validate_payment_details(self):
		"""Valide les détails de paiement"""
		if self.statut_paiement_locataire == "Payé":
			if not self.date_paiement_locataire:
				frappe.throw(_("La date de paiement locataire est obligatoire"))
			if not self.methode_paiement_locataire:
				frappe.throw(_("La méthode de paiement locataire est obligatoire"))
		
		if self.statut_paiement_proprietaire == "Payé":
			if not self.date_paiement_proprietaire:
				frappe.throw(_("La date de paiement propriétaire est obligatoire"))
			if not self.methode_paiement_proprietaire:
				frappe.throw(_("La méthode de paiement propriétaire est obligatoire"))
	
	def validate_month_year_format(self):
		"""Valide le format mois/année"""
		if self.mois_annee:
			try:
				# Format attendu: MM/YYYY ou MM-YYYY
				if '/' in self.mois_annee:
					mois, annee = self.mois_annee.split('/')
				elif '-' in self.mois_annee:
					mois, annee = self.mois_annee.split('-')
				else:
					raise ValueError("Format invalide")
				
				mois = int(mois)
				annee = int(annee)
				
				if mois < 1 or mois > 12:
					raise ValueError("Mois invalide")
				if annee < 2020 or annee > 2050:
					raise ValueError("Année invalide")
				
			except ValueError:
				frappe.throw(_("Format mois/année invalide. Utilisez MM/YYYY ou MM-YYYY"))
	
	def before_save(self):
		"""Actions avant sauvegarde"""
		# Calcule la marge mensuelle
		self.calculate_monthly_margin()
		# Normalise le format mois/année
		self.normalize_month_year()
	
	def calculate_monthly_margin(self):
		"""Calcule la marge mensuelle"""
		if self.montant_loyer_locataire and self.montant_loyer_proprietaire:
			self.marge_mensuelle = self.montant_loyer_locataire - self.montant_loyer_proprietaire
	
	def normalize_month_year(self):
		"""Normalise le format mois/année en MM/YYYY"""
		if self.mois_annee:
			try:
				if '/' in self.mois_annee:
					mois, annee = self.mois_annee.split('/')
				elif '-' in self.mois_annee:
					mois, annee = self.mois_annee.split('-')
				
				mois = int(mois)
				annee = int(annee)
				
				self.mois_annee = f"{mois:02d}/{annee}"
			except:
				pass
	
	def on_update(self):
		"""Actions après mise à jour"""
		# Crée automatiquement les paiements si les statuts sont "Payé"
		self.create_payment_records()
	
	def create_payment_records(self):
		"""Crée les enregistrements de paiement automatiquement"""
		# Paiement locataire
		if (self.statut_paiement_locataire == "Payé" and 
			self.date_paiement_locataire and 
			not self.has_tenant_payment()):
			
			paiement_locataire = frappe.get_doc({
				"doctype": "Paiement Locataire",
				"mensualite_id": self.name,
				"location_longue_duree_id": self.location_longue_duree_id,
				"montant": self.montant_loyer_locataire,
				"date_paiement": self.date_paiement_locataire,
				"methode_paiement": self.methode_paiement_locataire,
				"reference_paiement": self.reference_paiement_locataire,
				"statut": "Confirmé",
				"type_paiement": "Loyer mensuel"
			})
			paiement_locataire.insert()
		
		# Paiement propriétaire
		if (self.statut_paiement_proprietaire == "Payé" and 
			self.date_paiement_proprietaire and 
			not self.has_owner_payment()):
			
			paiement_proprietaire = frappe.get_doc({
				"doctype": "Paiement Propriétaire",
				"mensualite_id": self.name,
				"location_longue_duree_id": self.location_longue_duree_id,
				"montant": self.montant_loyer_proprietaire,
				"date_paiement": self.date_paiement_proprietaire,
				"methode_paiement": self.methode_paiement_proprietaire,
				"reference_paiement": self.reference_paiement_proprietaire,
				"statut": "Confirmé",
				"type_paiement": "Loyer mensuel"
			})
			paiement_proprietaire.insert()
	
	def has_tenant_payment(self):
		"""Vérifie si un paiement locataire existe déjà"""
		return frappe.db.exists("Paiement Locataire", {"mensualite_id": self.name})
	
	def has_owner_payment(self):
		"""Vérifie si un paiement propriétaire existe déjà"""
		return frappe.db.exists("Paiement Propriétaire", {"mensualite_id": self.name})
	
	@frappe.whitelist()
	def mark_tenant_payment_received(self, date_paiement, methode_paiement, reference_paiement=None):
		"""Marque le paiement locataire comme reçu"""
		self.statut_paiement_locataire = "Payé"
		self.date_paiement_locataire = date_paiement
		self.methode_paiement_locataire = methode_paiement
		if reference_paiement:
			self.reference_paiement_locataire = reference_paiement
		self.save()
		
		return {"message": _("Paiement locataire marqué comme reçu")}
	
	@frappe.whitelist()
	def mark_owner_payment_sent(self, date_paiement, methode_paiement, reference_paiement=None):
		"""Marque le paiement propriétaire comme envoyé"""
		self.statut_paiement_proprietaire = "Payé"
		self.date_paiement_proprietaire = date_paiement
		self.methode_paiement_proprietaire = methode_paiement
		if reference_paiement:
			self.reference_paiement_proprietaire = reference_paiement
		self.save()
		
		return {"message": _("Paiement propriétaire marqué comme envoyé")}
	
	@frappe.whitelist()
	def get_payment_summary(self):
		"""Récupère un résumé des paiements"""
		location = frappe.get_doc("Location Longue Durée", self.location_longue_duree_id)
		appartement = frappe.get_doc("Appartement", location.appartement_id)
		proprietaire = frappe.get_doc("Propriétaire", appartement.proprietaire_id)
		
		return {
			"mensualite": {
				"name": self.name,
				"mois_annee": self.mois_annee,
				"date_echeance": self.date_echeance,
				"marge_mensuelle": self.marge_mensuelle
			},
			"locataire": {
				"nom": location.locataire_nom,
				"email": location.locataire_email,
				"montant_loyer": self.montant_loyer_locataire,
				"statut_paiement": self.statut_paiement_locataire,
				"date_paiement": self.date_paiement_locataire
			},
			"proprietaire": {
				"nom": proprietaire.nom_complet,
				"email": proprietaire.email,
				"montant_loyer": self.montant_loyer_proprietaire,
				"statut_paiement": self.statut_paiement_proprietaire,
				"date_paiement": self.date_paiement_proprietaire
			},
			"appartement": {
				"adresse": appartement.adresse_complete,
				"nombre_pieces": appartement.nombre_pieces
			}
		}
	
	@frappe.whitelist()
	def check_overdue_status(self):
		"""Vérifie et met à jour le statut en retard"""
		today = frappe.utils.nowdate()
		
		# Vérifie le paiement locataire
		if (self.statut_paiement_locataire == "En attente" and 
			self.date_echeance and 
			self.date_echeance < today):
			self.statut_paiement_locataire = "En retard"
		
		# Vérifie le paiement propriétaire (généralement payé après réception du locataire)
		if (self.statut_paiement_proprietaire == "En attente" and 
			self.statut_paiement_locataire == "Payé" and 
			self.date_paiement_locataire):
			# Le propriétaire devrait être payé dans les 5 jours après réception
			expected_payment_date = frappe.utils.add_days(self.date_paiement_locataire, 5)
			if expected_payment_date < today:
				self.statut_paiement_proprietaire = "En retard"
		
		self.save()
		
		return {
			"statut_locataire": self.statut_paiement_locataire,
			"statut_proprietaire": self.statut_paiement_proprietaire
		}
	
	@frappe.whitelist()
	def send_payment_reminders(self):
		"""Envoie des rappels de paiement"""
		location = frappe.get_doc("Location Longue Durée", self.location_longue_duree_id)
		appartement = frappe.get_doc("Appartement", location.appartement_id)
		proprietaire = frappe.get_doc("Propriétaire", appartement.proprietaire_id)
		
		messages = []
		
		# Rappel locataire
		if self.statut_paiement_locataire in ["En attente", "En retard"] and location.locataire_email:
			frappe.sendmail(
				recipients=[location.locataire_email],
				subject=f"Rappel de paiement - {self.mois_annee}",
				message=f"""
				Bonjour {location.locataire_nom},
				
				Nous vous rappelons que le loyer de {self.montant_loyer_locataire}€ 
				pour le mois de {self.mois_annee} était dû le {self.date_echeance}.
				
				Merci de procéder au paiement dans les plus brefs délais.
				
				Cordialement
				"""
			)
			messages.append(f"Rappel envoyé à {location.locataire_email}")
		
		return {"messages": messages}