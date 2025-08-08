// Copyright (c) 2025, IntraPro and contributors
// For license information, please see license.txt

frappe.ui.form.on('Location Courte Duree', {
	refresh: function(frm) {
		// Afficher le type de location calculé automatiquement
		update_type_location_display(frm);
	},
	
	location_bloc_id: function(frm) {
		// Mettre à jour l'affichage du type de location quand le bloc change
		update_type_location_display(frm);
		
		// Si une location bloc est sélectionnée, récupérer les informations du bloc
		if (frm.doc.location_bloc_id) {
			frappe.call({
				method: 'frappe.client.get',
				args: {
					doctype: 'Location Bloc',
					name: frm.doc.location_bloc_id
				},
				callback: function(r) {
					if (r.message) {
						const bloc = r.message;
						
						// Vérifier la cohérence de l'appartement
						if (frm.doc.appartement_id && bloc.appartement_id !== frm.doc.appartement_id) {
							frappe.msgprint({
								title: 'Attention',
								message: 'L\'appartement sélectionné ne correspond pas à celui de la location bloc.',
								indicator: 'orange'
							});
						} else if (!frm.doc.appartement_id) {
							// Auto-remplir l'appartement si pas encore défini
							frm.set_value('appartement_id', bloc.appartement_id);
						}
						
						// Afficher des informations sur le bloc
						frappe.msgprint({
							title: 'Location Bloc sélectionnée',
							message: `Type de location automatiquement défini sur <strong>Sous-location</strong><br>
									 Période du bloc: ${bloc.date_debut_bloc} au ${bloc.date_fin_bloc}`,
							indicator: 'blue'
						});
					}
				}
			});
		}
	},
	
	appartement_id: function(frm) {
		// Vérifier la cohérence avec la location bloc si elle existe
		if (frm.doc.location_bloc_id && frm.doc.appartement_id) {
			frappe.call({
				method: 'frappe.client.get',
				args: {
					doctype: 'Location Bloc',
					name: frm.doc.location_bloc_id
				},
				callback: function(r) {
					if (r.message && r.message.appartement_id !== frm.doc.appartement_id) {
						frappe.msgprint({
							title: 'Attention',
							message: 'L\'appartement sélectionné ne correspond pas à celui de la location bloc.',
							indicator: 'orange'
						});
					}
				}
			});
		}
	}
});

function update_type_location_display(frm) {
	// Calculer et afficher le type de location
	const type_location = frm.doc.location_bloc_id ? 'Sous-location' : 'Directe';
	
	// Mettre à jour le champ caché
	frm.set_value('type_location', type_location);
	
	// Afficher une indication visuelle du type de location
	if (frm.doc.location_bloc_id) {
		frm.dashboard.add_indicator(__('Type: Sous-location'), 'blue');
	} else {
		frm.dashboard.add_indicator(__('Type: Location directe'), 'green');
	}
}
