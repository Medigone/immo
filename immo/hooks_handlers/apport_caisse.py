import frappe
from frappe.utils import now

def on_cancel(doc, method):
	"""Hook appelé lors de l'annulation d'un Apport Caisse."""
	frappe.logger().info(f"Hook on_cancel appelé pour Apport Caisse {doc.name}, docstatus: {doc.docstatus}")
	
	# Rechercher le mouvement de caisse associé à cet apport
	frappe.logger().info(f"Recherche des mouvements pour Apport Caisse {doc.name}")
	
	mouvements = frappe.get_all("Mouvement Caisse", 
		filters={
			"reference_doctype": "Apport Caisse",
			"reference_docname": doc.name,
			"docstatus": 1  # Seulement les mouvements soumis
		},
		fields=["name"]
	)
	
	frappe.logger().info(f"Trouvé {len(mouvements)} mouvements à annuler")
	
	# Annuler tous les mouvements associés
	for mouvement_data in mouvements:
		frappe.logger().info(f"Annulation du mouvement {mouvement_data.name}")
		mouvement = frappe.get_doc("Mouvement Caisse", mouvement_data.name)
		mouvement.cancel()
		frappe.msgprint(f"Mouvement de caisse annulé: {mouvement.name}")
	
	# Mettre à jour le statut
	doc.status = "Annulé"