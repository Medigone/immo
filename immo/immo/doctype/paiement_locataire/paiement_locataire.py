# Copyright (c) 2024, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class PaiementLocataire(Document):
	"""Doctype pour gérer les paiements des locataires"""
	
	def validate(self):
		"""Validation des données du paiement"""
		self.validate_location_reference()
		self.validate_amount()
		self.validate_payment_date()
		self.validate_status_change()
	
	def validate_location_reference(self):
		"""Valide qu'au moins une référence de location est fournie"""
		if not self.mensualite_id and not self.location_longue_duree_id and not self.location_courte_duree_id:
			frappe.throw(_("Au moins une référence (Mensualité, Location Longue Durée ou Location Courte Durée) est obligatoire"))
		
		# Vérifie que les références existent et sont valides
		if self.mensualite_id:
			mensualite = frappe.get_doc("Mensualite", self.mensualite_id)
			if not self.location_longue_duree_id:
				self.location_longue_duree_id = mensualite.location_longue_duree_id
		
		if self.location_longue_duree_id:
			location = frappe.get_doc("Location Longue Durée", self.location_longue_duree_id)
			if location.statut not in ["Actif", "Terminé"]:
				frappe.throw(_("La location longue durée doit être active ou terminée"))
		
		if self.location_courte_duree_id:
			location = frappe.get_doc("Location Courte Durée", self.location_courte_duree_id)
			if location.statut not in ["Confirmé", "Terminé"]:
				frappe.throw(_("La location courte durée doit être confirmée ou terminée"))
	
	def validate_amount(self):
		"""Valide le montant du paiement"""
		if self.montant is not None and self.montant <= 0:
			frappe.throw(_("Le montant du paiement doit être positif"))
		
		if self.frais_transaction is not None and self.frais_transaction < 0:
			frappe.throw(_("Les frais de transaction ne peuvent pas être négatifs"))
	
	def validate_payment_date(self):
		"""Valide la date de paiement"""
		if self.date_paiement:
			# La date de paiement ne peut pas être dans le futur
			today = frappe.utils.nowdate()
			if self.date_paiement > today:
				frappe.throw(_("La date de paiement ne peut pas être dans le futur"))
	
	def validate_status_change(self):
		"""Valide les changements de statut"""
		if self.is_new():
			return
		
		old_doc = self.get_doc_before_save()
		if old_doc and old_doc.statut == "Confirmé" and self.statut != "Confirmé":
			frappe.throw(_("Un paiement confirmé ne peut pas être modifié"))
	
	def before_save(self):
		"""Actions avant sauvegarde"""
		# Calcule le montant net
		self.calculate_net_amount()
		# Met à jour les informations de validation
		self.update_validation_info()
	
	def calculate_net_amount(self):
		"""Calcule le montant net après déduction des frais"""
		if self.montant is not None:
			frais = self.frais_transaction or 0
			self.montant_net = self.montant - frais
	
	def update_validation_info(self):
		"""Met à jour les informations de validation"""
		if self.statut == "Confirmé" and not self.date_validation:
			self.date_validation = frappe.utils.now()
			self.valide_par = frappe.session.user
	
	def on_update(self):
		"""Actions après mise à jour"""
		# Met à jour le statut de la mensualité si applicable
		if self.mensualite_id and self.statut == "Confirmé":
			self.update_mensualite_status()
	
	def update_mensualite_status(self):
		"""Met à jour le statut de paiement de la mensualité"""
		mensualite = frappe.get_doc("Mensualite", self.mensualite_id)
		if self.type_paiement == "Loyer mensuel":
			mensualite.statut_paiement_locataire = "Payé"
			mensualite.date_paiement_locataire = self.date_paiement
			mensualite.methode_paiement_locataire = self.methode_paiement
			mensualite.reference_paiement_locataire = self.reference_paiement
			mensualite.save()
	
	def on_cancel(self):
		"""Actions lors de l'annulation"""
		# Remet à jour le statut de la mensualité
		if self.mensualite_id:
			mensualite = frappe.get_doc("Mensualite", self.mensualite_id)
			if self.type_paiement == "Loyer mensuel":
				mensualite.statut_paiement_locataire = "En attente"
				mensualite.date_paiement_locataire = None
				mensualite.methode_paiement_locataire = None
				mensualite.reference_paiement_locataire = None
				mensualite.save()
	
	@frappe.whitelist()
	def confirm_payment(self):
		"""Confirme le paiement"""
		if self.statut == "Confirmé":
			frappe.throw(_("Le paiement est déjà confirmé"))
		
		self.statut = "Confirmé"
		self.save()
		
		return {
			"message": _("Paiement confirmé avec succès"),
			"paiement_id": self.name
		}
	
	@frappe.whitelist()
	def reject_payment(self, reason=None):
		"""Rejette le paiement"""
		if self.statut == "Confirmé":
			frappe.throw(_("Un paiement confirmé ne peut pas être rejeté"))
		
		self.statut = "Rejeté"
		if reason:
			self.commentaires = (self.commentaires or "") + f"\nRejeté: {reason}"
		self.save()
		
		return {
			"message": _("Paiement rejeté"),
			"paiement_id": self.name
		}
	
	@frappe.whitelist()
	def get_payment_details(self):
		"""Récupère les détails complets du paiement"""
		details = {
			"paiement": {
				"name": self.name,
				"type_paiement": self.type_paiement,
				"montant": self.montant,
				"montant_net": self.montant_net,
				"frais_transaction": self.frais_transaction,
				"date_paiement": self.date_paiement,
				"methode_paiement": self.methode_paiement,
				"statut": self.statut,
				"reference_paiement": self.reference_paiement
			}
		}
		
		# Ajoute les détails de la location
		if self.location_longue_duree_id:
			location = frappe.get_doc("Location Longue Durée", self.location_longue_duree_id)
			appartement = frappe.get_doc("Appartement", location.appartement_id)
			details["location_longue_duree"] = {
				"locataire_nom": location.locataire_nom,
				"locataire_email": location.locataire_email,
				"appartement_adresse": appartement.adresse_complete,
				"loyer_mensuel": location.loyer_mensuel_locataire
			}
		
		if self.location_courte_duree_id:
			location = frappe.get_doc("Location Courte Durée", self.location_courte_duree_id)
			appartement = frappe.get_doc("Appartement", location.appartement_id)
			details["location_courte_duree"] = {
				"locataire_nom": location.locataire_nom,
				"locataire_email": location.locataire_email,
				"appartement_adresse": appartement.adresse_complete,
				"date_debut": location.date_debut,
				"date_fin": location.date_fin,
				"montant_total": location.montant_total_locataire
			}
		
		if self.mensualite_id:
			mensualite = frappe.get_doc("Mensualite", self.mensualite_id)
			details["mensualite"] = {
				"mois_annee": mensualite.mois_annee,
				"date_echeance": mensualite.date_echeance,
				"montant_loyer": mensualite.montant_loyer_locataire
			}
		
		return details
	
	@frappe.whitelist()
	def send_payment_confirmation(self):
		"""Envoie une confirmation de paiement au locataire"""
		if self.statut != "Confirmé":
			frappe.throw(_("Le paiement doit être confirmé pour envoyer une confirmation"))
		
		# Récupère l'email du locataire
		locataire_email = None
		locataire_nom = None
		
		if self.location_longue_duree_id:
			location = frappe.get_doc("Location Longue Durée", self.location_longue_duree_id)
			locataire_email = location.locataire_email
			locataire_nom = location.locataire_nom
		elif self.location_courte_duree_id:
			location = frappe.get_doc("Location Courte Durée", self.location_courte_duree_id)
			locataire_email = location.locataire_email
			locataire_nom = location.locataire_nom
		
		if locataire_email:
			frappe.sendmail(
				recipients=[locataire_email],
				subject=f"Confirmation de paiement - {self.name}",
				message=f"""
				Bonjour {locataire_nom},
				
				Nous confirmons la réception de votre paiement :
				
				- Référence : {self.name}
				- Type : {self.type_paiement}
				- Montant : {self.montant}€
				- Date : {self.date_paiement}
				- Méthode : {self.methode_paiement}
				
				Merci pour votre paiement.
				
				Cordialement,
				L'équipe de gestion immobilière
				"""
			)
			
			return {"message": _("Confirmation envoyée à {0}").format(locataire_email)}
		else:
			return {"message": _("Aucun email de locataire trouvé")}
	
	@frappe.whitelist()
	def calculate_payment_statistics(self, start_date=None, end_date=None):
		"""Calcule les statistiques de paiement pour une période"""
		filters = {"statut": "Confirmé"}
		
		if start_date:
			filters["date_paiement"] = [">=", start_date]
		if end_date:
			if "date_paiement" in filters:
				filters["date_paiement"] = ["between", [start_date, end_date]]
			else:
				filters["date_paiement"] = ["<=", end_date]
		
		paiements = frappe.get_all(
			"Paiement Locataire",
			filters=filters,
			fields=["montant", "montant_net", "frais_transaction", "type_paiement", "methode_paiement"]
		)
		
		total_montant = sum(p.montant for p in paiements)
		total_net = sum(p.montant_net for p in paiements)
		total_frais = sum(p.frais_transaction or 0 for p in paiements)
		
		# Répartition par type de paiement
		par_type = {}
		for p in paiements:
			if p.type_paiement not in par_type:
				par_type[p.type_paiement] = {"count": 0, "montant": 0}
			par_type[p.type_paiement]["count"] += 1
			par_type[p.type_paiement]["montant"] += p.montant
		
		# Répartition par méthode de paiement
		par_methode = {}
		for p in paiements:
			if p.methode_paiement not in par_methode:
				par_methode[p.methode_paiement] = {"count": 0, "montant": 0}
			par_methode[p.methode_paiement]["count"] += 1
			par_methode[p.methode_paiement]["montant"] += p.montant
		
		return {
			"periode": {"debut": start_date, "fin": end_date},
			"total_paiements": len(paiements),
			"montant_total": total_montant,
			"montant_net_total": total_net,
			"frais_total": total_frais,
			"repartition_par_type": par_type,
			"repartition_par_methode": par_methode
		}