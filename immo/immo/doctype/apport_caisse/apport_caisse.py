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
	
	def on_cancel(self):
		"""Actions après annulation du document."""
		# Si l'apport était confirmé, créer un mouvement de caisse inverse
		if self.status == "Confirmé":
			from immo.immo.doctype.mouvement_caisse.mouvement_caisse import MouvementCaisse
			
			# Créer un mouvement de sortie pour compenser l'annulation de l'apport
			mouvement = MouvementCaisse.create_mouvement(
				type_mouvement="Sortie",
				montant=self.montant,
				notes=f"Annulation apport - {self.motif or 'Aucun motif spécifié'}",
				reference_doctype="Apport Caisse",
				reference_docname=f"{self.name}-ANNULE"
			)
			
			# Sauvegarder le mouvement (pas de submit car non soumissible)
			mouvement.save()
		
		self.status = "Annulé"
	
	def create_mouvement_caisse(self):
		"""Crée un mouvement de caisse pour cet apport."""
		from immo.immo.doctype.mouvement_caisse.mouvement_caisse import MouvementCaisse
		
		# Créer le mouvement de caisse
		mouvement = MouvementCaisse.create_mouvement(
			type_mouvement="Entrée",
			montant=self.montant,
			notes=f"Apport manuel - {self.motif or 'Aucun motif spécifié'}",
			reference_doctype="Apport Caisse",
			reference_docname=self.name
		)
		
		# Sauvegarder le mouvement (pas de submit car non soumissible)
		mouvement.save()
		
		return mouvement
	
	@frappe.whitelist()
	def confirmer_apport(self):
		"""Confirme l'apport et crée le mouvement de caisse."""
		if self.status != "Nouveau":
			frappe.throw("Seuls les apports avec le statut 'Nouveau' peuvent être confirmés")
		
		self.status = "Confirmé"
		self.date_validation = now()
		self.save()
		
		# Créer le mouvement de caisse
		self.create_mouvement_caisse()
		
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