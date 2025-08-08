frappe.ui.form.on('Location Bloc', {
	refresh: function(frm) {
		console.log("Location Bloc refresh triggered");
		// Ajouter un bouton pour créer un paiement bloc
		if (frm.doc.name) {
			frm.add_custom_button(__('Créer Paiement Bloc'), function() {
				// Créer un dialogue pour saisir les informations de paiement
				let dialog = new frappe.ui.Dialog({
					title: __('Créer un Paiement Bloc'),
					fields: [
						{
							fieldname: 'montant_paiement',
							label: __('Montant du Paiement'),
							fieldtype: 'Currency',
							default: frm.doc.solde_restant && frm.doc.solde_restant < frm.doc.montant_total_proprietaire ? frm.doc.solde_restant : frm.doc.montant_total_proprietaire,
							reqd: 1
						},
						{
							fieldname: 'date_paiement',
							label: __('Date de Paiement'),
							fieldtype: 'Date',
							default: frappe.datetime.get_today(),
							reqd: 1
						},
						{
							fieldname: 'type_paiement',
							label: __('Type de Paiement'),
							fieldtype: 'Select',
							options: 'Avance\nAcompte\nSolde\nUnique',
							default: 'Unique',
							reqd: 1
						},
						{
							fieldname: 'methode_paiement',
							label: __('Méthode de Paiement'),
							fieldtype: 'Select',
							options: 'Virement\nChèque\nEspèces\nCarte'
						},
						{
							fieldname: 'reference_paiement',
							label: __('Référence de Paiement'),
							fieldtype: 'Data'
						},
						{
							fieldname: 'notes',
							label: __('Notes'),
							fieldtype: 'Text Editor'
						}
					],
					primary_action_label: __('Créer Paiement'),
					primary_action: function(values) {
						frappe.call({
							method: 'frappe.client.insert',
							args: {
								doc: {
									doctype: 'Paiement Bloc',
									location_bloc_id: frm.doc.name,
									proprietaire_id: frm.doc.proprietaire_id,
									appartement_id: frm.doc.appartement_id,
									montant_paiement: values.montant_paiement,
									date_paiement: values.date_paiement,
									type_paiement: values.type_paiement,
									methode_paiement: values.methode_paiement,
									reference_paiement: values.reference_paiement,
									notes: values.notes
								}
							},
							callback: function(r) {
								if (!r.exc) {
									dialog.hide();
									frm.reload_doc();
									frappe.show_alert({
										message: __('Paiement Bloc créé avec succès'),
										indicator: 'green'
									});
								}
							}
						});
					}
				});
				dialog.show();
			});
		}
		
		// Mettre à jour l'affichage de la rentabilité
		console.log("Updating profitability display");
		frm.trigger('show_profitability_progress');
	},
	
	show_profitability_progress: function(frm) {
		// Créer une barre de progression pour la rentabilité
		let rentabilite = frm.doc.rentabilite_pourcentage || 0;
		
		// Déterminer la couleur en fonction du niveau de rentabilité
		let color = '#dc3545'; // Rouge par défaut (faible rentabilité)
		let status_text = 'Faible';
		if (rentabilite >= 20) {
			color = '#28a745'; // Vert (excellente rentabilité)
			status_text = 'Excellente';
		} else if (rentabilite >= 15) {
			color = '#17a2b8'; // Bleu (très bonne rentabilité)
			status_text = 'Très bonne';
		} else if (rentabilite >= 10) {
			color = '#ffc107'; // Jaune (bonne rentabilité)
			status_text = 'Bonne';
		} else if (rentabilite >= 5) {
			color = '#fd7e14'; // Orange (rentabilité modérée)
			status_text = 'Modérée';
		}
		
		// Limiter la largeur de la barre à 100%
		let progress_width = Math.min(Math.abs(rentabilite), 100);
		
		// Calculer les statistiques de paiement propriétaire
		let payment_percentage = 0;
		let payment_color = '#dc3545'; // Rouge par défaut
		let payment_icon = '❌';
		let payment_status = 'Non payé';
		
		if (frm.doc.montant_total_proprietaire > 0 && frm.doc.montant_total_paye > 0) {
			payment_percentage = (frm.doc.montant_total_paye / frm.doc.montant_total_proprietaire) * 100;
			
			if (payment_percentage >= 100) {
				payment_color = '#28a745'; // Vert
				payment_icon = '✅';
				payment_status = 'Totalement payé';
			} else if (payment_percentage > 0) {
				payment_color = '#fd7e14'; // Orange
				payment_icon = '⚠️';
				payment_status = 'Partiellement payé';
			}
		}
		
		let payment_progress_width = Math.min(payment_percentage, 100);

		// Calculer les statistiques de paiement locataires
		let tenant_payment_percentage = 0;
		let tenant_payment_color = '#dc3545'; // Rouge par défaut
		let tenant_payment_icon = '❌';
		let tenant_payment_status = 'Aucun paiement';
		
		if (frm.doc.paiements_prevus > 0 && frm.doc.total_encaisse > 0) {
			tenant_payment_percentage = (frm.doc.total_encaisse / frm.doc.paiements_prevus) * 100;
			
			if (tenant_payment_percentage >= 100) {
				tenant_payment_color = '#28a745'; // Vert
				tenant_payment_icon = '✅';
				tenant_payment_status = 'Totalement encaissé';
			} else if (tenant_payment_percentage > 0) {
				tenant_payment_color = '#fd7e14'; // Orange
				tenant_payment_icon = '⚠️';
				tenant_payment_status = 'Partiellement encaissé';
			}
		}
		
		let tenant_progress_width = Math.min(tenant_payment_percentage, 100);
		
		// Créer le HTML consolidé avec 3 sections distinctes
		let consolidated_html = `
			<div style="margin: 10px 0; display: flex; flex-direction: column; gap: 15px;">
				<!-- Rentabilité -->
				<div class="alert" style="padding: 15px; border: 1px solid ${color}; border-radius: 4px;">
					<div style="margin-bottom: 10px;">
						<div style="display: flex; justify-content: space-between; align-items: center;">
							<span style="font-weight: bold;">📈 Rentabilité</span>
							<span style="color: ${color};">${status_text}</span>
						</div>
						<div style="background: #f8f9fa; height: 20px; border-radius: 10px; margin: 10px 0;">
							<div style="width: ${progress_width}%; background-color: ${color}; height: 100%; border-radius: 10px; transition: width 0.5s ease-in-out;"></div>
						</div>
						<div style="text-align: right; color: ${color}; font-weight: bold;">${rentabilite.toFixed(1)}%</div>
					</div>
					<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
						<div>
							<div style="color: #6c757d; margin-bottom: 2px;">💰 Montant total</div>
							<div style="font-weight: bold;">${format_currency(frm.doc.montant_total_proprietaire || 0, 'EUR')}</div>
						</div>
						<div>
							<div style="color: #6c757d; margin-bottom: 2px;">📊 Marge réelle</div>
							<div style="font-weight: bold; color: ${(frm.doc.marge_totale || 0) >= 0 ? '#28a745' : '#dc3545'};">${format_currency(frm.doc.marge_totale || 0, 'EUR')}</div>
						</div>
					</div>
				</div>

				<!-- Paiements au propriétaire -->
				<div class="alert" style="padding: 15px; border: 1px solid ${payment_color}; border-radius: 4px;">
					<div style="display: flex; justify-content: space-between; align-items: center;">
						<span style="font-weight: bold;">💳 Paiements au propriétaire</span>
						<span style="color: ${payment_color};">${payment_icon} ${payment_status}</span>
					</div>
					<div style="background: #f8f9fa; height: 20px; border-radius: 10px; margin: 10px 0;">
						<div style="width: ${payment_progress_width}%; background-color: ${payment_color}; height: 100%; border-radius: 10px; transition: width 0.5s ease-in-out;"></div>
					</div>
					<div style="text-align: right; color: ${payment_color}; font-weight: bold;">${format_currency(frm.doc.montant_total_paye || 0, 'EUR')} / ${format_currency(frm.doc.montant_total_proprietaire || 0, 'EUR')}</div>
				</div>

				<!-- Paiements des locataires -->
				<div class="alert" style="padding: 15px; border: 1px solid ${tenant_payment_color}; border-radius: 4px;">
					<div style="display: flex; justify-content: space-between; align-items: center;">
						<span style="font-weight: bold;">💰 Paiements reçus des locataires</span>
						<span style="color: ${tenant_payment_color};">${tenant_payment_icon} ${tenant_payment_status}</span>
					</div>
					<div style="background: #f8f9fa; height: 20px; border-radius: 10px; margin: 10px 0;">
						<div style="width: ${tenant_progress_width}%; background-color: ${tenant_payment_color}; height: 100%; border-radius: 10px; transition: width 0.5s ease-in-out;"></div>
					</div>
					<div style="text-align: right; color: ${tenant_payment_color}; font-weight: bold;">${format_currency(frm.doc.total_encaisse || 0, 'EUR')} / ${format_currency(frm.doc.paiements_prevus || 0, 'EUR')}</div>
				</div>
			</div>
		`;
		
		// Injecter le HTML dans le champ HTML dédié
		console.log("Injecting HTML into rentabilite-progress-container");
		if (frm.fields_dict['rentabilite_progress_html']) {
			$(frm.fields_dict['rentabilite_progress_html'].wrapper)
				.find("#rentabilite-progress-container")
				.html(consolidated_html);
		} else {
			console.error("rentabilite_progress_html field not found");
		}
	}
});

// Formatage personnalisé pour les champs monétaires
function format_currency(value, currency) {
	return frappe.format(value, {
		fieldtype: 'Currency',
		currency: currency
	});
}
