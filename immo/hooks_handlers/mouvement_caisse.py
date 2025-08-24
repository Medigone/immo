import frappe
from frappe.utils import now

def on_cancel(doc, method):
	"""Hook appelé lors de l'annulation d'un Mouvement Caisse."""
	# Le mouvement de caisse a déjà sa propre logique on_cancel() dans le DocType
	# qui appelle reverse_caisse_solde() pour restaurer le solde précédent
	# Ce hook peut être utilisé pour des actions supplémentaires si nécessaire
	
	# Log de l'annulation pour traçabilité
	frappe.logger().info(f"Mouvement Caisse {doc.name} annulé - Solde restauré de {doc.solde_apres} à {doc.solde_avant}")
	
	# Optionnel: Notifier l'utilisateur
	frappe.msgprint(f"Mouvement de caisse {doc.name} annulé avec succès. Solde restauré.")