// Copyright (c) 2024, Immo and contributors
// For license information, please see license.txt

frappe.ui.form.on('Booking', {
	refresh: function(frm) {
		// Actions personnalisées lors du rafraîchissement
		if (frm.doc.apartment) {
			frm.add_custom_button(__('Voir appartement'), function() {
				frappe.set_route('Form', 'Apartment', frm.doc.apartment);
			});
		}
		
		if (frm.doc.guest) {
			frm.add_custom_button(__('Voir invité'), function() {
				frappe.set_route('Form', 'User', frm.doc.guest);
			});
		}
		
		// Boutons d'action selon le statut
		if (frm.doc.status === 'Pending') {
			frm.add_custom_button(__('Confirmer'), function() {
				frm.set_value('status', 'Confirmed');
				frm.save();
			}, __('Actions'));
			
			frm.add_custom_button(__('Annuler'), function() {
				frm.set_value('status', 'Cancelled');
				frm.save();
			}, __('Actions'));
		}
	},
	
	apartment: function(frm) {
		// Charger les informations de l'appartement
		if (frm.doc.apartment) {
			frappe.call({
				method: 'frappe.client.get',
				args: {
					doctype: 'Apartment',
					name: frm.doc.apartment
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
	
	start_date: function(frm) {
		frm.trigger('calculate_dates');
	},
	
	end_date: function(frm) {
		frm.trigger('calculate_dates');
	},
	
	calculate_dates: function(frm) {
		// Calculer le nombre de nuits côté client
		if (frm.doc.start_date && frm.doc.end_date) {
			var start = new Date(frm.doc.start_date);
			var end = new Date(frm.doc.end_date);
			var diffTime = Math.abs(end - start);
			var diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
			
			if (diffDays > 0) {
				frm.set_value('total_nights', diffDays);
			}
		}
	},
	
	status: function(frm) {
		// Validation du changement de statut
		if (frm.doc.status === 'Cancelled') {
			frappe.msgprint({
				title: __('Confirmation'),
				message: __('Êtes-vous sûr de vouloir annuler cette réservation ?'),
				indicator: 'orange'
			});
		}
	}
}); 