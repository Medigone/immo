# Copyright (c) 2024, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class PaiementProprietaire(Document):
	"""Doctype pour gérer les paiements aux propriétaires"""
	
	def validate(self):
		"""Validation des données du paiement"""
		self.validate_location_reference()
		self.validate_amount()
		self.validate_payment_date()
		self.validate_status_change()
	
	def validate_location_reference(self):
		"""Valide qu'au moins une référence de location est fournie"""
		if not self.mensualite_id and not self.location_longue_duree_id and not self.location_courte_duree_id:
			frappe.throw(_("Au moins une référence (Mensualité, Location Longue Duree ou Location Courte Duree) est obligatoire"))
		
		# Vérifie que les références existent et sont valides
		if self.mensualite_id:
			mensualite = frappe.get_doc("Mensualite", self.mensualite_id)
			if not self.location_longue_duree_id:
				self.location_longue_duree_id = mensualite.location_longue_duree_id
		
		if self.location_longue_duree_id:
			location = frappe.get_doc("Location Longue Duree", self.location_longue_duree_id)
		
		if self.location_courte_duree_id:
			location = frappe.get_doc("Location Courte Duree", self.location_courte_duree_id)
	
	def validate_amount(self):
		"""Valide le montant du paiement"""
		if self.montant is not None and self.montant <= 0:
			frappe.throw(_("Le montant du paiement doit être positif"))
	
	def validate_payment_date(self):
		"""Valide la date de paiement"""
		if self.date_paiement:
			# Pour les paiements programmés, la date peut être dans le futur
			if self.status in ["Envoyé", "Reçu"] and self.date_paiement > frappe.utils.nowdate():
				frappe.throw(_("La date de paiement ne peut pas être dans le futur pour un paiement envoyé ou reçu"))
	
	def validate_status_change(self):
		"""Valide les changements de statut"""
		if self.is_new():
			return
		
		old_doc = self.get_doc_before_save()
		if old_doc and old_doc.status == "Reçu" and self.status != "Reçu" and self.status != "Annulé":
			frappe.throw(_("Un paiement reçu ne peut pas être modifié, sauf pour l'annuler"))
	
	def before_save(self):
		"""Actions avant sauvegarde"""
		# Remplit automatiquement les champs appartement et proprietaire
		self.set_appartement_and_proprietaire()
		# Calcule le montant net
		self.calculate_net_amount()
		# Met à jour les informations de validation
		self.update_validation_info()
		# Met à jour la date de création
		if self.is_new():
			self.date_creation = frappe.utils.now()
	
	def set_appartement_and_proprietaire(self):
		"""Remplit automatiquement les champs appartement et proprietaire"""
		appartement_id = None
		
		# Récupère l'appartement selon la référence disponible
		if self.mensualite_id:
			mensualite = frappe.get_doc("Mensualite", self.mensualite_id)
			location = frappe.get_doc("Location Longue Duree", mensualite.location_longue_duree_id)
			appartement_id = location.appartement_id
		elif self.location_longue_duree_id:
			location = frappe.get_doc("Location Longue Duree", self.location_longue_duree_id)
			appartement_id = location.appartement_id
		elif self.location_courte_duree_id:
			location = frappe.get_doc("Location Courte Duree", self.location_courte_duree_id)
			appartement_id = location.appartement_id
		
		if appartement_id:
			self.appartement = appartement_id
			# Récupère le propriétaire de l'appartement
			appartement = frappe.get_doc("Appartement", appartement_id)
			self.proprietaire = appartement.proprietaire_id
	
	def calculate_net_amount(self):
		"""Calcule le montant net après déduction des frais"""
		if self.montant is not None:
			self.montant_net = self.montant
	
	def update_validation_info(self):
		"""Met à jour les informations de validation"""
		if self.status == "Reçu" and not self.date_validation:
			self.date_validation = frappe.utils.now()
			self.valide_par = frappe.session.user
	
	def on_update(self):
		"""Actions après mise à jour"""
		# Met à jour le statut de la mensualité si applicable
		if self.mensualite_id and self.status == "Reçu":
			self.update_mensualite_status()
	
	def update_mensualite_status(self):
		"""Met à jour le statut de paiement de la mensualité (uniquement pour les locations longue durée)"""
		# Ne met à jour la mensualité que si elle existe (locations longue durée)
		if self.mensualite_id and self.type_paiement == "Loyer mensuel":
			mensualite = frappe.get_doc("Mensualite", self.mensualite_id)
			mensualite.statut_paiement_proprietaire = "Payé"
			mensualite.date_paiement_proprietaire = self.date_paiement
			mensualite.methode_paiement_proprietaire = self.methode_paiement
			mensualite.reference_paiement_proprietaire = self.reference_paiement
			mensualite.save()
	
	def on_cancel(self):
		"""Actions lors de l'annulation"""
		# Remet à jour le statut de la mensualité
		if self.mensualite_id:
			mensualite = frappe.get_doc("Mensualite", self.mensualite_id)
			if self.type_paiement == "Loyer mensuel":
				mensualite.statut_paiement_proprietaire = "En attente"
				mensualite.date_paiement_proprietaire = None
				mensualite.methode_paiement_proprietaire = None
				mensualite.reference_paiement_proprietaire = None
				mensualite.save()
	
	@frappe.whitelist()
	def schedule_payment(self, scheduled_date=None):
		"""Programme le paiement pour une date donnée"""
		if self.status in ["Envoyé", "Reçu"]:
			frappe.throw(_("Un paiement envoyé ou reçu ne peut pas être reprogrammé"))
		
		if scheduled_date:
			self.date_paiement = scheduled_date
		self.status = "Programmé"
		self.save()
		
		return {
			"message": _("Paiement programmé pour le {0}").format(self.date_paiement),
			"paiement_id": self.name
		}
	
	@frappe.whitelist()
	def mark_as_sent(self):
		"""Marque le paiement comme envoyé"""
		if self.status == "Reçu":
			frappe.throw(_("Un paiement déjà reçu ne peut pas être marqué comme envoyé"))
		
		self.status = "Envoyé"
		if not self.date_paiement or self.date_paiement > frappe.utils.nowdate():
			self.date_paiement = frappe.utils.nowdate()
		self.save()
		
		return {
			"message": _("Paiement marqué comme envoyé"),
			"paiement_id": self.name
		}
	
	@frappe.whitelist()
	def confirm_receipt(self):
		"""Confirme la réception du paiement par le propriétaire"""
		if self.status == "Reçu":
			frappe.throw(_("Le paiement est déjà marqué comme reçu"))
		
		self.status = "Reçu"
		self.save()
		
		return {
			"message": _("Réception du paiement confirmée"),
			"paiement_id": self.name
		}
	
	@frappe.whitelist()
	def reject_payment(self, reason=None):
		"""Rejette le paiement"""
		if self.status == "Reçu":
			frappe.throw(_("Un paiement reçu ne peut pas être rejeté"))
		
		self.status = "Rejeté"
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
				"date_paiement": self.date_paiement,
				"methode_paiement": self.methode_paiement,
				"status": self.status,
				"reference_paiement": self.reference_paiement
			}
		}
		
		# Ajoute les détails de la location et du propriétaire
		if self.location_longue_duree_id:
			location = frappe.get_doc("Location Longue Duree", self.location_longue_duree_id)
			appartement = frappe.get_doc("Appartement", location.appartement_id)
			proprietaire = frappe.get_doc("Proprietaire", appartement.proprietaire_id)
			details["location_longue_duree"] = {
				"locataire_nom": location.locataire_nom,
				"appartement_adresse": appartement.adresse_complete,
				"loyer_mensuel": location.loyer_mensuel_proprietaire
			}
			details["proprietaire"] = {
				"nom_complet": proprietaire.nom_complet,
				"email": proprietaire.email,
				"telephone": proprietaire.telephone
			}
		
		if self.location_courte_duree_id:
			location = frappe.get_doc("Location Courte Duree", self.location_courte_duree_id)
			appartement = frappe.get_doc("Appartement", location.appartement_id)
			proprietaire = frappe.get_doc("Proprietaire", appartement.proprietaire_id)
			details["location_courte_duree"] = {
				"locataire_nom": location.locataire_nom,
				"appartement_adresse": appartement.adresse_complete,
				"date_debut": location.date_debut,
				"date_fin": location.date_fin,
				"montant_total": location.montant_total_proprietaire
			}
			details["proprietaire"] = {
				"nom_complet": proprietaire.nom_complet,
				"email": proprietaire.email,
				"telephone": proprietaire.telephone
			}
		
		if self.mensualite_id:
			mensualite = frappe.get_doc("Mensualite", self.mensualite_id)
			details["mensualite"] = {
				"mois_annee": mensualite.mois_annee,
				"date_echeance": mensualite.date_echeance,
				"montant_loyer": mensualite.montant_loyer_proprietaire
			}
		
		return details
	
	@frappe.whitelist()
	def send_payment_notification(self):
		"""Envoie une notification de paiement au propriétaire"""
		if self.status not in ["Programmé", "Envoyé"]:
			frappe.throw(_("Le paiement doit être programmé ou envoyé pour envoyer une notification"))
		
		# Récupère l'email du propriétaire
		proprietaire_email = None
		proprietaire_nom = None
		
		if self.location_longue_duree_id:
			location = frappe.get_doc("Location Longue Duree", self.location_longue_duree_id)
			appartement = frappe.get_doc("Appartement", location.appartement_id)
			proprietaire = frappe.get_doc("Proprietaire", appartement.proprietaire_id)
			proprietaire_email = proprietaire.email
			proprietaire_nom = proprietaire.nom_complet
		elif self.location_courte_duree_id:
			location = frappe.get_doc("Location Courte Duree", self.location_courte_duree_id)
			appartement = frappe.get_doc("Appartement", location.appartement_id)
			proprietaire = frappe.get_doc("Proprietaire", appartement.proprietaire_id)
			proprietaire_email = proprietaire.email
			proprietaire_nom = proprietaire.nom_complet
		
		if proprietaire_email:
			subject = f"Notification de paiement - {self.name}"
			if self.status == "Programmé":
				message = f"""
				Bonjour {proprietaire_nom},
				
				Votre paiement a été programmé :
				
				- Référence : {self.name}
				- Type : {self.type_paiement}
				- Montant : {self.montant}€
				- Date prévue : {self.date_paiement}
				- Méthode : {self.methode_paiement}
				
				Vous recevrez une confirmation une fois le paiement effectué.
				
				Cordialement,
				L'équipe de gestion immobilière
				"""
			else:  # Envoyé
				message = f"""
				Bonjour {proprietaire_nom},
				
				Votre paiement a été envoyé :
				
				- Référence : {self.name}
				- Type : {self.type_paiement}
				- Montant : {self.montant}€
				- Date d'envoi : {self.date_paiement}
				- Méthode : {self.methode_paiement}
				- Référence : {self.reference_paiement or 'N/A'}
				
				Veuillez vérifier votre compte et confirmer la réception.
				
				Cordialement,
				L'équipe de gestion immobilière
				"""
			
			frappe.sendmail(
				recipients=[proprietaire_email],
				subject=subject,
				message=message
			)
			
			return {"message": _("Notification envoyée à {0}").format(proprietaire_email)}
		else:
			return {"message": _("Aucun email de propriétaire trouvé")}
	
	@frappe.whitelist()
	def calculate_payment_statistics(self, start_date=None, end_date=None):
		"""Calcule les statistiques de paiement pour une période"""
		filters = {"status": ["in", ["Envoyé", "Reçu"]]}
		
		if start_date:
			filters["date_paiement"] = [">=", start_date]
		if end_date:
			if "date_paiement" in filters:
				filters["date_paiement"] = ["between", [start_date, end_date]]
			else:
				filters["date_paiement"] = ["<=", end_date]
		
		paiements = frappe.get_all(
			"Paiement Propriétaire",
			filters=filters,
			fields=["montant", "montant_net", "type_paiement", "methode_paiement", "status"]
		)
		
		total_montant = sum(p.montant for p in paiements)
		total_net = sum(p.montant_net for p in paiements)
		
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
		
		# Répartition par status
		par_status = {}
		for p in paiements:
			if p.status not in par_status:
				par_status[p.status] = {"count": 0, "montant": 0}
			par_status[p.status]["count"] += 1
			par_status[p.status]["montant"] += p.montant
		
		return {
			"periode": {"debut": start_date, "fin": end_date},
			"total_paiements": len(paiements),
			"montant_total": total_montant,
			"montant_net_total": total_net,
			"repartition_par_type": par_type,
			"repartition_par_methode": par_methode,
			"repartition_par_status": par_status
		}
	
	@frappe.whitelist()
	def get_pending_payments(self, proprietaire_id=None):
		"""Récupère les paiements en attente pour un propriétaire"""
		filters = {"status": ["in", ["En attente", "Programmé"]]}
		
		if proprietaire_id:
			# Récupère les appartements du propriétaire
			appartements = frappe.get_all(
				"Appartement",
				filters={"proprietaire_id": proprietaire_id},
				fields=["name"]
			)
			appartement_ids = [a.name for a in appartements]
			
			# Filtre par les locations de ces appartements
			locations_longues = frappe.get_all(
				"Location Longue Duree",
				filters={"appartement_id": ["in", appartement_ids]},
				fields=["name"]
			)
			locations_courtes = frappe.get_all(
				"Location Courte Duree",
				filters={"appartement_id": ["in", appartement_ids]},
				fields=["name"]
			)
			
			location_longue_ids = [l.name for l in locations_longues]
			location_courte_ids = [l.name for l in locations_courtes]
			
			filters["location_longue_duree_id"] = ["in", location_longue_ids]
			filters["location_courte_duree_id"] = ["in", location_courte_ids]
		
		paiements = frappe.get_all(
			"Paiement Propriétaire",
			filters=filters,
			fields=["name", "type_paiement", "montant", "date_paiement", "status", "location_longue_duree_id", "location_courte_duree_id"],
			order_by="date_paiement asc"
		)
		
		return paiements