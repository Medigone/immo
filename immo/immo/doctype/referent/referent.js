// Copyright (c) 2025, IntraPro and contributors
// For license information, please see license.txt

frappe.ui.form.on("Referent", {
	refresh(frm) {
		// Rafraîchir le tableau de bord des commissions
		if (frm.doc.name) {
			frm.trigger('update_dashboard');
		}
	},
	
	update_dashboard(frm) {
		// Appeler la méthode pour générer le HTML du tableau de bord
		frappe.call({
			method: 'get_dashboard_html',
			doc: frm.doc,
			callback: function(r) {
				if (r.message) {
					// Mettre à jour le contenu du champ HTML
					frm.get_field('html_dashboard').$wrapper.html(r.message);
				}
			}
		});
	},
	
	// Rafraîchir le tableau de bord quand certains champs changent
	nom_complet(frm) {
		if (frm.doc.name) {
			frm.trigger('update_dashboard');
		}
	},
	
	actif(frm) {
		if (frm.doc.name) {
			frm.trigger('update_dashboard');
		}
	}
});

// Rafraîchir le tableau de bord après sauvegarde
frappe.ui.form.on("Referent", "after_save", function(frm) {
	setTimeout(function() {
		frm.trigger('update_dashboard');
	}, 1000);
});
