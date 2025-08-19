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
		
		// Stocker la référence du formulaire globalement pour les boutons des cartes
		if (!frm.doc.__islocal) {
			window.current_location_courte_duree_frm = frm;
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
		
		// Récupérer les listes de paiements en parallèle
		Promise.all([
			// Récupérer les paiements locataire
			frappe.call({
				method: 'frappe.client.get_list',
				args: {
					doctype: 'Paiement Locataire',
					filters: {
						location_courte_duree_id: frm.doc.name
					},
					fields: ['name', 'montant', 'status'],
					order_by: 'creation desc'
				}
			}),
			// Récupérer les paiements propriétaire
			frappe.call({
				method: 'frappe.client.get_list',
				args: {
					doctype: 'Paiement Proprietaire',
					filters: {
						location_courte_duree_id: frm.doc.name
					},
					fields: ['name', 'montant', 'status'],
					order_by: 'creation desc'
				}
			})
		]).then(([paiements_locataire_response, paiements_proprietaire_response]) => {
			const paiements_locataire = paiements_locataire_response.message || [];
			const paiements_proprietaire = paiements_proprietaire_response.message || [];
			
			// Générer le dashboard avec les listes de paiements
			const dashboard_html = createLocationCourteDureeDashboard(frm.doc, paiements_locataire, paiements_proprietaire);
			if (frm.fields_dict && frm.fields_dict['dashboard']) {
				$(frm.fields_dict['dashboard'].wrapper).html(dashboard_html);
			}
		}).catch(error => {
			console.error('Erreur lors du chargement des paiements:', error);
			// En cas d'erreur, afficher le dashboard sans les listes de paiements
			const dashboard_html = createLocationCourteDureeDashboard(frm.doc);
			if (frm.fields_dict && frm.fields_dict['dashboard']) {
				$(frm.fields_dict['dashboard'].wrapper).html(dashboard_html);
			}
		});
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
function createLocationCourteDureeDashboard(doc, paiements_locataire = [], paiements_proprietaire = []) {
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
		
		// Générer le HTML avec le style d'appartement responsive
		const html = `
		<style>
			.dashboard-container {
				display: grid;
				grid-template-rows: auto auto;
				gap: 16px;
				font-family: 'Inter', sans-serif;
				padding: 16px;
				max-width: 100%;
				overflow-x: hidden;
			}
			
			.stats-grid {
				display: grid;
				grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
				gap: 12px;
				align-items: stretch;
			}
			
			.details-grid {
				display: grid;
				grid-template-columns: 1fr 1fr;
				gap: 20px;
			}
			
			@media (max-width: 768px) {
				.dashboard-container {
					padding: 12px;
					gap: 12px;
				}
				
				.stats-grid {
					grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
					gap: 8px;
				}
				
				.stat-card {
					min-height: 100px !important;
					padding: 8px 10px !important;
				}
				
				.stat-title {
					font-size: 0.75rem !important;
				}
				
				.stat-value {
					font-size: 1.1rem !important;
				}
				
				.details-grid {
					grid-template-columns: 1fr;
					gap: 16px;
				}
				
				.detail-card {
					padding: 12px !important;
				}
				
				.detail-header {
					flex-direction: column !important;
					align-items: flex-start !important;
					gap: 8px !important;
				}
				
				.detail-title {
					font-size: 0.85rem !important;
				}
				
				.detail-status {
					font-size: 0.6rem !important;
				}
			}
			
			@media (max-width: 480px) {
				.dashboard-container {
					padding: 8px;
				}
				
				.stats-grid {
					grid-template-columns: 1fr 1fr;
					gap: 6px;
				}
				
				.stat-card {
					min-height: 90px !important;
					padding: 6px 8px !important;
				}
				
				.stat-title {
					font-size: 0.7rem !important;
					line-height: 1.1 !important;
				}
				
				.stat-value {
					font-size: 1rem !important;
				}
				
				.stat-footer {
					font-size: 0.7rem !important;
				}
				
				.stat-badge {
					font-size: 0.65rem !important;
					padding: 1px 4px !important;
				}
				
				.details-grid {
					gap: 12px;
				}
				
				.detail-card {
					padding: 10px !important;
				}
				
				.detail-header {
					flex-direction: column !important;
					align-items: flex-start !important;
					gap: 6px !important;
				}
				
				.detail-title {
					font-size: 0.8rem !important;
				}
				
				.detail-status {
					font-size: 0.55rem !important;
					padding: 1px 4px !important;
				}
				
				.detail-amount {
					font-size: 0.75rem !important;
				}
				
				.payment-list {
					padding-top: 6px !important;
					margin-top: 6px !important;
				}
				
				.payment-item {
					padding: 6px !important;
					font-size: 0.7rem !important;
				}
			}
		</style>
		<div class="dashboard-container">
			<!-- Ligne des 4 cartes statistiques -->
			<div class="stats-grid">
				${createStatCard("Montant Total Locataire", format_currency(montant_total_loc, 'EUR'), "Montant à payer", null)}
				${createStatCard("Montant Payé Locataire", format_currency(montant_paye_loc, 'EUR'), "Montant déjà payé", pourcentage_loc)}
				${createStatCard("Montant Total Propriétaire", format_currency(montant_total_prop, 'EUR'), "Montant à verser", null)}
				${createStatCard("Montant Versé Propriétaire", format_currency(montant_paye_prop, 'EUR'), "Montant déjà versé", pourcentage_prop)}
			</div>
			
			<!-- Ligne des informations détaillées -->
			<div class="details-grid">
				<!-- Section Locataire -->
				<div class="detail-card" style="
					background: #fff;
					border: 1px solid #e5e7eb;
					border-radius: 10px;
					padding: 16px;
					box-shadow: 0 2px 4px rgba(0,0,0,0.05);
					position: relative;
				">
					<div class="detail-header" style="
						font-size: 0.9rem; 
						color: #374151; 
						margin-bottom: 12px; 
						font-weight: 600;
						display: flex;
						align-items: center;
						justify-content: space-between;
					">
						<div style="display: flex; align-items: center; gap: 8px;">
							<div class="detail-title" style="display: flex; align-items: center;">
								<span style="
									width: 8px; 
									height: 8px; 
									background: #3b82f6; 
									border-radius: 50%; 
									margin-right: 8px;
								"></span>
								Locataire
							</div>
							<span class="detail-status" style="
								background: ${getStatusColor(statut_loc).background}; 
								color: ${getStatusColor(statut_loc).text}; 
								padding: 2px 6px; 
								border-radius: 8px; 
								font-size: 0.65rem; 
								font-weight: 600;
							">
								${statut_loc}
							</span>
						</div>
						${montant_restant_loc > 0 ? `
						<button 
							onclick="window.create_paiement_locataire_from_card()" 
							style="
								background: #374151;
								color: white;
								border: none;
								padding: 4px 8px;
								border-radius: 6px;
								font-size: 0.75rem;
								font-weight: 500;
								cursor: pointer;
								transition: all 0.2s;
								box-shadow: 0 1px 2px rgba(0,0,0,0.1);
							"
							onmouseover="this.style.background='#1f2937'"
							onmouseout="this.style.background='#374151'"
							title="Créer un nouveau paiement locataire"
						>
							+ Paiement
						</button>
						` : ''}
					</div>
					
					<div style="font-size: 0.8rem; color: #6b7280; line-height: 1.6;">
						<div style="margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">
							<span style="font-weight: 500;">Montant restant:</span> 
							<span class="detail-amount" style="
								color: ${montant_restant_loc > 0 ? '#dc2626' : '#16a34a'}; 
								font-weight: 700;
								font-size: 0.85rem;
							">
								${montant_restant_loc.toFixed(2)} €
							</span>
						</div>
						
						<!-- Liste des paiements locataire -->
						<div class="payment-list" style="
							border-top: 1px solid #e5e7eb; 
							padding-top: 8px; 
							margin-top: 8px;
						">
							<div style="
								font-weight: 600; 
								margin-bottom: 6px; 
								color: #374151; 
								font-size: 0.75rem;
							">
								Paiements:
							</div>
							${generatePaiementsList(paiements_locataire, 'locataire')}
						</div>

					</div>
				</div>
				
				<!-- Section Propriétaire -->
				<div class="detail-card" style="
					background: #fff;
					border: 1px solid #e5e7eb;
					border-radius: 10px;
					padding: 16px;
					box-shadow: 0 2px 4px rgba(0,0,0,0.05);
					position: relative;
				">
					<div class="detail-header" style="
						font-size: 0.9rem; 
						color: #374151; 
						margin-bottom: 12px; 
						font-weight: 600;
						display: flex;
						align-items: center;
						justify-content: space-between;
					">
						<div style="display: flex; align-items: center; gap: 8px;">
							<div class="detail-title" style="display: flex; align-items: center;">
								<span style="
									width: 8px; 
									height: 8px; 
									background: #16a34a; 
									border-radius: 50%; 
									margin-right: 8px;
								"></span>
								Propriétaire
							</div>
							<span class="detail-status" style="
								background: ${doc.location_bloc_id ? getStatusColor('Payé').background : getStatusColor(statut_prop).background}; 
								color: ${doc.location_bloc_id ? getStatusColor('Payé').text : getStatusColor(statut_prop).text}; 
								padding: 2px 6px; 
								border-radius: 8px; 
								font-size: 0.65rem; 
								font-weight: 600;
							">
								${doc.location_bloc_id ? 'Payé' : statut_prop}
							</span>
						</div>
						${doc.location_bloc_id ? `
						<div style="
							background: #dcfce7;
							color: #16a34a;
							border: 1px solid #22c55e;
							padding: 6px 10px;
							border-radius: 6px;
							font-size: 0.7rem;
							font-weight: 500;
							text-align: center;
							line-height: 1.3;
						">
							Payé via bloc
						</div>
						` : (montant_restant_prop > 0 ? `
						<button 
							onclick="window.create_paiement_proprietaire_from_card()" 
							style="
								background: #374151;
								color: white;
								border: none;
								padding: 4px 8px;
								border-radius: 6px;
								font-size: 0.75rem;
								font-weight: 500;
								cursor: pointer;
								transition: all 0.2s;
								box-shadow: 0 1px 2px rgba(0,0,0,0.1);
							"
							onmouseover="this.style.background='#1f2937'"
							onmouseout="this.style.background='#374151'"
							title="Créer un nouveau paiement propriétaire"
						>
							+ Paiement
						</button>
						` : '')}
					</div>
					
					<div style="font-size: 0.8rem; color: #6b7280; line-height: 1.6;">
					<div style="margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center;">
						<span style="font-weight: 500;">Montant restant:</span> 
						<span class="detail-amount" style="
							color: ${doc.location_bloc_id ? '#16a34a' : (montant_restant_prop > 0 ? '#dc2626' : '#16a34a')}; 
							font-weight: 700;
							font-size: 0.85rem;
						">
							${doc.location_bloc_id ? '0.00' : montant_restant_prop.toFixed(2)} €
						</span>
					</div>
						
						<!-- Liste des paiements propriétaire -->
						<div class="payment-list" style="
							border-top: 1px solid #e5e7eb; 
							padding-top: 8px; 
							margin-top: 8px;
						">
							<div style="
								font-weight: 600; 
								margin-bottom: 6px; 
								color: #374151; 
								font-size: 0.75rem;
							">
								Paiements:
							</div>
							${generatePaiementsList(paiements_proprietaire, 'proprietaire')}
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

// Fonction pour créer une carte de statistique responsive
function createStatCard(title, mainValue, footerValue, percentage) {
	let showBadge = percentage !== null;
	let isPositive = percentage >= 0;
	let badgeColor = isPositive ? '#16a34a' : '#dc2626';

	return `
		<div class="stat-card" style="
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
			<div class="stat-title" style="font-size: 0.8rem; color: #6b7280; line-height: 1.2;">${title}</div>
			
			<div class="stat-content" style="display: flex; align-items: center; justify-content: space-between; margin: 6px 0; flex-wrap: wrap; gap: 4px;">
				<div class="stat-value" style="font-size: 1.2rem; font-weight: 700; color: #111827; word-break: break-word; flex: 1; min-width: 0;">${mainValue}</div>
				${showBadge ? `<div class="stat-badge" style="
					font-size: 0.7rem;
					padding: 2px 6px;
					border-radius: 9999px;
					border: 1px solid ${badgeColor};
					color: ${badgeColor};
					background: transparent;
					white-space: nowrap;
					flex-shrink: 0;
				">
					${percentage.toFixed(0)}%
				</div>` : ''}
			</div>

			<div class="stat-footer" style="
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
	
	// Vérifier si cette location provient d'un bloc
	if (frm.doc.location_bloc_id) {
		frappe.msgprint({
			title: __('Paiement via Bloc'),
			message: __('Cette location provient d\'un bloc. Le propriétaire a déjà été payé via un Paiement Bloc. Aucun paiement direct n\'est nécessaire.'),
			indicator: 'orange'
		});
		return;
	}
	
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

// Fonctions globales pour les boutons des cartes HTML
window.create_paiement_locataire_from_card = function() {
	if (window.current_location_courte_duree_frm) {
		create_paiement_locataire(window.current_location_courte_duree_frm);
	} else {
		frappe.msgprint(__('Erreur: Formulaire non disponible'));
	}
};

window.create_paiement_proprietaire_from_card = function() {
	if (window.current_location_courte_duree_frm) {
		create_paiement_proprietaire(window.current_location_courte_duree_frm);
	} else {
		frappe.msgprint(__('Erreur: Formulaire non disponible'));
	}
};

// Fonction pour générer la liste des paiements
function generatePaiementsList(paiements, type) {
	if (!paiements || paiements.length === 0) {
		return `<div style="color: #6b7280; font-style: italic; text-align: center; padding: 8px;">Aucun paiement</div>`;
	}
	
	return paiements.map(paiement => {
		const statusColor = getStatusColor(paiement.status);
		return `
			<div class="payment-item" style="
				display: flex; 
				justify-content: space-between; 
				align-items: center; 
				padding: 6px 0; 
				border-bottom: 1px solid #f3f4f6;
				font-size: 0.75rem;
				flex-wrap: wrap;
				gap: 4px;
			">
				<span 
					onclick="navigateToPaiement('${paiement.name}', '${type}')" 
					style="
						color: #2563eb; 
						cursor: pointer; 
						text-decoration: underline;
						font-weight: 500;
						flex: 1;
						min-width: 0;
						word-break: break-word;
					"
				>
					${paiement.name}
				</span>
				<div style="display: flex; align-items: center; gap: 6px; flex-shrink: 0;">
					<span style="font-weight: 600; white-space: nowrap;">${paiement.montant.toFixed(2)} €</span>
					<span style="
						background: ${statusColor.background}; 
						color: ${statusColor.text}; 
						padding: 1px 6px; 
						border-radius: 8px; 
						font-size: 0.65rem; 
						font-weight: 600;
						white-space: nowrap;
					">
						${paiement.status}
					</span>
				</div>
			</div>
		`;
	}).join('');
}

// Fonction pour naviguer vers un paiement
window.navigateToPaiement = function(paiement_name, type) {
	const doctype = type === 'locataire' ? 'Paiement Locataire' : 'Paiement Proprietaire';
	frappe.set_route('Form', doctype, paiement_name);
};