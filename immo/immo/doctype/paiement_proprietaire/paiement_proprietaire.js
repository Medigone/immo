// Copyright (c) 2025, IntraPro and contributors
// For license information, please see license.txt

frappe.ui.form.on("Paiement Proprietaire", {
	refresh(frm) {
		if (!frm.doc.__islocal) {
			add_status_buttons(frm);
		}
	}
});

/**
 * Ajoute les boutons de statut dans la barre d'outils
 * @param {Object} frm - L'objet formulaire Frappe
 */
function add_status_buttons(frm) {
	// Supprimer les boutons existants pour éviter les doublons
	frm.remove_custom_button(__("Statut"));
	
	// Créer le groupe de boutons pour le statut
	frm.add_custom_button(__("Nouveau"), function() {
		change_status(frm, "Nouveau");
	}, __("Statut"));
	
	frm.add_custom_button(__("Payé"), function() {
		change_status(frm, "Payé");
	}, __("Statut"));
	
	frm.add_custom_button(__("Annulé"), function() {
		change_status(frm, "Annulé");
	}, __("Statut"));
	
	// Mettre en évidence le statut actuel
	highlight_current_status(frm);
}

/**
 * Change le statut du paiement avec validation
 * @param {Object} frm - L'objet formulaire Frappe
 * @param {string} new_status - Le nouveau statut
 */
function change_status(frm, new_status) {
	if (frm.doc.status === new_status) {
		frappe.msgprint(__("Le paiement a déjà le statut: {0}", [new_status]));
		return;
	}
	
	// Demander confirmation pour les changements critiques
	let confirmation_needed = false;
	let confirmation_message = "";
	
	if (frm.doc.status === "Payé" && new_status !== "Payé") {
		confirmation_needed = true;
		confirmation_message = `Êtes-vous sûr de vouloir changer le statut d'un paiement payé vers '${new_status}' ?`;
	}
	
	if (new_status === "Annulé") {
		confirmation_needed = true;
		confirmation_message = "Êtes-vous sûr de vouloir annuler ce paiement ?";
	}
	
	if (confirmation_needed) {
		frappe.confirm(
			confirmation_message,
			function() {
				update_status(frm, new_status);
			}
		);
	} else {
		update_status(frm, new_status);
	}
}

/**
 * Met à jour le statut et sauvegarde le document
 * @param {Object} frm - L'objet formulaire Frappe
 * @param {string} new_status - Le nouveau statut
 */
function update_status(frm, new_status) {
	frm.set_value("status", new_status);
	frm.save().then(() => {
		frappe.show_alert({
			message: __("Statut mis à jour vers: {0}", [new_status]),
			indicator: "green"
		});
		add_status_buttons(frm);
	}).catch((error) => {
		frappe.msgprint({
			title: __("Erreur"),
			message: __("Impossible de mettre à jour le statut: {0}", [error.message]),
			indicator: "red"
		});
	});
}

/**
 * Met en évidence le bouton du statut actuel
 * @param {Object} frm - L'objet formulaire Frappe
 */
function highlight_current_status(frm) {
	// Attendre que les boutons soient créés
	setTimeout(() => {
		// Supprimer toutes les classes de statut existantes
		$('.btn-group .btn').removeClass('btn-primary btn-success btn-danger');
		
		// Ajouter la classe appropriée selon le statut actuel
		const status_classes = {
			"Nouveau": "btn-primary",
			"Payé": "btn-success",
			"Annulé": "btn-danger"
		};
		
		const current_status = frm.doc.status;
		if (status_classes[current_status]) {
			$('.btn-group .btn:contains("' + current_status + '")').addClass(status_classes[current_status]);
		}
	}, 100);
}
