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
		self.validate_type_mouvement()
		self.set_soldes()
	
	def validate_montant(self):
		"""Valide que le montant est positif."""
		if self.montant <= 0:
			frappe.throw("Le montant doit être positif")
	
	def validate_type_mouvement(self):
		"""Valide la cohérence entre type_mouvement et type_transaction."""
		entrees = ["Paiement locataire", "Apport manuel"]
		sorties = ["Paiement propriétaire", "Commission référent", "Charge", "Paiement bloc", "Retrait manuel"]
		
		if self.type_transaction in entrees and self.type_mouvement != "Entrée":
			frappe.throw(f"Le type de transaction '{self.type_transaction}' doit être une Entrée")
		
		if self.type_transaction in sorties and self.type_mouvement != "Sortie":
			frappe.throw(f"Le type de transaction '{self.type_transaction}' doit être une Sortie")
	
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
	
	@staticmethod
	def create_mouvement(type_mouvement, type_transaction, montant, description=None, 
						 reference_doctype=None, reference_docname=None, reference_externe=None):
		"""Crée un nouveau mouvement de caisse."""
		mouvement = frappe.new_doc("Mouvement Caisse")
		mouvement.type_mouvement = type_mouvement
		mouvement.type_transaction = type_transaction
		mouvement.montant = montant
		mouvement.date_mouvement = now()
		mouvement.description = description
		mouvement.reference_doctype = reference_doctype
		mouvement.reference_docname = reference_docname
		mouvement.reference_externe = reference_externe
		
		mouvement.insert()
		return mouvement