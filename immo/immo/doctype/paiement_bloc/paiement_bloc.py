# Copyright (c) 2024, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, flt
from datetime import datetime


class PaiementBloc(Document):
	"""DocType pour gérer les paiements aux propriétaires dans le cadre des locations en bloc."""
	
	def validate(self):
		"""Validation des données avant sauvegarde."""
		self.validate_location_bloc()
		self.validate_montant()
		self.validate_proprietaire_consistency()
		self.set_appartement_from_bloc()
		self.set_timestamps()
	
	def validate_location_bloc(self):
		"""Valide que la location bloc existe."""
		if not self.location_bloc_id:
			frappe.throw("La location bloc est obligatoire")
		
		# Vérifier que la location bloc existe
		if not frappe.db.exists("Location Bloc", self.location_bloc_id):
			frappe.throw("La location bloc spécifiée n'existe pas")
	
	def validate_montant(self):
		"""Valide que le montant est positif et cohérent."""
		if not self.montant_paiement or flt(self.montant_paiement) <= 0:
			frappe.throw("Le montant du paiement doit être positif")
		
		# Vérifier que le total des paiements ne dépasse pas le montant du bloc
		location_bloc = frappe.get_doc("Location Bloc", self.location_bloc_id)
		total_paiements = frappe.db.sql("""
			SELECT COALESCE(SUM(montant_paiement), 0)
			FROM `tabPaiement Bloc`
			WHERE location_bloc_id = %s
			AND name != %s
		""", (self.location_bloc_id, self.name or ''))[0][0] or 0
		
		total_avec_nouveau = flt(total_paiements) + flt(self.montant_paiement)
		if total_avec_nouveau > flt(location_bloc.montant_total_proprietaire):
			frappe.throw(f"Le total des paiements ({total_avec_nouveau}) dépasse le montant du bloc ({location_bloc.montant_total_proprietaire})")
	
	def validate_proprietaire_consistency(self):
		"""Valide que le propriétaire correspond à celui de la location bloc."""
		if self.location_bloc_id and self.proprietaire_id:
			location_bloc = frappe.get_doc("Location Bloc", self.location_bloc_id)
			if location_bloc.proprietaire_id != self.proprietaire_id:
				frappe.throw("Le propriétaire doit correspondre à celui de la location bloc")
	
	def set_appartement_from_bloc(self):
		"""Récupère l'appartement depuis la location bloc."""
		if self.location_bloc_id:
			location_bloc = frappe.get_doc("Location Bloc", self.location_bloc_id)
			self.appartement_id = location_bloc.appartement_id
	
	def set_timestamps(self):
		"""Met à jour les timestamps."""
		if self.is_new():
			self.date_creation = datetime.now()
		self.date_modification = datetime.now()
	
	def on_update(self):
		"""Actions après mise à jour du document."""
		from immo.hooks_handlers.paiement_bloc import update_location_bloc_payment_status
		update_location_bloc_payment_status(self)
		self.send_payment_notification()
	
	def on_cancel(self):
		"""Actions lors de l'annulation."""
		self.update_location_bloc_status()
	
	def update_location_bloc_status(self):
		"""Met à jour le statut de la location bloc selon les paiements."""
		try:
			if not self.location_bloc_id:
				return
			
			location_bloc = frappe.get_doc("Location Bloc", self.location_bloc_id)
			
			# Calculer le total payé
			total_paye = frappe.db.sql("""
				SELECT COALESCE(SUM(montant_paiement), 0)
				FROM `tabPaiement Bloc`
				WHERE location_bloc_id = %s
			""", (self.location_bloc_id,))[0][0] or 0
			
			# Déterminer le nouveau statut
			new_status = location_bloc.statut
			if flt(total_paye) >= flt(location_bloc.montant_total_proprietaire):
				if location_bloc.statut == "Réservé":
					new_status = "Confirmé"
			elif flt(total_paye) > 0:
				if location_bloc.statut == "Réservé":
					new_status = "Confirmé"  # Paiement partiel confirme la réservation
			
			# Mettre à jour les métriques de paiement
			location_bloc.montant_total_paye = flt(total_paye)
			location_bloc.solde_restant = flt(location_bloc.montant_total_proprietaire) - flt(total_paye)
			location_bloc.pourcentage_paye = (flt(total_paye) / flt(location_bloc.montant_total_proprietaire) * 100) if flt(location_bloc.montant_total_proprietaire) > 0 else 0
			
			# Sauvegarder les modifications
			location_bloc.save()
			
		except Exception as e:
			frappe.log_error(f"Erreur lors de la mise à jour du statut Location Bloc {self.location_bloc_id}: {str(e)}")
	
	def send_payment_notification(self):
		"""Envoie une notification de paiement."""
		try:
			# Envoyer notification pour tous les paiements créés
			if True:
				# Notification au propriétaire
				proprietaire = frappe.get_doc("Proprietaire", self.proprietaire_id)
				if proprietaire.email:
					frappe.sendmail(
						recipients=[proprietaire.email],
						subject=f"Paiement reçu - Location Bloc {self.location_bloc_id}",
						message=f"""
						Bonjour {proprietaire.nom_complet},
						
						Nous vous confirmons la réception de votre paiement:
						- Montant: {self.montant_paiement} €
						- Date: {self.date_paiement}
						- Référence: {self.reference_paiement or 'N/A'}
						- Location Bloc: {self.location_bloc_id}
						
						Cordialement,
						L'équipe de gestion
						"""
					)
			
				# Notification interne
				frappe.publish_realtime(
					"payment_notification",
					{
						"type": "paiement_bloc",
						"message": f"Paiement bloc reçu: {self.montant_paiement}€ pour {self.location_bloc_id}",
						"paiement_id": self.name
					}
				)
			
		except Exception as e:
			frappe.log_error(f"Erreur lors de l'envoi de notification pour Paiement Bloc {self.name}: {str(e)}")
	
	@frappe.whitelist()
	def get_remaining_amount(self):
		"""Retourne le montant restant à payer pour la location bloc."""
		if not self.location_bloc_id:
			return 0
		
		location_bloc = frappe.get_doc("Location Bloc", self.location_bloc_id)
		total_paye = frappe.db.sql("""
			SELECT COALESCE(SUM(montant_paiement), 0)
			FROM `tabPaiement Bloc`
			WHERE location_bloc_id = %s
		""", (self.location_bloc_id,))[0][0] or 0
		
		return flt(location_bloc.montant_total_proprietaire) - flt(total_paye)
	
	@frappe.whitelist()
	def validate_payment_schedule(self):
		"""Valide l'échéancier de paiement pour les paiements échelonnés."""
		if self.type_paiement == "Échelonné":
			# Logique pour valider l'échéancier
			# À implémenter selon les besoins spécifiques
			pass
		
		return True