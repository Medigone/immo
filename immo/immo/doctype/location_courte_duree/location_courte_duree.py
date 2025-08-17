# Copyright (c) 2024, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate
from datetime import datetime, timedelta


class LocationCourteDuree(Document):
	"""Doctype pour gérer les locations courte durée (réservations journalières)"""
	
	def validate(self):
		"""Validation des données de la location"""
		self.validate_appartement()
		self.validate_dates()
		self.validate_prix()
		self.validate_email()
		self.validate_referent()
		self.validate_location_bloc()
	
	def validate_appartement(self):
		"""Valide que l'appartement existe"""
		if self.appartement_id:
			# Vérifier que l'appartement existe
			appartement = frappe.get_doc("Appartement", self.appartement_id)
			# La disponibilité sera vérifiée par les validations de chevauchement de dates
	
	def validate_dates(self):
		"""Valide les dates de location"""
		if self.date_debut and self.date_fin:
			date_debut = getdate(self.date_debut)
			date_fin = getdate(self.date_fin)
			if date_fin <= date_debut:
				frappe.throw("La date de fin doit être postérieure à la date de début")
		

	
	def validate_prix(self):
		"""Valide que les prix sont positifs"""
		if self.prix_journalier_locataire and self.prix_journalier_locataire <= 0:
			frappe.throw("Le prix journalier locataire doit être positif")
		
		if self.prix_journalier_proprietaire and self.prix_journalier_proprietaire <= 0:
			frappe.throw("Le prix journalier propriétaire doit être positif")
		
		if (self.prix_journalier_locataire and self.prix_journalier_proprietaire and 
			self.prix_journalier_proprietaire >= self.prix_journalier_locataire):
			frappe.throw("Le prix propriétaire doit être inférieur au prix locataire")
	
	def validate_email(self):
		"""Valide le format de l'email du locataire"""
		if self.locataire_email:
			import re
			email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
			if not re.match(email_pattern, self.locataire_email):
				frappe.throw("Format d'email invalide pour le locataire")
	
	def validate_referent(self):
		"""Valide que le référent existe si spécifié"""
		if self.referent_id:
			referent = frappe.get_doc("Referent", self.referent_id)
			if not referent.actif:
				frappe.throw(f"Le référent {referent.nom_complet} n'est pas actif")
	
	def validate_location_bloc(self):
		"""Valide la cohérence avec la location bloc si une est sélectionnée"""
		if self.location_bloc_id:
			# Vérifier que la location bloc existe et est active
			location_bloc = frappe.get_doc("Location Bloc", self.location_bloc_id)
			if location_bloc.statut in ["Annulé", "Terminé"]:
				frappe.throw("Impossible de créer une sous-location sur un bloc annulé ou terminé")
			
			# Vérifier que l'appartement correspond
			if location_bloc.appartement_id != self.appartement_id:
				frappe.throw("L'appartement doit correspondre à celui de la location bloc")
			
			# Vérifier que les dates sont dans la période du bloc
			if self.date_debut and self.date_fin:
				if (getdate(self.date_debut) < getdate(location_bloc.date_debut_bloc) or 
					getdate(self.date_fin) > getdate(location_bloc.date_fin_bloc)):
					frappe.throw("Les dates de sous-location doivent être comprises dans la période du bloc")
			
			# Calculer automatiquement le prix journalier propriétaire basé sur la quote-part du bloc
			self.calculate_prix_proprietaire_from_bloc(location_bloc)
			
			# Vérifier les chevauchements avec d'autres sous-locations
			self.check_bloc_overlaps()
	
	def calculate_prix_proprietaire_from_bloc(self, location_bloc):
		"""Calcule automatiquement le prix journalier propriétaire basé sur la quote-part du bloc"""
		try:
			# Récupérer la quote-part par nuit du bloc
			quote_part_nuit = location_bloc.get_quote_part_nuit()
			
			if quote_part_nuit > 0:
				# Définir le prix journalier propriétaire égal à la quote-part
				self.prix_journalier_proprietaire = quote_part_nuit
				frappe.msgprint(f"Prix journalier propriétaire calculé automatiquement: {quote_part_nuit} (basé sur la quote-part du bloc)")
			else:
				frappe.msgprint("Impossible de calculer le prix propriétaire: quote-part du bloc non définie")
				
		except Exception as e:
			frappe.log_error(f"Erreur calcul prix propriétaire depuis bloc {self.location_bloc_id}: {str(e)}")
			frappe.msgprint("Erreur lors du calcul automatique du prix propriétaire")

	def check_bloc_overlaps(self):
		"""Vérifie les chevauchements avec d'autres sous-locations du même bloc"""
		if not self.location_bloc_id or not self.date_debut or not self.date_fin:
			return
		
		# Modifié pour permettre qu'une date de fin soit égale à une date de début
		overlapping = frappe.db.sql("""
			SELECT name, locataire_nom, date_debut, date_fin
			FROM `tabLocation Courte Duree`
			WHERE location_bloc_id = %s
			AND name != %s
			AND statut NOT IN ('Annulé')
			AND (
				(date_debut < %s AND date_fin > %s)
				OR (date_debut < %s AND date_fin > %s)
				OR (date_debut > %s AND date_fin < %s)
			)
		""", (
			self.location_bloc_id, self.name or '',
			self.date_fin, self.date_debut,
			self.date_fin, self.date_debut,
			self.date_debut, self.date_fin
		))
		
		if overlapping:
			conflict = overlapping[0]
			frappe.throw(f"Conflit de dates avec la sous-location {conflict[0]} ({conflict[1]}) du {conflict[2]} au {conflict[3]}")
	
	def set_type_location(self):
		"""Détermine automatiquement le type de location selon la présence d'une Location Bloc"""
		if self.location_bloc_id:
			self.type_location = "Sous-location"
		else:
			self.type_location = "Directe"
	
	def before_save(self):
		"""Actions avant sauvegarde"""
		# Détermination automatique du type de location
		self.set_type_location()
		
		# Calcule le nombre de nuits
		self.calculate_nights()
		
		# Calcule les montants et marges
		self.calculate_amounts()
		
		# Calcule la commission du référent
		self.calculate_referent_commission()
		
		# Normalise le nom du locataire
		if self.locataire_nom:
			self.locataire_nom = self.locataire_nom.strip().title()
	
	def calculate_nights(self):
		"""Calcule le nombre de nuits"""
		if self.date_debut and self.date_fin:
			start_date = datetime.strptime(str(self.date_debut), "%Y-%m-%d")
			end_date = datetime.strptime(str(self.date_fin), "%Y-%m-%d")
			self.nombre_nuits = (end_date - start_date).days
	
	def calculate_amounts(self):
		"""Calcule les montants totaux"""
		if self.nombre_nuits and self.prix_journalier_locataire:
			self.montant_total_locataire = self.nombre_nuits * self.prix_journalier_locataire
			
			# Calculs spécifiques selon le type de location
			if self.type_location == "Sous-location" and self.location_bloc_id:
				self.calculate_bloc_amounts()
			elif self.prix_journalier_proprietaire:
				# Location directe classique
				self.montant_total_proprietaire = self.nombre_nuits * self.prix_journalier_proprietaire
				self.marge_totale = self.montant_total_locataire - self.montant_total_proprietaire
	
	def calculate_bloc_amounts(self):
		"""Calcule les montants pour une sous-location en bloc"""
		try:
			location_bloc = frappe.get_doc("Location Bloc", self.location_bloc_id)
			
			# Calculer la quote-part par nuit du bloc
			quote_part_nuit = location_bloc.get_quote_part_nuit()
			self.quote_part_bloc = quote_part_nuit * self.nombre_nuits
			
			# La marge sur bloc = revenus locataire - quote-part bloc
			self.marge_sur_bloc = self.montant_total_locataire - self.quote_part_bloc
			
			# Pour compatibilité avec le système existant
			self.montant_total_proprietaire = self.quote_part_bloc
			self.marge_totale = self.marge_sur_bloc
			
		except Exception as e:
			frappe.log_error(f"Erreur calcul montants bloc pour {self.name}: {str(e)}")
			# En cas d'erreur, utiliser le calcul classique
			if self.prix_journalier_proprietaire:
				self.montant_total_proprietaire = self.nombre_nuits * self.prix_journalier_proprietaire
				self.marge_totale = self.montant_total_locataire - self.montant_total_proprietaire
	
	def calculate_referent_commission(self):
		"""Calcule la commission du référent"""
		if self.referent_id and self.marge_totale:
			referent = frappe.get_doc("Referent", self.referent_id)
			if referent.pourcentage_commission_defaut:
				self.commission_referent = (self.marge_totale * referent.pourcentage_commission_defaut) / 100
		else:
			self.commission_referent = 0
	

	

	
	@frappe.whitelist()
	def get_commission(self):
		"""Retourne la commission associée à cette location"""
		return frappe.get_all("Commission",
			filters={"location_courte_duree_id": self.name},
			fields=["name", "montant_commission", "pourcentage_commission", "statut_paiement", "date_creation", "date_paiement"])
	
	@frappe.whitelist()
	def get_paiements_locataire(self):
		"""Retourne les paiements du locataire"""
		return frappe.get_all("Paiement Locataire",
			filters={"location_courte_duree_id": self.name},
			fields=["name", "montant", "date_paiement", "status", "methode_paiement"],
			order_by="date_paiement desc")
	
	@frappe.whitelist()
	def get_paiements_proprietaire(self):
		"""Retourne les paiements au propriétaire"""
		return frappe.get_all("Paiement Propriétaire",
            filters={"location_courte_duree_id": self.name},
            fields=["name", "montant", "date_paiement", "status", "methode_paiement"],
			order_by="date_paiement desc")
	
	@frappe.whitelist()
	def calculate_net_margin(self):
		"""Calcule la marge nette après commission référent"""
		net_margin = self.marge_totale - (self.commission_referent or 0)
		return {
			"marge_totale": self.marge_totale,
			"commission_referent": self.commission_referent or 0,
			"marge_nette": net_margin
		}
	

	

	
	def update_location_bloc_metrics(self):
		"""Met à jour les métriques de la location bloc"""
		try:
			if self.location_bloc_id:
				location_bloc = frappe.get_doc("Location Bloc", self.location_bloc_id)
				location_bloc.reload()
				location_bloc.update_metrics()
				location_bloc.save()
		except Exception as e:
			frappe.log_error(f"Erreur MAJ métriques {self.location_bloc_id}: {str(e)[:50]}", "LCD Metrics Error")
	
	@frappe.whitelist()
	def check_availability(self):
		"""Vérifie la disponibilité de l'appartement pour les dates données"""
		if not self.appartement_id or not self.date_debut or not self.date_fin:
			return {"available": False, "message": "Données incomplètes"}
		
		# Vérifie les conflits avec d'autres locations courte durée
		conflicting_short = frappe.get_all("Location Courte Duree",
			filters={
				"appartement_id": self.appartement_id,
				"statut": ["in", ["Confirmé", "En cours"]],
				"name": ["!=", self.name] if not self.is_new() else None
			})
		
		for location in conflicting_short:
			loc_doc = frappe.get_doc("Location Courte Duree", location.name)
			# Modifié pour permettre qu'une date de fin soit égale à une date de début
			if (self.date_debut < loc_doc.date_fin and self.date_fin > loc_doc.date_debut):
				return {
					"available": False, 
					"message": f"Conflit avec la location {loc_doc.name}"
				}
		
		# Vérifie les conflits avec les locations longue durée
		conflicting_long = frappe.get_all("Location Longue Duree",
			filters={
				"appartement_id": self.appartement_id,
				"statut": "Actif"
			})
		
		for location in conflicting_long:
			loc_doc = frappe.get_doc("Location Longue Duree", location.name)
			# Modifié pour permettre qu'une date de fin soit égale à une date de début
			if (self.date_debut < loc_doc.date_fin and self.date_fin > loc_doc.date_debut):
				return {
					"available": False, 
					"message": f"Conflit avec la location longue durée {loc_doc.name}"
				}
		
		return {"available": True, "message": "Appartement disponible"}
	
	def calculate_payment_status(self):
		"""Calcule le statut des paiements et met à jour les champs de suivi"""
		try:
			# Calculer les paiements locataire
			self.calculate_locataire_payments()
			
			# Calculer les paiements propriétaire
			self.calculate_proprietaire_payments()
			
		except Exception as e:
			frappe.log_error(f"Erreur calcul statut paiements {self.name}: {str(e)}", "LCD Payment Status Error")
	
	def calculate_locataire_payments(self):
		"""Calcule les montants payés et restants pour le locataire"""
		try:
			# Récupérer tous les paiements validés (status = 'Payé')
			paiements = frappe.get_all("Paiement Locataire",
				filters={
					"location_courte_duree_id": self.name,
					"status": "Payé"
				},
				fields=["montant"]
			)
			
			# Calculer le total payé
			total_paye = sum(paiement.montant for paiement in paiements)
			self.montant_paye_locataire = total_paye
			
			# Calculer le montant restant
			montant_total = self.montant_total_locataire or 0
			self.montant_restant_locataire = max(0, montant_total - total_paye)
			
			# Déterminer le statut
			if total_paye == 0:
				self.statut_paiement_locataire = "En attente"
			elif total_paye >= montant_total:
				self.statut_paiement_locataire = "Entièrement payé"
			else:
				self.statut_paiement_locataire = "Partiellement payé"
				
		except Exception as e:
			frappe.log_error(f"Erreur calcul paiements locataire {self.name}: {str(e)}", "LCD Locataire Payment Error")
	
	def calculate_proprietaire_payments(self):
		"""Calcule les montants versés et restants pour le propriétaire"""
		try:
			# Récupérer tous les paiements validés (status = 'Payé')
			paiements = frappe.get_all("Paiement Proprietaire",
				filters={
					"location_courte_duree_id": self.name,
					"status": "Payé"
				},
				fields=["montant"]
			)
			
			# Calculer le total versé
			total_verse = sum(paiement.montant for paiement in paiements)
			self.montant_paye_proprietaire = total_verse
			
			# Calculer le montant restant
			montant_total = self.montant_total_proprietaire or 0
			self.montant_restant_proprietaire = max(0, montant_total - total_verse)
			
			# Déterminer le statut
			if total_verse == 0:
				self.statut_paiement_proprietaire = "En attente"
			elif total_verse >= montant_total:
				self.statut_paiement_proprietaire = "Entièrement versé"
			else:
				self.statut_paiement_proprietaire = "Partiellement versé"
				
		except Exception as e:
			frappe.log_error(f"Erreur calcul paiements propriétaire {self.name}: {str(e)}", "LCD Proprietaire Payment Error")
	
	@frappe.whitelist()
	def refresh_payment_status(self):
		"""Méthode publique pour rafraîchir le statut des paiements"""
		self.calculate_payment_status()
		self.save()
		return {
			"montant_paye_locataire": self.montant_paye_locataire,
			"montant_restant_locataire": self.montant_restant_locataire,
			"statut_paiement_locataire": self.statut_paiement_locataire,
			"montant_paye_proprietaire": self.montant_paye_proprietaire,
			"montant_restant_proprietaire": self.montant_restant_proprietaire,
			"statut_paiement_proprietaire": self.statut_paiement_proprietaire
		}