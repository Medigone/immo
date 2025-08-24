# Copyright (c) 2024, Wezri and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now


class ApportCaisse(Document):
	"""DocType pour la gestion des apports manuels en caisse."""
	
	def validate(self):
		"""Validation du document Apport Caisse."""
		self.validate_montant()
	
	def validate_montant(self):
		"""Valide que le montant est positif."""
		if self.montant <= 0:
			frappe.throw("Le montant doit être positif")
	
	def on_submit(self):
		"""Actions après soumission du document."""
		if self.status == "Confirmé":
			self.create_mouvement_caisse()
			self.date_validation = now()
	

	
	def create_mouvement_caisse(self):
		"""Crée un mouvement de caisse pour cet apport."""
		from immo.immo.doctype.mouvement_caisse.mouvement_caisse import MouvementCaisse
		
		# Créer le mouvement de caisse
		mouvement = MouvementCaisse.create_mouvement(
			type_mouvement="Entrée",
			montant=self.montant,
			notes=f"Apport - {self.motif or 'Aucun motif spécifié'}",
			reference_doctype="Apport Caisse",
			reference_docname=self.name
		)
		
		# Soumettre le mouvement (maintenant submittable)
		mouvement.submit()
		
		frappe.msgprint(f"Mouvement de caisse créé et soumis: {mouvement.name}")
		
		return mouvement
	
	@frappe.whitelist()
	def confirmer_apport(self):
		"""Confirme l'apport et crée le mouvement de caisse."""
		if self.status != "Nouveau":
			frappe.throw("Seuls les apports avec le statut 'Nouveau' peuvent être confirmés")
		
		self.status = "Confirmé"
		self.date_validation = now()
		self.submit()  # Ceci appelle on_submit() qui crée déjà le mouvement
		
		frappe.msgprint(f"Apport de {self.montant} confirmé avec succès")
	
	@staticmethod
	def create_apport(montant, motif=None, date=None):
		"""Crée un nouveau document Apport Caisse."""
		apport = frappe.new_doc("Apport Caisse")
		apport.montant = montant
		apport.motif = motif
		apport.date = date or frappe.utils.today()
		apport.status = "Nouveau"
		
		apport.insert()
		return apport