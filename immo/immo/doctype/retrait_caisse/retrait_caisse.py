# Copyright (c) 2024, Wezri and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now


class RetraitCaisse(Document):
	"""DocType pour la gestion des retraits manuels de caisse."""
	
	def validate(self):
		"""Validation du document Retrait Caisse."""
		self.validate_montant()
		self.validate_solde_suffisant()
	
	def validate_montant(self):
		"""Valide que le montant est positif."""
		if self.montant <= 0:
			frappe.throw("Le montant doit être positif")
	
	def validate_solde_suffisant(self):
		"""Valide que le solde de la caisse est suffisant pour le retrait."""
		if self.status == "Confirmé":
			from immo.immo.doctype.caisse.caisse import Caisse
			solde_actuel = Caisse.get_solde_actuel()
			
			if solde_actuel < self.montant:
				frappe.throw(f"Solde insuffisant. Solde actuel: {solde_actuel}, Montant demandé: {self.montant}")
	
	def on_submit(self):
		"""Actions après soumission du document."""
		if self.status == "Confirmé":
			self.create_mouvement_caisse()
			self.date_validation = now()
	
	def on_cancel(self):
		"""Actions après annulation du document."""
		# Si le retrait était confirmé, créer un mouvement de caisse inverse
		if self.status == "Confirmé" or self.date_validation:
			from immo.immo.doctype.mouvement_caisse.mouvement_caisse import MouvementCaisse
			
			# Créer un mouvement d'entrée pour compenser l'annulation du retrait
			mouvement = MouvementCaisse.create_mouvement(
				type_mouvement="Entrée",
				montant=self.montant,
				notes=f"Annulation retrait - {self.motif or 'Aucun motif spécifié'}",
				reference_doctype="Retrait Caisse",
				reference_docname=f"{self.name}-ANNULE"
			)
			
			# Sauvegarder le mouvement (pas de submit car non soumissible)
			mouvement.save()
		
		self.status = "Annulé"
	
	def create_mouvement_caisse(self):
		"""Crée un mouvement de caisse pour ce retrait."""
		from immo.immo.doctype.mouvement_caisse.mouvement_caisse import MouvementCaisse
		
		# Créer le mouvement de caisse
		mouvement = MouvementCaisse.create_mouvement(
			type_mouvement="Sortie",
			montant=self.montant,
			notes=f"Retrait manuel - {self.motif or 'Aucun motif spécifié'}",
			reference_doctype="Retrait Caisse",
			reference_docname=self.name
		)
		
		# Sauvegarder le mouvement (pas de submit car non soumissible)
		mouvement.save()
		
		return mouvement
	
	@frappe.whitelist()
	def confirmer_retrait(self):
		"""Confirme le retrait et crée le mouvement de caisse."""
		if self.status != "Nouveau":
			frappe.throw("Seuls les retraits avec le statut 'Nouveau' peuvent être confirmés")
		
		# Vérifier le solde avant confirmation
		self.validate_solde_suffisant()
		
		self.status = "Confirmé"
		self.date_validation = now()
		self.save()
		
		# Créer le mouvement de caisse
		self.create_mouvement_caisse()
		
		frappe.msgprint(f"Retrait de {self.montant} confirmé avec succès")
	
	@staticmethod
	def create_retrait(montant, motif=None, date=None):
		"""Crée un nouveau document Retrait Caisse."""
		retrait = frappe.new_doc("Retrait Caisse")
		retrait.montant = montant
		retrait.motif = motif
		retrait.date = date or frappe.utils.today()
		retrait.status = "Nouveau"
		
		retrait.insert()
		return retrait