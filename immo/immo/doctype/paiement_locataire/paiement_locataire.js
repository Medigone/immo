// Copyright (c) 2025, IntraPro and contributors
// For license information, please see license.txt

frappe.ui.form.on("Paiement Locataire", {
	refresh(frm) {
		// Ajouter le groupe de boutons Statut
		if (!frm.doc.__islocal) {
			add_status_buttons(frm);
		}
	}
});

function add_status_buttons(frm) {
	// Supprimer les boutons existants du groupe Statut s'ils existent
	frm.remove_custom_button(__("Statut"));
	
	// Créer le groupe de boutons Statut
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

function change_status(frm, new_status) {
	// Vérifier si le statut est différent du statut actuel
	if (frm.doc.status === new_status) {
		frappe.msgprint({
			title: __("Information"),
			message: __("Le paiement a déjà le statut '{0}'", [new_status]),
			indicator: "blue"
		});
		return;
	}
	
	// Demander confirmation pour les changements critiques
	let confirmation_needed = false;
	let confirmation_message = "";
	
	if (frm.doc.status === "Payé" && new_status !== "Payé") {
		confirmation_needed = true;
		confirmation_message = __("Êtes-vous sûr de vouloir changer le statut d'un paiement payé vers '{0}' ?", [new_status]);
	} else if (new_status === "Annulé") {
		confirmation_needed = true;
		confirmation_message = __("Êtes-vous sûr de vouloir annuler ce paiement ?");
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

function update_status(frm, new_status) {
	// Mettre à jour le statut
	frm.set_value("status", new_status);
	
	// Sauvegarder automatiquement
	frm.save().then(() => {
		frappe.show_alert({
			message: __("Statut mis à jour vers '{0}'", [new_status]),
			indicator: "green"
		});
		
		// Rafraîchir les boutons pour mettre en évidence le nouveau statut
		add_status_buttons(frm);
	}).catch((error) => {
		frappe.msgprint({
			title: __("Erreur"),
			message: __("Erreur lors de la mise à jour du statut: {0}", [error.message || error]),
			indicator: "red"
		});
	});
}

function highlight_current_status(frm) {
	// Mettre en évidence le bouton du statut actuel
	const current_status = frm.doc.status;
	
	// Supprimer les classes de mise en évidence existantes
	$('.btn-group .btn').removeClass('btn-primary btn-success btn-danger');
	
	// Ajouter la classe appropriée selon le statut
	setTimeout(() => {
		const status_colors = {
			"Nouveau": "btn-primary",
			"Payé": "btn-success", 
			"Annulé": "btn-danger"
		};
		
		if (status_colors[current_status]) {
			$(`.btn-group .btn:contains('${current_status}')`).addClass(status_colors[current_status]);
		}
	}, 100);
}
