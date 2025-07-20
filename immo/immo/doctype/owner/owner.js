// Copyright (c) 2024, Immo and contributors
// For license information, please see license.txt

frappe.ui.form.on('Owner', {
	refresh: function(frm) {
		// Actions personnalisées lors du rafraîchissement
		if (frm.doc.full_name) {
			frm.add_custom_button(__('Voir appartements'), function() {
				frappe.set_route('List', 'Apartment', {'owner': frm.doc.name});
			});
		}
	},
	

}); 