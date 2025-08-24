# Copyright (c) 2024, Wezri and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now


class MouvementCaisse(Document):
	"""DocType pour le journal des mouvements de caisse."""
	
	def validate(self):
		"""Validation du document Mouvement Caisse."""
		self.validate_montant()
		# Les soldes seront calculés dans after_insert() pour avoir le bon solde_avant
	
	def validate_montant(self):
		"""Valide que le montant est positif."""
		if self.montant <= 0:
			frappe.throw("Le montant doit être positif")
	

	
	def set_soldes(self):
		"""Calcule et définit les soldes avant et après le mouvement."""
		from immo.immo.doctype.caisse.caisse import Caisse
		
		# Récupérer le solde actuel de la caisse
		self.solde_avant = Caisse.get_solde_actuel()
		
		# Calculer le nouveau solde
		if self.type_mouvement == "Entrée":
			self.solde_apres = self.solde_avant + self.montant
		else:  # Sortie
			self.solde_apres = self.solde_avant - self.montant
			
			# Vérifier que le solde ne devient pas négatif
			if self.solde_apres < 0:
				frappe.throw(f"Solde insuffisant. Solde actuel: {self.solde_avant}, Montant demandé: {self.montant}")
	
	def on_submit(self):
		"""Actions après soumission du document."""
		self.update_caisse_solde()
	
	def on_cancel(self):
		"""Actions après annulation du document."""
		self.reverse_caisse_solde()
	
	def update_caisse_solde(self):
		"""Met à jour le solde de la caisse après le mouvement."""
		from immo.immo.doctype.caisse.caisse import Caisse
		Caisse.update_solde(self.solde_apres)
	
	def reverse_caisse_solde(self):
		"""Inverse le mouvement dans la caisse lors de l'annulation."""
		from immo.immo.doctype.caisse.caisse import Caisse
		Caisse.update_solde(self.solde_avant)
	
	def after_insert(self):
		"""Actions après insertion du document."""
		# Calculer les soldes avant et après AVANT de mettre à jour la caisse
		self.set_soldes()
		self.save()
		# Maintenant mettre à jour le solde de la caisse
		self.update_caisse_solde()
	
	@staticmethod
	def create_mouvement(type_mouvement, montant, notes=None, 
						 reference_doctype=None, reference_docname=None):
		"""Crée un nouveau mouvement de caisse."""
		mouvement = frappe.new_doc("Mouvement Caisse")
		mouvement.type_mouvement = type_mouvement
		mouvement.montant = montant
		mouvement.date_mouvement = now()
		mouvement.notes = notes
		mouvement.reference_doctype = reference_doctype
		mouvement.reference_docname = reference_docname
		
		mouvement.insert()
		return mouvement