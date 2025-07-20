// Copyright (c) 2024, Immo and contributors
// For license information, please see license.txt

frappe.ui.form.on('Apartment', {
	refresh: function(frm) {
		// Actions personnalisées lors du rafraîchissement
		if (frm.doc.owner) {
			frm.add_custom_button(__('Voir réservations'), function() {
				frappe.set_route('List', 'Booking', {'apartment': frm.doc.name});
			});
			
			frm.add_custom_button(__('Voir propriétaire'), function() {
				frappe.set_route('Form', 'Owner', frm.doc.owner);
			});
		} else {
			frm.add_custom_button(__('Créer un propriétaire'), function() {
				frappe.new_doc('Owner');
			});
		}
	},
	
	owner: function(frm) {
		// Charger les informations du propriétaire
		if (frm.doc.owner) {
			frappe.call({
				method: 'frappe.client.get',
				args: {
					doctype: 'Owner',
					name: frm.doc.owner
				},
				callback: function(r) {
					if (r.message) {
						// Vous pouvez ajouter des champs calculés ici
						frm.refresh();
					}
				}
			});
		}
	},
	
	default_price_per_night: function(frm) {
		// Validation côté client
		if (frm.doc.default_price_per_night && frm.doc.default_price_per_night <= 0) {
			frappe.msgprint({
				title: __('Erreur'),
				message: __('Le prix par nuit par défaut doit être supérieur à 0.'),
				indicator: 'red'
			});
		}
	},
	
	custom_price: function(frm) {
		// Validation côté client
		if (frm.doc.custom_price && frm.doc.custom_price <= 0) {
			frappe.msgprint({
				title: __('Erreur'),
				message: __('Le prix personnalisé doit être supérieur à 0.'),
				indicator: 'red'
			});
		}
	},
	
	is_available: function(frm) {
		// Vérifier les réservations actives si on marque comme indisponible
		if (!frm.doc.is_available) {
			frappe.call({
				method: 'frappe.client.get_list',
				args: {
					doctype: 'Booking',
					filters: {
						apartment: frm.doc.name,
						status: 'Confirmed'
					}
				},
				callback: function(r) {
					if (r.message && r.message.length > 0) {
						frappe.msgprint({
							title: __('Attention'),
							message: __('Il y a des réservations actives pour cet appartement.'),
							indicator: 'orange'
						});
					}
				}
			});
		}
	}
}); 