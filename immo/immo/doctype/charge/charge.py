# Copyright (c) 2024, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class Charge(Document):
	"""Doctype pour gérer les charges et dépenses immobilières"""
	
	def validate(self):
		"""Validation des données de la charge"""
		self.validate_appartement()
		self.validate_amount()
		self.validate_repartition()
		self.validate_payment_details()
		self.validate_date()
	
	def validate_appartement(self):
		"""Valide que l'appartement existe et est valide"""
		if not self.appartement_id:
			frappe.throw(_("L'appartement est obligatoire"))
		
		appartement = frappe.get_doc("Appartement", self.appartement_id)
		if not appartement:
			frappe.throw(_("L'appartement spécifié n'existe pas"))
		
		# Vérifie la cohérence avec les locations
		if self.location_longue_duree_id:
			location = frappe.get_doc("Location Longue Duree", self.location_longue_duree_id)
			if location.appartement_id != self.appartement_id:
				frappe.throw(_("La location longue durée ne correspond pas à l'appartement sélectionné"))
		
		if self.location_courte_duree_id:
			location = frappe.get_doc("Location Courte Duree", self.location_courte_duree_id)
			if location.appartement_id != self.appartement_id:
				frappe.throw(_("La location courte duree ne correspond pas à l'appartement sélectionné"))
	
	def validate_amount(self):
		"""Valide le montant de la charge"""
		if self.montant is not None and self.montant <= 0:
			frappe.throw(_("Le montant de la charge doit être positif"))
	
	def validate_repartition(self):
		"""Valide la répartition des charges"""
		if self.repartition_locataire is None:
			self.repartition_locataire = 0
		if self.repartition_proprietaire is None:
			self.repartition_proprietaire = 100
		
		# Convert to float to handle string values from form
		try:
			repartition_locataire = float(self.repartition_locataire or 0)
			repartition_proprietaire = float(self.repartition_proprietaire or 100)
		except (ValueError, TypeError):
			frappe.throw(_("Les valeurs de répartition doivent être numériques"))
		
		# Update the actual values
		self.repartition_locataire = repartition_locataire
		self.repartition_proprietaire = repartition_proprietaire
		
		if repartition_locataire < 0 or repartition_locataire > 100:
			frappe.throw(_("La répartition locataire doit être entre 0 et 100%"))
		
		if repartition_proprietaire < 0 or repartition_proprietaire > 100:
			frappe.throw(_("La répartition propriétaire doit être entre 0 et 100%"))
		
		total_repartition = repartition_locataire + repartition_proprietaire
		if abs(total_repartition - 100) > 0.01:  # Tolérance pour les erreurs d'arrondi
			frappe.throw(_("La somme des répartitions doit être égale à 100%"))
	
	def validate_payment_details(self):
		"""Valide les détails de paiement selon le statut"""
		if self.status == "Payée":
			if not self.date_paiement:
				frappe.throw(_("La date de paiement est obligatoire pour une charge payée"))
			if not self.methode_paiement:
				frappe.throw(_("La méthode de paiement est obligatoire pour une charge payée"))
	
	def validate_date(self):
		"""Valide les dates"""
		today = frappe.utils.getdate(frappe.utils.nowdate())
		
		if self.date_charge and frappe.utils.getdate(self.date_charge) > today:
			frappe.throw(_("La date de la charge ne peut pas être dans le futur"))
		
		if self.date_paiement and frappe.utils.getdate(self.date_paiement) > today:
			frappe.throw(_("La date de paiement ne peut pas être dans le futur"))
	
	def before_save(self):
		"""Actions avant sauvegarde"""
		# Calcule les montants par partie
		self.calculate_amounts()
		# Met à jour les informations de création
		if self.is_new():
			self.date_creation = frappe.utils.now()
			self.cree_par = frappe.session.user
	
	def calculate_amounts(self):
		"""Calcule les montants pour le locataire et le propriétaire"""
		if self.montant is not None:
			self.montant_locataire = self.montant * (self.repartition_locataire or 0) / 100
			self.montant_proprietaire = self.montant * (self.repartition_proprietaire or 100) / 100
	
	def on_update(self):
		"""Actions après mise à jour"""
		# Met à jour les marges des locations si nécessaire
		if self.status == "Validée":
			self.update_location_margins()
	
	def update_location_margins(self):
		"""Met à jour les marges des locations concernées"""
		# Pour les locations longue durée, met à jour la mensualité courante
		if self.location_longue_duree_id and self.montant_locataire > 0:
			# Trouve la mensualité du mois de la charge
			mois_charge = frappe.utils.formatdate(self.date_charge, "MM/yyyy")
			mensualites = frappe.get_all(
				"Mensualite",
				filters={
					"location_longue_duree_id": self.location_longue_duree_id,
					"mois_annee": mois_charge
				},
				fields=["name"]
			)
			
			if mensualites:
				mensualite = frappe.get_doc("Mensualite", mensualites[0].name)
				# Ajoute la charge aux charges locatives
				mensualite.charges_locatives = (mensualite.charges_locatives or 0) + self.montant_locataire
				mensualite.save()
	
	@frappe.whitelist()
	def validate_charge(self):
		"""Valide la charge"""
		if self.status == "Validée":
			frappe.throw(_("La charge est déjà validée"))
		
		self.status = "Validée"
		self.save()
		
		return {
			"message": _("Charge validée avec succès"),
			"charge_id": self.name
		}
	
	@frappe.whitelist()
	def mark_as_paid(self, payment_date=None, payment_method=None, payment_reference=None):
		"""Marque la charge comme payée"""
		if self.status == "Payée":
			frappe.throw(_("La charge est déjà marquée comme payée"))
		
		if self.status != "Validée":
			frappe.throw(_("La charge doit être validée avant d'être marquée comme payée"))
		
		self.status = "Payée"
		self.date_paiement = payment_date or frappe.utils.nowdate()
		self.methode_paiement = payment_method
		self.reference_paiement = payment_reference
		self.save()
		
		return {
			"message": _("Charge marquée comme payée"),
			"charge_id": self.name
		}
	

	
	@frappe.whitelist()
	def reject_charge(self, reason=None):
		"""Rejette la charge"""
		if self.status == "Payée":
			frappe.throw(_("Une charge payée ne peut pas être rejetée"))
		
		self.status = "Rejetée"
		if reason:
			self.commentaires = (self.commentaires or "") + f"\nRejetée: {reason}"
		self.save()
		
		return {
			"message": _("Charge rejetée"),
			"charge_id": self.name
		}
	
	@frappe.whitelist()
	def get_charge_details(self):
		"""Récupère les détails complets de la charge"""
		details = {
			"charge": {
				"name": self.name,
				"type_charge": self.type_charge,
				"categorie": self.categorie,
				"description": self.description,
				"montant": self.montant,
				"montant_locataire": self.montant_locataire,
				"montant_proprietaire": self.montant_proprietaire,
				"date_charge": self.date_charge,
				"status": self.status,
				"fournisseur": self.fournisseur,
				"numero_facture": self.numero_facture
			}
		}
		
		# Ajoute les détails de l'appartement et du propriétaire
		appartement = frappe.get_doc("Appartement", self.appartement_id)
		proprietaire = frappe.get_doc("Proprietaire", appartement.proprietaire_id)
		details["appartement"] = {
			"adresse_complete": appartement.adresse_complete,
			"surface": appartement.surface,
			"nombre_pieces": appartement.nombre_pieces
		}
		details["proprietaire"] = {
			"nom_complet": proprietaire.nom_complet,
			"email": proprietaire.email,
			"telephone": proprietaire.telephone
		}
		
		# Ajoute les détails de la location si applicable
		if self.location_longue_duree_id:
			location = frappe.get_doc("Location Longue Duree", self.location_longue_duree_id)
			details["location_longue_duree"] = {
				"locataire_nom": location.locataire_nom,
				"locataire_email": location.locataire_email,
				"loyer_mensuel": location.loyer_mensuel_locataire
			}
		
		if self.location_courte_duree_id:
			location = frappe.get_doc("Location Courte Duree", self.location_courte_duree_id)
			details["location_courte_duree"] = {
				"locataire_nom": location.locataire_nom,
				"locataire_email": location.locataire_email,
				"date_debut": location.date_debut,
				"date_fin": location.date_fin
			}
		
		return details
	
	@frappe.whitelist()
	def calculate_charges_statistics(self, start_date=None, end_date=None, appartement_id=None):
		"""Calcule les statistiques des charges pour une période"""
		filters = {"status": ["in", ["Validée", "Payée"]]}
		
		if start_date:
			filters["date_charge"] = [">=", start_date]
		if end_date:
			if "date_charge" in filters:
				filters["date_charge"] = ["between", [start_date, end_date]]
			else:
				filters["date_charge"] = ["<=", end_date]
		
		if appartement_id:
			filters["appartement_id"] = appartement_id
		
		charges = frappe.get_all(
			"Charge",
			filters=filters,
			fields=["montant", "montant_locataire", "montant_proprietaire", "type_charge", "categorie", "status"]
		)
		
		total_montant = sum(c.montant for c in charges)
		total_locataire = sum(c.montant_locataire for c in charges)
		total_proprietaire = sum(c.montant_proprietaire for c in charges)
		
		# Répartition par type de charge
		par_type = {}
		for c in charges:
			if c.type_charge not in par_type:
				par_type[c.type_charge] = {"count": 0, "montant": 0}
			par_type[c.type_charge]["count"] += 1
			par_type[c.type_charge]["montant"] += c.montant
		
		# Répartition par catégorie
		par_categorie = {}
		for c in charges:
			if c.categorie not in par_categorie:
				par_categorie[c.categorie] = {"count": 0, "montant": 0}
			par_categorie[c.categorie]["count"] += 1
			par_categorie[c.categorie]["montant"] += c.montant
		
		# Répartition par status
		par_status = {}
		for c in charges:
			if c.status not in par_status:
				par_status[c.status] = {"count": 0, "montant": 0}
			par_status[c.status]["count"] += 1
			par_status[c.status]["montant"] += c.montant
		
		return {
			"periode": {"debut": start_date, "fin": end_date},
			"appartement_id": appartement_id,
			"total_charges": len(charges),
			"montant_total": total_montant,
			"montant_locataire_total": total_locataire,
			"montant_proprietaire_total": total_proprietaire,
			"repartition_par_type": par_type,
			"repartition_par_categorie": par_categorie,
			"repartition_par_status": par_status
		}
	
	@frappe.whitelist()
	def get_pending_charges(self, appartement_id=None, proprietaire_id=None):
		"""Récupère les charges en attente"""
		filters = {"status": ["in", ["En attente", "Validée"]]}
		
		if appartement_id:
			filters["appartement_id"] = appartement_id
		elif proprietaire_id:
			# Récupère les appartements du propriétaire
			appartements = frappe.get_all(
				"Appartement",
				filters={"proprietaire_id": proprietaire_id},
				fields=["name"]
			)
			appartement_ids = [a.name for a in appartements]
			filters["appartement_id"] = ["in", appartement_ids]
		
		charges = frappe.get_all(
			"Charge",
			filters=filters,
			fields=["name", "type_charge", "description", "montant", "date_charge", "status", "appartement_id"],
			order_by="date_charge desc"
		)
		
		return charges
	
	@frappe.whitelist()
	def send_charge_notification(self, recipient_type="proprietaire"):
		"""Envoie une notification de charge"""
		if recipient_type == "proprietaire":
			appartement = frappe.get_doc("Appartement", self.appartement_id)
			proprietaire = frappe.get_doc("Proprietaire", appartement.proprietaire_id)
			recipient_email = proprietaire.email
			recipient_name = proprietaire.nom_complet
			montant_concerne = self.montant_proprietaire
		elif recipient_type == "locataire" and self.montant_locataire > 0:
			if self.location_longue_duree_id:
				location = frappe.get_doc("Location Longue Duree", self.location_longue_duree_id)
				recipient_email = location.locataire_email
				recipient_name = location.locataire_nom
			elif self.location_courte_duree_id:
				location = frappe.get_doc("Location Courte Duree", self.location_courte_duree_id)
				recipient_email = location.locataire_email
				recipient_name = location.locataire_nom
			else:
				return {"message": _("Aucune location associée pour notifier le locataire")}
			montant_concerne = self.montant_locataire
		else:
			return {"message": _("Type de destinataire invalide")}
		
		if recipient_email and montant_concerne > 0:
			subject = f"Nouvelle charge - {self.name}"
			message = f"""
			Bonjour {recipient_name},
			
			Une nouvelle charge a été enregistrée :
			
			- Référence : {self.name}
			- Type : {self.type_charge}
			- Description : {self.description}
			- Montant total : {self.montant}€
			- Votre part : {montant_concerne}€
			- Date : {self.date_charge}
			- status : {self.status}
			
			{f'Fournisseur : {self.fournisseur}' if self.fournisseur else ''}
			{f'Numéro de facture : {self.numero_facture}' if self.numero_facture else ''}
			
			Cordialement,
			L'équipe de gestion immobilière
			"""
			
			frappe.sendmail(
				recipients=[recipient_email],
				subject=subject,
				message=message
			)
			
			return {"message": _("Notification envoyée à {0}").format(recipient_email)}
		else:
			return {"message": _("Aucun email trouvé ou montant nul")}