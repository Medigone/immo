// Copyright (c) 2025, IntraPro and contributors
// For license information, please see license.txt

// Location Courte Duree JavaScript - Dashboard des paiements
frappe.ui.form.on('Location Courte Duree', {
	onload: function (frm) {
		frm.trigger('update_dashboard');
		
		// Écouter les mises à jour en temps réel
		frappe.realtime.on('location_courte_duree_updated', (data) => {
			if (data.docname === frm.doc.name) {
				frappe.show_alert('Mise à jour des paiements détectée, rafraîchissement...', 3);
				setTimeout(() => {
					frm.reload_doc();
				}, 1000);
			}
		});
	},

	validate: function (frm) {
		frm.trigger('update_dashboard');
	},

	refresh: function(frm) {
		// Vérifier que frm et frm.doc existent avant de continuer
		if (!frm || !frm.doc) return;
		
		// Ajouter les boutons de création de paiements
		if (!frm.doc.__islocal) {
			frm.add_custom_button(__('Paiement Locataire'), function() {
				create_paiement_locataire(frm);
			}, __('Créer'));
			
			frm.add_custom_button(__('Paiement Propriétaire'), function() {
				create_paiement_proprietaire(frm);
			}, __('Créer'));
			
			// Les champs de suivi des paiements sont mis à jour automatiquement
			// via les hooks doc_events lors de la création/modification des paiements
		}

		frm.trigger('update_dashboard');
	},

	after_save: function(frm) {
		frm.trigger('update_dashboard');
	},

	// Mettre à jour le dashboard quand les montants changent
	montant_total_locataire: function(frm) {
		frm.trigger('update_dashboard');
	},

	montant_total_proprietaire: function(frm) {
		frm.trigger('update_dashboard');
	},

	update_dashboard: function(frm) {
		if (!frm || !frm.doc || !frm.doc.name) return;
		
		// Afficher un placeholder pendant le chargement
		let loading_html = `
			<div style="
				display: flex;
				justify-content: center;
				align-items: center;
				height: 200px;
				font-family: 'Inter', sans-serif;
				color: #6b7280;
			">
				<div>Chargement du dashboard...</div>
			</div>
		`;
		
		if (frm.fields_dict && frm.fields_dict['dashboard']) {
			$(frm.fields_dict['dashboard'].wrapper).html(loading_html);
		}
		
		// Charger les données du dashboard
		frm.trigger('load_dashboard_data');
	},

	load_dashboard_data: function(frm) {
		if (!frm || !frm.doc || !frm.doc.name) return;
		
		// Générer le dashboard directement avec les données disponibles
		const dashboard_html = createLocationCourteDureeDashboard(frm.doc);
		if (frm.fields_dict && frm.fields_dict['dashboard']) {
			$(frm.fields_dict['dashboard'].wrapper).html(dashboard_html);
		}
	},

	location_bloc_id: function(frm) {
		// Mettre à jour l'affichage du type de location
		update_type_location_display(frm);
	},

	appartement_id: function(frm) {
		// Mettre à jour l'affichage du type de location
		update_type_location_display(frm);
	},

	date_debut: function(frm) {
		// Mettre à jour l'affichage du type de location
		update_type_location_display(frm);
	},

	date_fin: function(frm) {
		// Mettre à jour l'affichage du type de location
		update_type_location_display(frm);
	}
});

// Fonction pour créer le dashboard de Location Courte Durée
function createLocationCourteDureeDashboard(doc) {
	try {
		// Récupérer les valeurs
		const montant_total_loc = doc.montant_total_locataire || 0;
		const montant_paye_loc = doc.montant_paye_locataire || 0;
		const montant_restant_loc = doc.montant_restant_locataire || 0;
		const statut_loc = doc.statut_paiement_locataire || "En attente";
		
		const montant_total_prop = doc.montant_total_proprietaire || 0;
		const montant_paye_prop = doc.montant_paye_proprietaire || 0;
		const montant_restant_prop = doc.montant_restant_proprietaire || 0;
		const statut_prop = doc.statut_paiement_proprietaire || "En attente";
		
		// Calculer les pourcentages
		const pourcentage_loc = montant_total_loc > 0 ? (montant_paye_loc / montant_total_loc * 100) : 0;
		const pourcentage_prop = montant_total_prop > 0 ? (montant_paye_prop / montant_total_prop * 100) : 0;
		
		// Générer le HTML avec le style d'appartement
		const html = `
		<div style="
			display: grid;
			grid-template-rows: auto auto;
			gap: 16px;
			font-family: 'Inter', sans-serif;
			padding: 16px;
		">
			<!-- Ligne des 4 cartes statistiques -->
			<div style="
				display: grid;
				grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
				gap: 12px;
				align-items: stretch;
			">
				${createStatCard("Montant Total Locataire", format_currency(montant_total_loc, 'EUR'), "Montant à payer", null)}
				${createStatCard("Montant Payé Locataire", format_currency(montant_paye_loc, 'EUR'), "Montant déjà payé", pourcentage_loc)}
				${createStatCard("Montant Total Propriétaire", format_currency(montant_total_prop, 'EUR'), "Montant à verser", null)}
				${createStatCard("Montant Versé Propriétaire", format_currency(montant_paye_prop, 'EUR'), "Montant déjà versé", pourcentage_prop)}
			</div>
			
			<!-- Ligne des informations détaillées -->
			<div style="
				display: grid;
				grid-template-columns: 1fr 1fr;
				gap: 20px;
			">
				<!-- Section Locataire -->
				<div style="
					background: #fff;
					border: 1px solid #e5e7eb;
					border-radius: 10px;
					padding: 16px;
					box-shadow: 0 2px 4px rgba(0,0,0,0.05);
				">
					<div style="
						font-size: 0.9rem; 
						color: #374151; 
						margin-bottom: 12px; 
						font-weight: 600;
						display: flex;
						align-items: center;
					">
						<span style="
							width: 8px; 
							height: 8px; 
							background: #3b82f6; 
							border-radius: 50%; 
							margin-right: 8px;
						"></span>
						Paiements Locataire
					</div>
					
					<div style="font-size: 0.8rem; color: #6b7280; line-height: 1.6;">
						<div style="margin-bottom: 8px; display: flex; justify-content: space-between;">
							<span>Montant restant:</span> 
							<span style="
								color: ${montant_restant_loc > 0 ? '#dc2626' : '#16a34a'}; 
								font-weight: 600;
							">
								${montant_restant_loc.toFixed(2)} €
							</span>
						</div>
						<div style="margin-bottom: 8px; display: flex; justify-content: space-between;">
							<span>Statut:</span> 
							<span style="
								background: ${getStatusColor(statut_loc).background}; 
								color: ${getStatusColor(statut_loc).text}; 
								padding: 2px 8px; 
								border-radius: 12px; 
								font-size: 0.75rem; 
								font-weight: 600;
							">
								${statut_loc}
							</span>
						</div>

					</div>
				</div>
				
				<!-- Section Propriétaire -->
				<div style="
					background: #fff;
					border: 1px solid #e5e7eb;
					border-radius: 10px;
					padding: 16px;
					box-shadow: 0 2px 4px rgba(0,0,0,0.05);
				">
					<div style="
						font-size: 0.9rem; 
						color: #374151; 
						margin-bottom: 12px; 
						font-weight: 600;
						display: flex;
						align-items: center;
					">
						<span style="
							width: 8px; 
							height: 8px; 
							background: #16a34a; 
							border-radius: 50%; 
							margin-right: 8px;
						"></span>
						Paiements Propriétaire
					</div>
					
					<div style="font-size: 0.8rem; color: #6b7280; line-height: 1.6;">
						<div style="margin-bottom: 8px; display: flex; justify-content: space-between;">
							<span>Montant restant:</span> 
							<span style="
								color: ${montant_restant_prop > 0 ? '#dc2626' : '#16a34a'}; 
								font-weight: 600;
							">
								${montant_restant_prop.toFixed(2)} €
							</span>
						</div>
						<div style="margin-bottom: 8px; display: flex; justify-content: space-between;">
							<span>Statut:</span> 
							<span style="
								background: ${getStatusColor(statut_prop).background}; 
								color: ${getStatusColor(statut_prop).text}; 
								padding: 2px 8px; 
								border-radius: 12px; 
								font-size: 0.75rem; 
								font-weight: 600;
							">
								${statut_prop}
							</span>
						</div>

					</div>
				</div>
			</div>
		</div>
		`;
		
		return html;
		
	} catch (e) {
		console.error('Erreur lors de la génération du dashboard:', e);
		return '<div style="padding: 20px; color: #e74c3c;">Erreur lors de la génération du dashboard</div>';
	}
}

// Fonction pour créer une carte de statistique (style identique à appartement)
function createStatCard(title, mainValue, footerValue, percentage) {
	let showBadge = percentage !== null;
	let isPositive = percentage >= 0;
	let badgeColor = isPositive ? '#16a34a' : '#dc2626';
	let arrow = isPositive ? '↑' : '↓';

	return `
		<div style="
			background: #fff;
			border: 1px solid #e5e7eb;
			border-radius: 10px;
			padding: 10px 12px;
			display: flex;
			flex-direction: column;
			justify-content: flex-start;
			height: 100%;
			min-height: 120px;
			min-width: 0;
		">
			<div style="font-size: 0.8rem; color: #6b7280;">${title}</div>
			
			<div style="display: flex; align-items: center; justify-content: space-between; margin: 6px 0;">
				<div style="font-size: 1.2rem; font-weight: 700; color: #111827;">${mainValue}</div>
				${showBadge ? `<div style="
					font-size: 0.7rem;
					padding: 2px 6px;
					border-radius: 9999px;
					border: 1px solid ${badgeColor};
					color: ${badgeColor};
					background: transparent;
					white-space: nowrap;
				">
					${arrow} ${percentage.toFixed(0)}%
				</div>` : ''}
			</div>

			<div style="
				font-size: 0.75rem;
				color: #374151;
				margin-top: auto;
				white-space: nowrap;
				overflow: hidden;
				text-overflow: ellipsis;
				display: flex;
				align-items: center;
				gap: 4px;
			">
				${footerValue}
			</div>
		</div>
	`;
}

// Fonction pour formater les devises (style identique à appartement)
function format_currency(value, currency) {
	// Formatage manuel pour éviter le HTML généré par frappe.format
	if (!value) value = 0;
	const formatted = parseFloat(value).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
	return `€ ${formatted}`;
}

// Fonction pour obtenir les couleurs des statuts de paiement
function getStatusColor(status) {
	switch(status) {
		case 'Entièrement payé':
		case 'Entièrement versé':
		case 'Payé':
		case 'Versé':
			return {
				background: '#dcfce7',
				text: '#166534'
			};
		case 'Partiellement payé':
		case 'Partiellement versé':
		case 'En cours':
		case 'En attente':
		case 'Nouveau':
			return {
				background: '#fef3c7',
				text: '#92400e'
			};
		case 'Annulé':
		case 'Rejeté':
		case 'En retard':
			return {
				background: '#fee2e2',
				text: '#991b1b'
			};
		default:
			return {
				background: '#f3f4f6',
				text: '#374151'
			};
	}
}

// Fonction pour mettre à jour l'affichage du type de location
function update_type_location_display(frm) {
	if (!frm.doc.location_bloc_id || !frm.doc.appartement_id || !frm.doc.date_debut || !frm.doc.date_fin) {
		return;
	}

	// Calculer la durée en jours
	const dateDebut = new Date(frm.doc.date_debut);
	const dateFin = new Date(frm.doc.date_fin);
	const differenceTemps = dateFin.getTime() - dateDebut.getTime();
	const differenceJours = Math.ceil(differenceTemps / (1000 * 3600 * 24));

	// Déterminer le type de location
	let typeLocation = '';
	let couleur = '';
	
	if (differenceJours <= 31) {
		typeLocation = 'Court Séjour';
		couleur = '#28a745'; // Vert
	} else if (differenceJours <= 90) {
		typeLocation = 'Moyen Séjour';
		couleur = '#ffc107'; // Jaune
	} else {
		typeLocation = 'Long Séjour';
		couleur = '#dc3545'; // Rouge
	}

	// Créer le HTML pour l'affichage
	const html = `
		<div style="
			display: inline-block;
			padding: 4px 12px;
			background-color: ${couleur};
			color: white;
			border-radius: 20px;
			font-size: 12px;
			font-weight: 600;
			text-transform: uppercase;
			letter-spacing: 0.5px;
		">
			${typeLocation} (${differenceJours} jours)
		</div>
	`;

	// Mettre à jour le champ HTML
	if (frm.fields_dict['type_location_display']) {
		$(frm.fields_dict['type_location_display'].wrapper).html(html);
	}
}

// Fonction pour créer un paiement locataire
function create_paiement_locataire(frm) {
	frm.refresh(); // Ensure latest data
	const montantRestant = frm.doc.montant_restant_locataire || 0;
	
	if (montantRestant <= 0) {
		frappe.msgprint({
			title: __('Information'),
			message: __('Le montant total locataire est entièrement payé. Aucun nouveau paiement nécessaire.'),
			indicator: 'blue'
		});
		return;
	}

	const defaultData = {
		doctype: 'Paiement Locataire',
		location_courte_duree_id: frm.doc.name,
		locataire_nom: frm.doc.locataire_nom,
		locataire_email: frm.doc.locataire_email,
		montant: montantRestant,
		date_paiement: frappe.datetime.get_today(),
		type_paiement: 'Court Séjour',
		status: 'Nouveau'
	};

	const dialog = new frappe.ui.Dialog({
		title: __('Créer un Paiement Locataire'),
		fields: [
			{
				fieldname: 'locataire_nom',
				label: __('Nom du locataire'),
				fieldtype: 'Data',
				default: defaultData.locataire_nom,
				reqd: 1
			},
			{
				fieldname: 'montant',
				label: __('Montant'),
				fieldtype: 'Currency',
				default: defaultData.montant,
				reqd: 1
			},
			{
				fieldname: 'date_paiement',
				label: __('Date de paiement'),
				fieldtype: 'Date',
				default: defaultData.date_paiement,
				reqd: 1
			},
			{
				fieldname: 'type_paiement',
				label: __('Type de paiement'),
				fieldtype: 'Select',
				options: 'Court Séjour\nSéjour moyen\nSéjour long',
				default: defaultData.type_paiement,
				reqd: 1
			},
			{
				fieldtype: 'HTML',
				fieldname: 'info_montant',
				label: __('Information'),
				options: `<div style="padding: 8px; background-color: #f8f9fa; border-radius: 4px; border-left: 4px solid #007cba;">
					<strong>Montant total:</strong> ${frm.doc.montant_total_locataire || 0} €<br>
					<strong>Montant déjà payé:</strong> ${frm.doc.montant_paye_locataire || 0} €<br>
					<strong>Montant restant:</strong> <span style="color: #007cba; font-weight: bold;">${montantRestant} €</span>
				</div>`
			}
		],
		primary_action_label: __('Créer'),
		primary_action: function(values) {
			const currentMontantRestant = frm.doc.montant_restant_locataire || frm.doc.montant_total_locataire || 0;
			if (values.montant > currentMontantRestant) {
				frappe.msgprint({
					title: __('Attention'),
					message: __('Le montant saisi (${values.montant} €) dépasse le montant restant à payer (${currentMontantRestant} €).'),
					indicator: 'orange'
				});
				return;
			}

			frappe.call({
				method: 'frappe.client.insert',
				args: {
					doc: {
						doctype: 'Paiement Locataire',
						location_courte_duree_id: frm.doc.name,
						locataire_nom: values.locataire_nom,
						locataire_email: values.locataire_email,
						montant: values.montant,
						date_paiement: values.date_paiement,
						type_paiement: values.type_paiement,
						status: 'Nouveau'
					}
				},
				// Dans create_paiement_locataire, remplacer le callback par :
				callback: function(r) {
					if (r.message) {
						dialog.hide();
						frappe.show_alert({
							message: __('Paiement Locataire créé avec succès'),
							indicator: 'green'
						});
						
						// Rafraîchir le formulaire après la création avec vérifications
						if (frm && frm.reload_doc) {
							frm.reload_doc().then(() => {
								if (frm.trigger) {
									frm.trigger('update_dashboard');
								}
							}).catch((error) => {
								console.error('Erreur lors du rechargement:', error);
								// Fallback: simple refresh
								if (frm && frm.refresh) {
									frm.refresh();
								}
							});
						}
					}
				}
			});
		}
	});
	dialog.show();
}

// Fonction pour créer un paiement propriétaire
function create_paiement_proprietaire(frm) {
	frm.refresh(); // Ensure latest data
	const montantRestant = frm.doc.montant_restant_proprietaire || 0;
	
	if (montantRestant <= 0) {
		frappe.msgprint({
			title: __('Information'),
			message: __('Le montant total propriétaire est entièrement versé. Aucun nouveau versement nécessaire.'),
			indicator: 'blue'
		});
		return;
	}

	// Récupérer le propriétaire depuis l'appartement
	let proprietaire_id = null;
	if (frm.doc.appartement_id) {
		frappe.call({
			method: 'frappe.client.get_value',
			args: {
				doctype: 'Appartement',
				filters: {'name': frm.doc.appartement_id},
				fieldname: 'proprietaire_id'
			},
			callback: function(r) {
				if (r.message) {
					proprietaire_id = r.message.proprietaire_id;
					show_paiement_dialog(frm, montantRestant, proprietaire_id);
				} else {
					show_paiement_dialog(frm, montantRestant, null);
				}
			}
		});
	} else {
		show_paiement_dialog(frm, montantRestant, null);
	}
}

function show_paiement_dialog(frm, montantRestant, proprietaire_id) {
	const defaultData = {
		doctype: 'Paiement Proprietaire',
		location_courte_duree_id: frm.doc.name,
		proprietaire: proprietaire_id,
		montant: montantRestant,
		date_paiement: frappe.datetime.get_today(),
		type_paiement: 'Court Séjour',
		status: 'Nouveau'
	};

	const dialog = new frappe.ui.Dialog({
		title: __('Créer un Paiement Propriétaire'),
		fields: [
			{
				fieldname: 'proprietaire',
				label: __('Propriétaire'),
				fieldtype: 'Link',
				options: 'Proprietaire',
				default: defaultData.proprietaire,
				reqd: 1
			},
			{
				fieldname: 'montant',
				label: __('Montant'),
				fieldtype: 'Currency',
				default: defaultData.montant,
				reqd: 1
			},
			{
				fieldname: 'date_paiement',
				label: __('Date de paiement'),
				fieldtype: 'Date',
				default: defaultData.date_paiement,
				reqd: 1
			},
			{
				fieldname: 'type_paiement',
				label: __('Type de paiement'),
				fieldtype: 'Select',
				options: 'Court Séjour\nLoyer mensuel\nDépôt de garantie\nCharges\nAutre',
				default: defaultData.type_paiement,
				reqd: 1
			},
			{
				fieldtype: 'HTML',
				fieldname: 'info_montant',
				label: __('Information'),
				options: `<div style="padding: 8px; background-color: #f8f9fa; border-radius: 4px; border-left: 4px solid #007cba;">
					<strong>Montant total:</strong> ${frm.doc.montant_total_proprietaire || 0} €<br>
					<strong>Montant déjà versé:</strong> ${frm.doc.montant_paye_proprietaire || 0} €<br>
					<strong>Montant restant:</strong> <span style="color: #007cba; font-weight: bold;">${montantRestant} €</span>
				</div>`
			}
		],
		primary_action_label: __('Créer'),
		primary_action: function(values) {
			const currentMontantRestant = frm.doc.montant_restant_proprietaire || frm.doc.montant_total_proprietaire || 0;
			if (values.montant > currentMontantRestant) {
				frappe.msgprint({
					title: __('Attention'),
					message: __('Le montant saisi (${values.montant} €) dépasse le montant restant à verser (${currentMontantRestant} €).'),
					indicator: 'orange'
				});
				return;
			}

			frappe.call({
				method: 'frappe.client.insert',
				args: {
					doc: {
						doctype: 'Paiement Proprietaire',
						location_courte_duree_id: frm.doc.name,
						proprietaire: values.proprietaire,
						montant: values.montant,
						date_paiement: values.date_paiement,
						type_paiement: values.type_paiement,
						status: 'Nouveau'
					}
				},
				callback: function(r) {
					if (r.message) {
						dialog.hide();
						frappe.show_alert({
							message: __('Paiement Propriétaire créé avec succès'),
							indicator: 'green'
						});
						
						// Rafraîchir le formulaire après la création
						if (frm && frm.reload_doc) {
							frm.reload_doc().then(() => {
								if (frm && frm.doc && frm.trigger) {
									frm.trigger('update_dashboard');
								}
							}).catch((error) => {
								console.error('Erreur lors du rechargement:', error);
								// Fallback: simple refresh avec vérifications
								setTimeout(() => {
									if (frm && frm.doc && frm.refresh) {
										frm.refresh();
									}
								}, 500);
							});
						}
					}
				}
			});
		}
	});
	dialog.show();
}