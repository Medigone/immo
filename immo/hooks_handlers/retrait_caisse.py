import frappe
from frappe.utils import now

def on_cancel(doc, method):
	"""Hook appelé lors de l'annulation d'un Retrait Caisse."""
	# Rechercher le mouvement de caisse associé à ce retrait
	mouvements = frappe.get_all("Mouvement Caisse", 
		filters={
			"reference_doctype": "Retrait Caisse",
			"reference_docname": doc.name,
			"docstatus": 1  # Seulement les mouvements soumis
		},
		fields=["name"]
	)
	
	# Annuler tous les mouvements associés
	for mouvement_data in mouvements:
		mouvement = frappe.get_doc("Mouvement Caisse", mouvement_data.name)
		mouvement.cancel()
		frappe.msgprint(f"Mouvement de caisse annulé: {mouvement.name}")
	
	# Mettre à jour le statut
	doc.status = "Annulé"