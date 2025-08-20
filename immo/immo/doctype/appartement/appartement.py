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
	
	@frappe.whitelist()
	def validate_location_overlap(self, location_type, date_debut, date_fin, exclude_location=None):
		"""Valide qu'il n'y a pas de chevauchement entre les locations"""
		from datetime import datetime
		
		# Vérifier que le document a un nom (n'est pas nouveau)
		if not self.name or self.name.startswith('new-'):
			# Pour un nouveau document, pas de conflit possible
			return True
		
		if isinstance(date_debut, str):
			date_debut = datetime.strptime(date_debut, '%Y-%m-%d').date()
		if isinstance(date_fin, str):
			date_fin = datetime.strptime(date_fin, '%Y-%m-%d').date()
		
		# Vérifier les locations courte durée
		filters_courte = {
			"appartement_id": self.name,
			"statut": ["in", ["Confirmée", "En cours", "Terminée"]]
		}
		if exclude_location and location_type == "Location Courte Duree":
			filters_courte["name"] = ["!=", exclude_location]
		
		locations_courte = frappe.get_all("Location Courte Duree",
			filters=filters_courte,
			fields=["name", "date_debut", "date_fin"])
		
		# Vérifier les locations longue durée
		filters_longue = {
			"appartement_id": self.name,
			"statut": ["in", ["Confirmée", "En cours", "Terminée"]]
		}
		if exclude_location and location_type == "Location Longue Duree":
			filters_longue["name"] = ["!=", exclude_location]
		
		locations_longue = frappe.get_all("Location Longue Duree",
			filters=filters_longue,
			fields=["name", "date_debut", "date_fin"])
		
		# Vérifier les chevauchements
		all_locations = locations_courte + locations_longue
		for location in all_locations:
			loc_debut = location.date_debut
			loc_fin = location.date_fin
			
			# Règle: pas de chevauchement sauf si date_fin = date_debut
			if not (date_fin < loc_debut or date_debut > loc_fin or 
					date_fin == loc_debut or date_debut == loc_fin):
				frappe.throw(
					f"Conflit de dates détecté avec la location {location.name}. "
					f"Les périodes ne peuvent pas se chevaucher sauf si la date de fin "
					f"d'une location correspond à la date de début d'une autre."
				)
		
		return True
	
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
		# Fonction conservée pour compatibilité
		pass
	

	
	@frappe.whitelist()
	def get_locations_longue_duree(self):
		"""Retourne les locations longue durée de l'appartement"""
		if not self.name or self.name.startswith('new-'):
			return []
		return frappe.get_all("Location Longue Duree",
			filters={"appartement_id": self.name},
			fields=["name", "locataire_nom", "date_debut", "date_fin", "loyer_mensuel_locataire", "statut"],
			order_by="date_debut desc")
	
	@frappe.whitelist()
	def get_locations_courte_duree(self):
		"""Retourne les locations courte durée de l'appartement"""
		if not self.name or self.name.startswith('new-'):
			return []
		return frappe.get_all("Location Courte Duree",
			filters={"appartement_id": self.name},
			fields=["name", "locataire_nom", "date_debut", "date_fin", "montant_total_locataire", "statut"],
			order_by="date_debut desc")
	
	@frappe.whitelist()
	def get_charges(self):
		"""Retourne les charges de l'appartement"""
		if not self.name or self.name.startswith('new-'):
			return []
		return frappe.get_all("Charge",
			filters={"appartement_id": self.name},
			fields=["name", "date_charge", "description", "categorie", "montant", "recupere_proprietaire"],
			order_by="date_charge desc")
	
	@frappe.whitelist()
	def calculate_rentability(self):
		"""Calcule la rentabilité de l'appartement - Revenus, Charges et Marge"""
		try:
			# Vérifier que le document a un nom (n'est pas nouveau)
			if not self.name or self.name.startswith('new-'):
				return {
					"revenus_total": 0,
					"charges_total": 0,
					"marge": 0,
					"periode": "Aucune donnée disponible pour un nouveau document"
				}
			
			from datetime import datetime, timedelta
			end_date = datetime.now()
			start_date = end_date - timedelta(days=365)
			
			# Revenus - Paiements Locataire avec status = 'Payé'
			# Jointure avec les tables de location pour obtenir l'appartement
			revenues = frappe.db.sql("""
				SELECT SUM(pl.montant) as total
				FROM `tabPaiement Locataire` pl
				LEFT JOIN `tabLocation Courte Duree` lcd ON pl.location_courte_duree_id = lcd.name
				LEFT JOIN `tabLocation Longue Duree` lld ON pl.location_longue_duree_id = lld.name
				WHERE (lcd.appartement_id = %s OR lld.appartement_id = %s)
				AND pl.date_paiement BETWEEN %s AND %s
				AND pl.status = 'Payé'
			""", (self.name, self.name, start_date, end_date), as_dict=True)
			
			# Charges - Paiements Propriétaire avec status = 'Payé'
			charges = frappe.db.sql("""
				SELECT SUM(montant) as total
				FROM `tabPaiement Proprietaire`
				WHERE appartement = %s
				AND date_paiement BETWEEN %s AND %s
				AND status = 'Payé'
			""", (self.name, start_date, end_date), as_dict=True)
			
			total_revenus = revenues[0].total or 0
			total_charges = charges[0].total or 0
			marge = total_revenus - total_charges
			
			return {
				"revenus_total": total_revenus,
				"charges_total": total_charges,
				"marge": marge,
				"periode": "12 derniers mois"
			}
		except Exception as e:
			frappe.log_error(f"Erreur dans calculate_rentability pour appartement {self.name}: {str(e)}")
			return {
				"revenus_total": 0,
				"charges_total": 0,
				"marge": 0,
				"periode": "12 derniers mois"
			}