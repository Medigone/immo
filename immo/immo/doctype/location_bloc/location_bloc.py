# Copyright (c) 2024, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import getdate, date_diff, flt
from datetime import datetime


class LocationBloc(Document):
	"""DocType pour gérer les locations en bloc d'appartements."""
	
	def validate(self):
		"""Validation des données avant sauvegarde."""
		self.validate_dates()
		self.validate_appartement_availability()
		self.calculate_nights_and_price()
		self.set_timestamps()
	
	def validate_dates(self):
		"""Valide que les dates sont cohérentes."""
		if not self.date_debut_bloc or not self.date_fin_bloc:
			frappe.throw("Les dates de début et fin sont obligatoires")
		
		if getdate(self.date_fin_bloc) <= getdate(self.date_debut_bloc):
			frappe.throw("La date de fin doit être postérieure à la date de début")
		
		# Permettre la saisie de dates antérieures pour les saisies rétroactives
		# Pas de validation sur les dates passées
	
	def validate_appartement_availability(self):
		"""Vérifie la disponibilité de l'appartement pour la période."""
		if not self.appartement_id:
			return
		
		# Vérifier les conflits avec d'autres locations bloc
		conflicting_blocs = frappe.db.sql("""
			SELECT name FROM `tabLocation Bloc`
			WHERE appartement_id = %s
			AND name != %s
			AND statut NOT IN ('Annulé', 'Terminé')
			AND (
				(date_debut_bloc <= %s AND date_fin_bloc >= %s)
				OR (date_debut_bloc <= %s AND date_fin_bloc >= %s)
				OR (date_debut_bloc >= %s AND date_fin_bloc <= %s)
			)
		""", (
			self.appartement_id, self.name or '',
			self.date_debut_bloc, self.date_debut_bloc,
			self.date_fin_bloc, self.date_fin_bloc,
			self.date_debut_bloc, self.date_fin_bloc
		))
		
		if conflicting_blocs:
			frappe.throw(f"L'appartement est déjà réservé en bloc pour cette période (Conflit avec: {conflicting_blocs[0][0]})")
		
		# Vérifier les conflits avec les locations longue durée
		conflicting_long = frappe.db.sql("""
			SELECT name FROM `tabLocation Longue Duree`
			WHERE appartement_id = %s
			AND statut NOT IN ('Annulé', 'Terminé')
			AND (
				(date_debut <= %s AND date_fin >= %s)
				OR (date_debut <= %s AND date_fin >= %s)
				OR (date_debut >= %s AND date_fin <= %s)
			)
		""", (
			self.appartement_id,
			self.date_debut_bloc, self.date_debut_bloc,
			self.date_fin_bloc, self.date_fin_bloc,
			self.date_debut_bloc, self.date_fin_bloc
		))
		
		if conflicting_long:
			frappe.throw(f"L'appartement a une location longue durée active pour cette période (Conflit avec: {conflicting_long[0][0]})")
	
	@frappe.whitelist()
	def calculate_nights_and_price(self):
		"""Calcule le nombre de nuits et le prix par nuit."""
		if self.date_debut_bloc and self.date_fin_bloc:
			self.nombre_nuits_total = date_diff(self.date_fin_bloc, self.date_debut_bloc)
			
			if self.montant_total_proprietaire and self.nombre_nuits_total > 0:
				self.prix_nuit_proprietaire = flt(self.montant_total_proprietaire) / self.nombre_nuits_total
	
	def set_timestamps(self):
		"""Met à jour les timestamps."""
		if self.is_new():
			self.date_creation = datetime.now()
		self.date_modification = datetime.now()
	
	def on_update(self):
		"""Actions après mise à jour du document."""
		self.update_metrics()
	
	def on_cancel(self):
		"""Actions lors de l'annulation."""
		pass
	
	def update_metrics(self):
		"""Met à jour les métriques de performance."""
		try:
			# Calculer le total encaissé (montant des locations)
			total_encaisse = frappe.db.sql("""
				SELECT COALESCE(SUM(montant_total_locataire), 0)
				FROM `tabLocation Courte Duree`
				WHERE location_bloc_id = %s
			""", (self.name,))[0][0] or 0
			
			self.total_encaisse = flt(total_encaisse)
			
			# Calculer les paiements prévus (montant total des locations courte durée)
			paiements_prevus = frappe.db.sql("""
				SELECT COALESCE(SUM(montant_total_locataire), 0)
				FROM `tabLocation Courte Duree`
				WHERE location_bloc_id = %s
			""", (self.name,))[0][0] or 0
			
			self.paiements_prevus = flt(paiements_prevus)
			
			# Calculer les paiements totaux (somme des paiements locataires)
			paiements_totaux = frappe.db.sql("""
				SELECT COALESCE(SUM(montant), 0)
				FROM `tabPaiement Locataire`
				WHERE location_bloc_id = %s
			""", (self.name,))[0][0] or 0
			
			self.paiements_totaux = flt(paiements_totaux)
			
			# Calculer la marge totale basée sur les paiements réels
			if self.montant_total_proprietaire:
				self.marge_totale = flt(self.paiements_totaux) - flt(self.montant_total_proprietaire)
				
				# Calculer la rentabilité en pourcentage basée sur les paiements réels
				if flt(self.montant_total_proprietaire) > 0:
					self.rentabilite_pourcentage = (flt(self.marge_totale) / flt(self.montant_total_proprietaire)) * 100
			
			# Calculer le taux d'occupation
			nuits_occupees = frappe.db.sql("""
				SELECT COALESCE(SUM(nombre_nuits), 0)
				FROM `tabLocation Courte Duree`
				WHERE location_bloc_id = %s
			""", (self.name,))[0][0] or 0
			
			if self.nombre_nuits_total and self.nombre_nuits_total > 0:
				self.taux_occupation = (flt(nuits_occupees) / self.nombre_nuits_total) * 100
			
			# Sauvegarder sans déclencher les hooks
			frappe.db.set_value("Location Bloc", self.name, {
				"total_encaisse": self.total_encaisse,
				"paiements_prevus": self.paiements_prevus,
				"paiements_totaux": self.paiements_totaux,
				"marge_totale": self.marge_totale,
				"rentabilite_pourcentage": self.rentabilite_pourcentage,
				"taux_occupation": self.taux_occupation
			})
			
		except Exception as e:
			frappe.log_error(f"Erreur lors de la mise à jour des métriques pour Location Bloc {self.name}: {str(e)}")
	

	

	


	@frappe.whitelist()
	def get_quote_part_nuit(self):
		"""Retourne la quote-part par nuit pour les calculs de sous-location."""
		if self.montant_total_proprietaire and self.nombre_nuits_total and self.nombre_nuits_total > 0:
			return flt(self.montant_total_proprietaire) / self.nombre_nuits_total
		return 0
	
	@frappe.whitelist()
	def get_available_nights(self):
		"""Retourne le nombre de nuits encore disponibles pour sous-location."""
		nuits_occupees = frappe.db.sql("""
			SELECT COALESCE(SUM(nombre_nuits), 0)
			FROM `tabLocation Courte Duree`
			WHERE location_bloc_id = %s
		""", (self.name,))[0][0] or 0
		
		return (self.nombre_nuits_total or 0) - flt(nuits_occupees)

	@frappe.whitelist()
	def create_paiement_bloc(self, montant_paiement=None, date_paiement=None, type_paiement=None, methode_paiement=None, reference_paiement=None, notes=None):
		"""Crée un nouveau paiement bloc basé sur cette location bloc."""
		# Créer un nouveau document Paiement Bloc
		paiement_bloc = frappe.new_doc("Paiement Bloc")
		paiement_bloc.location_bloc_id = self.name
		paiement_bloc.proprietaire_id = self.proprietaire_id
		paiement_bloc.appartement_id = self.appartement_id
		
		# Utiliser les paramètres fournis ou les valeurs par défaut
		paiement_bloc.montant_paiement = flt(montant_paiement) if montant_paiement else flt(self.montant_total_proprietaire)
		paiement_bloc.date_paiement = date_paiement if date_paiement else frappe.utils.today()
		paiement_bloc.type_paiement = type_paiement if type_paiement else "Unique"
		
		# Champs optionnels
		if methode_paiement:
			paiement_bloc.methode_paiement = methode_paiement
		if reference_paiement:
			paiement_bloc.reference_paiement = reference_paiement
		if notes:
			paiement_bloc.notes = notes
		
		# Sauvegarder le paiement
		paiement_bloc.insert()
		
		# La mise à jour des champs se fait automatiquement via le hook on_update
		
		return {
			"type": "success",
			"message": "Paiement Bloc créé avec succès",
			"paiement_id": paiement_bloc.name,
			"refresh_form": True
		}
	
	def update_payment_tracking(self):
		"""Met à jour les champs de suivi des paiements dans Location Bloc."""
		try:
			# Calculer le montant total payé
			total_paye = frappe.db.sql("""
				SELECT COALESCE(SUM(montant_paiement), 0)
				FROM `tabPaiement Bloc`
				WHERE location_bloc_id = %s
			""", (self.name,))[0][0] or 0
			
			self.montant_total_paye = flt(total_paye)
			
			# Calculer le solde restant
			if self.montant_total_proprietaire:
				self.solde_restant = flt(self.montant_total_proprietaire) - flt(total_paye)
				
				# Calculer le pourcentage payé
				if flt(self.montant_total_proprietaire) > 0:
					self.pourcentage_paye = (flt(total_paye) / flt(self.montant_total_proprietaire)) * 100
				else:
					self.pourcentage_paye = 0
			else:
				self.solde_restant = 0
				self.pourcentage_paye = 0
			
			# Sauvegarder sans déclencher les hooks
			frappe.db.set_value("Location Bloc", self.name, {
				"montant_total_paye": self.montant_total_paye,
				"solde_restant": self.solde_restant,
				"pourcentage_paye": self.pourcentage_paye
			})
			
			# Mettre à jour aussi les métriques de performance
			self.update_metrics()
			
			frappe.db.commit()
			
			# Déclencher une mise à jour côté client pour le dashboard
			frappe.publish_realtime(
				"location_bloc_updated",
				{"location_bloc_id": self.name, "action": "payment_updated"},
				user=frappe.session.user
			)
			
		except Exception as e:
			frappe.log_error(f"Erreur lors de la mise à jour du suivi des paiements pour Location Bloc {self.name}: {str(e)}")
	
	def create_location_courte_duree(self, date_debut=None, date_fin=None, locataire_nom=None, prix_journalier_locataire=None):
		"""Crée une nouvelle Location Courte Duree liée à cette location bloc."""
		
		# Utiliser les dates du bloc si non spécifiées
		if not date_debut:
			date_debut = self.date_debut_bloc
		if not date_fin:
			date_fin = self.date_fin_bloc
		
		# Vérifier que les dates sont dans la période du bloc
		if getdate(date_debut) < getdate(self.date_debut_bloc) or getdate(date_fin) > getdate(self.date_fin_bloc):
			frappe.throw("Les dates de sous-location doivent être comprises dans la période du bloc")
		
		# Créer la nouvelle Location Courte Duree
		location_courte_duree = frappe.new_doc("Location Courte Duree")
		location_courte_duree.location_bloc_id = self.name
		location_courte_duree.appartement_id = self.appartement_id
		location_courte_duree.date_debut = date_debut
		location_courte_duree.date_fin = date_fin
		
		# Ajouter les champs obligatoires si fournis
		if locataire_nom:
			location_courte_duree.locataire_nom = locataire_nom
		if prix_journalier_locataire:
			location_courte_duree.prix_journalier_locataire = flt(prix_journalier_locataire)
		
		# Le type_location sera automatiquement défini sur "Sous-location" par la logique existante
		
		# Insérer la nouvelle location courte durée
		location_courte_duree.insert()
		
		# Recharger le document pour éviter les conflits de timestamp
		self.reload()
		
		# Forcer la synchronisation de la base de données
		frappe.db.commit()
		
		frappe.msgprint(
			f"Sous-location {location_courte_duree.name} créée avec succès.",
			title="Sous-location créée",
			indicator="green"
		)
		
		# Rediriger vers la nouvelle location courte durée
		return {
			"type": "redirect",
			"route": f"/app/location-courte-duree/{location_courte_duree.name}"
		}
	


@frappe.whitelist()
def create_paiement_bloc(docname, montant_paiement=None, date_paiement=None, type_paiement=None, methode_paiement=None, reference_paiement=None, notes=None):
	"""Fonction globale pour créer un paiement bloc depuis une location bloc."""
	# Charger le document Location Bloc
	location_bloc = frappe.get_doc("Location Bloc", docname)
	
	# Appeler la méthode de l'instance avec les paramètres
	return location_bloc.create_paiement_bloc(
		montant_paiement=montant_paiement,
		date_paiement=date_paiement,
		type_paiement=type_paiement,
		methode_paiement=methode_paiement,
		reference_paiement=reference_paiement,
		notes=notes
	)

@frappe.whitelist()
def create_location_courte_duree(docname, date_debut=None, date_fin=None, locataire_nom=None, prix_journalier_locataire=None):
	"""Fonction globale pour créer une location courte durée depuis une location bloc."""
	# Charger le document Location Bloc
	location_bloc = frappe.get_doc("Location Bloc", docname)
	
	# Appeler la méthode de l'instance
	return location_bloc.create_location_courte_duree(date_debut, date_fin, locataire_nom, prix_journalier_locataire)