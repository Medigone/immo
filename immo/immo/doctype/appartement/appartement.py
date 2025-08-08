# Copyright (c) 2024, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Appartement(Document):
	"""Doctype pour gérer les appartements"""
	
	def validate(self):
		"""Validation des données de l'appartement"""
		self.validate_proprietaire()
		self.validate_surface()
		self.validate_prix()
	
	def validate_proprietaire(self):
		"""Valide que le propriétaire existe et est actif"""
		if self.proprietaire_id:
			proprietaire = frappe.get_doc("Proprietaire", self.proprietaire_id)
			if not proprietaire.actif:
				frappe.throw(f"Le propriétaire {proprietaire.nom_complet} n'est pas actif")
	
	def validate_surface(self):
		"""Valide que la surface est positive"""
		if self.surface and self.surface <= 0:
			frappe.throw("La surface doit être positive")
	
	def validate_prix(self):
		"""Valide que les prix sont positifs"""
		if self.prix_journalier_defaut and self.prix_journalier_defaut <= 0:
			frappe.throw("Le prix journalier doit être positif")
		
		if self.prix_mensuel_defaut and self.prix_mensuel_defaut <= 0:
			frappe.throw("Le prix mensuel doit être positif")
	
	def before_save(self):
		"""Actions avant sauvegarde"""
		# Génère automatiquement l'adresse complète à partir des champs individuels
		self.generate_adresse_complete()
		
		# Normalise l'adresse
		if self.adresse_complete:
			self.adresse_complete = self.adresse_complete.strip()
	
	def generate_adresse_complete(self):
		"""Génère l'adresse complète en concaténant ville, rue et complément d'adresse"""
		adresse_parts = []
		
		# Ajoute la rue si elle existe
		if self.rue:
			adresse_parts.append(self.rue.strip())
		
		# Ajoute le complément d'adresse si il existe
		if self.complement_ad:
			adresse_parts.append(self.complement_ad.strip())
		
		# Ajoute la ville si elle existe
		if self.ville:
			adresse_parts.append(self.ville.strip())
		
		# Concatène avec des virgules et espaces
		self.adresse_complete = ", ".join(adresse_parts) if adresse_parts else ""
	
	def on_update(self):
		"""Actions après mise à jour"""
		# Met à jour les locations actives si l'appartement devient indisponible
		if not self.disponible:
			self.check_active_locations()
	
	def check_active_locations(self):
		"""Vérifie s'il y a des locations actives"""
		# Vérifie les locations longue durée actives
		active_long_term = frappe.get_all("Location Longue Durée",
			filters={
				"appartement_id": self.name,
				"statut": ["in", ["Actif", "En cours"]]
			})
		
		# Vérifie les locations courte durée actives
		active_short_term = frappe.get_all("Location Courte Duree",
			filters={
				"appartement_id": self.name,
				"statut": ["in", ["Confirmé", "En cours"]]
			})
		
		if active_long_term or active_short_term:
			frappe.msgprint("Attention: Cet appartement a des locations actives")
	
	@frappe.whitelist()
	def get_locations_longue_duree(self):
		"""Retourne les locations longue durée de l'appartement"""
		return frappe.get_all("Location Longue Durée",
			filters={"appartement_id": self.name},
			fields=["name", "locataire_nom", "date_debut", "date_fin", "loyer_mensuel_locataire", "statut"],
			order_by="date_debut desc")
	
	@frappe.whitelist()
	def get_locations_courte_duree(self):
		"""Retourne les locations courte durée de l'appartement"""
		return frappe.get_all("Location Courte Duree",
			filters={"appartement_id": self.name},
			fields=["name", "locataire_nom", "date_debut", "date_fin", "montant_total_locataire", "statut"],
			order_by="date_debut desc")
	
	@frappe.whitelist()
	def get_charges(self):
		"""Retourne les charges de l'appartement"""
		return frappe.get_all("Charge",
			filters={"appartement_id": self.name},
			fields=["name", "date_charge", "description", "categorie", "montant", "recupere_proprietaire"],
			order_by="date_charge desc")
	
	@frappe.whitelist()
	def calculate_rentability(self):
		"""Calcule la rentabilité de l'appartement"""
		# Calcul basé sur les 12 derniers mois
		from datetime import datetime, timedelta
		end_date = datetime.now()
		start_date = end_date - timedelta(days=365)
		
		# Revenus des locations
		revenues = frappe.db.sql("""
			SELECT SUM(montant) as total
			FROM `tabPaiement Locataire`
			WHERE (
				location_longue_duree_id IN (
					SELECT name FROM `tabLocation Longue Duree` WHERE appartement_id = %s
				)
				OR location_courte_duree_id IN (
					SELECT name FROM `tabLocation Courte Duree` WHERE appartement_id = %s
				)
			)
			AND date_paiement BETWEEN %s AND %s
			AND statut = 'Payé'
		""", (self.name, self.name, start_date, end_date), as_dict=True)
		
		# Charges de l'appartement
		charges = frappe.db.sql("""
			SELECT SUM(montant) as total
			FROM `tabCharge`
			WHERE appartement_id = %s
			AND date_charge BETWEEN %s AND %s
		""", (self.name, start_date, end_date), as_dict=True)
		
		total_revenus = revenues[0].total or 0
		total_charges = charges[0].total or 0
		benefice_net = total_revenus - total_charges
		
		return {
			"revenus": total_revenus,
			"charges": total_charges,
			"benefice_net": benefice_net,
			"periode": "12 derniers mois"
		}