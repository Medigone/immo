// Location Bloc JavaScript - v11
frappe.ui.form.on('Location Bloc', {
	onload: function (frm) {
		frm.trigger('update_dashboard');

		// Écouter les mises à jour en temps réel des paiements et locations
		frappe.realtime.on('location_bloc_updated', function (data) {
			if (
				data.location_bloc_id === frm.doc.name &&
				(data.action === 'payment_updated' ||
					data.action === 'payment_deleted' ||
					data.action === 'location_updated' ||
					data.action === 'location_deleted')
			) {
				console.log('Mise à jour détectée, rechargement du dashboard et calendrier');
				// Recharger le document pour obtenir les nouvelles valeurs
				frm.reload_doc().then(() => {
					frm.trigger('update_dashboard');
				});
			}
		});
	},

	validate: function (frm) {
		frm.trigger('update_dashboard');
	},

	after_save: function (frm) {
		frm.trigger('update_dashboard');
	},

	refresh: function (frm) {
		if (frm.doc.name) {
			// Bouton pour créer une Location Courte Durée
			frm.add_custom_button(__('Location Courte Durée'), function () {
				let dialog = new frappe.ui.Dialog({
					title: __('Créer une Location Courte Durée'),
					fields: [
						{ fieldname: 'locataire_nom', label: __('Nom du locataire'), fieldtype: 'Data', reqd: 1 },
						{ fieldname: 'locataire_email', label: __('Email du locataire'), fieldtype: 'Data', options: 'Email' },
						{ fieldname: 'date_debut', label: __('Date de début'), fieldtype: 'Date', default: frappe.datetime.get_today(), reqd: 1 },
						{ fieldname: 'date_fin', label: __('Date de fin'), fieldtype: 'Date', default: frappe.datetime.add_days(frappe.datetime.get_today(), 1), reqd: 1 },
						{ fieldname: 'prix_journalier_locataire', label: __('Prix journalier locataire'), fieldtype: 'Currency', reqd: 1 }
					],
					primary_action_label: __('Créer'),
					primary_action: function (values) {
						frappe.call({
							method: 'frappe.client.insert',
							args: {
								doc: {
									doctype: 'Location Courte Duree',
									location_bloc_id: frm.doc.name,
									appartement_id: frm.doc.appartement_id,
									locataire_nom: values.locataire_nom,
									locataire_email: values.locataire_email,
									date_debut: values.date_debut,
									date_fin: values.date_fin,
									prix_journalier_locataire: values.prix_journalier_locataire,
									type_location: 'Sous-location'
								}
							},
							callback: function (r) {
								if (!r.exc) {
									dialog.hide();
									frm.reload_doc();
									frappe.show_alert({ message: __('Location Courte Durée créée avec succès'), indicator: 'green' });
								}
							}
						});
					}
				});
				dialog.show();
			}, __('Créer'));

			// Bouton pour créer un Paiement Bloc
			frm.add_custom_button(__('Paiement Bloc'), function () {
				let dialog = new frappe.ui.Dialog({
					title: __('Créer un Paiement Bloc'),
					fields: [
						{ fieldname: 'montant_paiement', label: __('Montant du Paiement'), fieldtype: 'Currency', default: frm.doc.solde_restant && frm.doc.solde_restant < frm.doc.montant_total_proprietaire ? frm.doc.solde_restant : frm.doc.montant_total_proprietaire, reqd: 1 },
						{ fieldname: 'date_paiement', label: __('Date de Paiement'), fieldtype: 'Date', default: frappe.datetime.get_today(), reqd: 1 },

						{ fieldname: 'methode_paiement', label: __('Méthode de Paiement'), fieldtype: 'Select', options: 'Virement\nChèque\nEspèces\nCarte' },
						{ fieldname: 'reference_paiement', label: __('Référence de Paiement'), fieldtype: 'Data' },
						{ fieldname: 'notes', label: __('Notes'), fieldtype: 'Text Editor' }
					],
					primary_action_label: __('Créer Paiement'),
					primary_action: function (values) {
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
									type_paiement: 'Unique',
									methode_paiement: values.methode_paiement,
									reference_paiement: values.reference_paiement,
									notes: values.notes
								}
							},
							callback: function (r) {
								if (!r.exc) {
									dialog.hide();
									frappe.show_alert({ message: __('Paiement Bloc créé avec succès'), indicator: 'green' });
									frm.reload_doc().then(() => {
										frm.trigger('update_dashboard');
									});
								}
							}
						});
					}
				});
				dialog.show();
			}, __('Créer'));
		}

		frm.trigger('update_dashboard');
	},

	update_dashboard: function(frm) {
		let rentabilite = frm.doc.rentabilite_pourcentage || 0;
		let payment_percentage = frm.doc.montant_total_proprietaire > 0 ? (frm.doc.montant_total_paye / frm.doc.montant_total_proprietaire) * 100 : 0;
		let occupation_percentage = frm.doc.taux_occupation || 0;
		let tenant_payment_total = frm.doc.total_encaisse || 0;
		
		// Calculer les nuits occupées basées sur le taux d'occupation
		let total_nights = frm.doc.nombre_nuits_total || 0;
		let occupied_nights = Math.round((occupation_percentage / 100) * total_nights);

		// Préparer le calendrier d'occupation
		let calendar_card = '<div id="occupation-calendar-placeholder" style="background: #fff; border: 1px solid #e5e7eb; border-radius: 10px; padding: 10px 12px; display: flex; align-items: center; justify-content: center; font-size: 0.8rem; color: #6b7280;">Chargement du calendrier...</div>';

		let dashboard_html = `
			<div style="
				display: grid;
				grid-template-rows: auto auto;
				gap: 16px;
				font-family: 'Inter', sans-serif;
			">
				<!-- Ligne des 4 cartes statistiques -->
				<div style="
					display: grid;
					grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
					gap: 12px;
					align-items: stretch;
				">
					${createStatCard("Rentabilité", rentabilite.toFixed(1) + "%", "Marge : " + format_currency(frm.doc.marge_totale || 0, 'EUR'), rentabilite)}
					${createStatCard("Paiements Propriétaire", payment_percentage.toFixed(1) + "%", format_currency(frm.doc.montant_total_paye || 0, 'EUR') + "/" + format_currency(frm.doc.montant_total_proprietaire || 0, 'EUR'), payment_percentage)}
					${createStatCard("Taux d'occupation", occupation_percentage.toFixed(1) + "%", occupied_nights + "/" + total_nights + " nuits", occupation_percentage)}
					${createStatCard("Paiements Locataires", format_currency(tenant_payment_total, 'EUR'), "Total encaissé", null)}
				</div>
				<!-- Ligne du calendrier en pleine largeur -->
				<div style="
					width: 100%;
				">
					${calendar_card}
				</div>
			</div>
		`;

		if (frm.fields_dict['rentabilite_progress_html']) {
			$(frm.fields_dict['rentabilite_progress_html'].wrapper).find("#rentabilite-progress-container").html(dashboard_html);
			
			// Charger le calendrier d'occupation
			frm.trigger('load_occupation_calendar');
		}
	},

	load_occupation_calendar: function(frm) {
		if (!frm.doc.name) return;
		
		frappe.call({
			method: 'immo.api.location_bloc.get_bloc_dashboard_data',
			args: {
				location_bloc_id: frm.doc.name
			},
			callback: function(r) {
				if (r.message && r.message.calendrier) {
					const calendar_html = createOccupationCalendar(r.message.calendrier, frm.doc.date_debut_bloc, frm.doc.date_fin_bloc);
					$(frm.fields_dict['rentabilite_progress_html'].wrapper).find("#occupation-calendar-placeholder").replaceWith(calendar_html);
				} else {
					// Si pas de données, afficher un calendrier vide
					const empty_calendar = createOccupationCalendar([], frm.doc.date_debut_bloc, frm.doc.date_fin_bloc);
					$(frm.fields_dict['rentabilite_progress_html'].wrapper).find("#occupation-calendar-placeholder").replaceWith(empty_calendar);
				}
			}
		});
	}
});

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

function format_currency(value, currency) {
	return frappe.format(value, { fieldtype: 'Currency', currency: currency });
}

function createOccupationCalendar(calendrier, date_debut, date_fin) {
	if (!calendrier || calendrier.length === 0) {
		return `
			<div style="
				background: #fff;
				border: 1px solid #e5e7eb;
				border-radius: 10px;
				padding: 10px 12px;
				display: flex;
				flex-direction: column;
				justify-content: center;
				align-items: center;
				height: 120px;
				min-width: 0;
				font-family: 'Inter', sans-serif;
			">
				<div style="font-size: 0.8rem; color: #6b7280; margin-bottom: 8px;">Calendrier d'Occupation</div>
				<div style="font-size: 0.75rem; color: #9ca3af;">Aucune donnée disponible</div>
			</div>
		`;
	}

	// Grouper les jours par mois
	const moisGroupes = {};
	calendrier.forEach(jour => {
		const date = new Date(jour.date);
		const moisKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
		if (!moisGroupes[moisKey]) {
			moisGroupes[moisKey] = {
				mois: date.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' }),
				jours: []
			};
		}
		moisGroupes[moisKey].jours.push(jour);
	});

	// Calculer les statistiques d'occupation
	const totalJours = calendrier.length;
	const joursOccupes = calendrier.filter(j => j.occupe).length;
	const tauxOccupation = totalJours > 0 ? (joursOccupes / totalJours) * 100 : 0;

	let calendar_html = `
		<div style="
			background: #fff;
			border: 1px solid #e5e7eb;
			border-radius: 10px;
			padding: 10px 12px;
			display: flex;
			flex-direction: column;
			justify-content: space-between;
			height: 100%;
			min-width: 0;
			font-family: 'Inter', sans-serif;
		">
			<!-- En-tête avec style des cartes -->
			<div style="font-size: 0.8rem; color: #6b7280;">Calendrier d'Occupation</div>
			
			<!-- Statistiques avec style des cartes -->
			<div style="display: flex; align-items: center; justify-content: space-between; margin: 6px 0;">
				<div style="font-size: 1.2rem; font-weight: 700; color: #111827;">${tauxOccupation.toFixed(1)}%</div>
				<div style="
					font-size: 0.7rem;
					padding: 2px 6px;
					border-radius: 9999px;
					border: 1px solid #16a34a;
					color: #16a34a;
					background: transparent;
					white-space: nowrap;
				">
					↑ ${joursOccupes}/${totalJours}
				</div>
			</div>

			<!-- Légende avec style des cartes -->
			<div style="
				font-size: 0.75rem;
				color: #374151;
				margin-top: auto;
				display: flex;
				align-items: center;
				gap: 12px;
				margin-bottom: 12px;
			">
				<span style="display: flex; align-items: center; gap: 4px;">
					<div style="width: 8px; height: 8px; background: #16a34a; border-radius: 2px;"></div>
					Occupé
				</span>
				<span style="display: flex; align-items: center; gap: 4px;">
					<div style="width: 8px; height: 8px; background: #f3f4f6; border: 1px solid #d1d5db; border-radius: 2px;"></div>
					Libre
				</span>
			</div>
	`;

	// Générer le calendrier pour chaque mois
	Object.keys(moisGroupes).sort().forEach((moisKey, index) => {
		const moisData = moisGroupes[moisKey];
		
		calendar_html += `
			<div style="margin-bottom: ${index === Object.keys(moisGroupes).length - 1 ? '0' : '16px'};">
				<div style="
					margin: 0 0 8px 0;
					color: #374151;
					font-size: 0.8rem;
					font-weight: 600;
					text-transform: capitalize;
				">${moisData.mois}</div>
				<div style="
					display: grid;
					grid-template-columns: repeat(7, 1fr);
					gap: 1px;
					max-width: 280px;
				">
		`;

		// En-têtes des jours de la semaine
		const joursNoms = ['D', 'L', 'M', 'M', 'J', 'V', 'S'];
		joursNoms.forEach(jour => {
			calendar_html += `
				<div style="
					padding: 2px;
					text-align: center;
					font-size: 0.65rem;
					font-weight: 600;
					color: #6b7280;
				">${jour}</div>
			`;
		});

		// Calculer le premier jour du mois et ajouter des cellules vides si nécessaire
		const premierJour = new Date(moisData.jours[0].date);
		premierJour.setDate(1);
		const premierJourSemaine = premierJour.getDay();
		
		// Ajouter des cellules vides pour les jours avant le début du mois
		for (let i = 0; i < premierJourSemaine; i++) {
			calendar_html += '<div></div>';
		}

		// Ajouter les jours du mois
		moisData.jours.forEach(jour => {
			const date = new Date(jour.date);
			const jourNum = date.getDate();
			const isOccupe = jour.occupe;
			const bgColor = isOccupe ? '#16a34a' : '#f9fafb';
			const textColor = isOccupe ? '#fff' : '#374151';
			const borderColor = isOccupe ? '#16a34a' : '#e5e7eb';
			
			const tooltip = isOccupe ? `Occupé par ${jour.locataire}` : 'Libre';
			const clickHandler = jour.occupe && jour.location_id ? `onclick="showLocationDetailsModal('${jour.location_id}')"` : '';
			
			calendar_html += `
				<div style="
					width: 24px;
					height: 24px;
					display: flex;
					align-items: center;
					justify-content: center;
					background: ${bgColor};
					color: ${textColor};
					border: 1px solid ${borderColor};
					border-radius: 4px;
					font-size: 0.65rem;
					font-weight: ${isOccupe ? '600' : '400'};
					cursor: pointer;
					transition: all 0.2s ease;
					box-shadow: ${isOccupe ? '0 1px 2px rgba(0, 0, 0, 0.05)' : 'none'};
				" title="${tooltip}" ${clickHandler} onmouseover="this.style.transform='scale(1.1)'; this.style.zIndex='10';" onmouseout="this.style.transform='scale(1)'; this.style.zIndex='1';">
					${jourNum}
				</div>
			`;
		});

		calendar_html += '</div></div>';
	});

	calendar_html += '</div>';
	return calendar_html;
}

// Fonction globale pour afficher les détails d'une Location Courte Duree dans un modal - v3
window.showLocationDetailsModal = function(location_id) {
	frappe.call({
		method: 'frappe.client.get',
		args: {
			doctype: 'Location Courte Duree',
			name: location_id
		},
		callback: function(r) {
			if (r.message) {
				const location = r.message;
				
				// Créer le modal avec les informations de la location
				const dialog = new frappe.ui.Dialog({
					title: `Détails de la Location - ${location.name}`,
					size: 'large',
					fields: [
						{
							fieldtype: 'HTML',
							fieldname: 'location_details',
							options: `
								<div style="padding: 12px; display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; align-items: stretch;" class="location-modal-grid">
									<div style="
												background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
												border: 1px solid #cbd5e1;
												border-radius: 12px;
												padding: 14px 16px;
												display: flex;
												flex-direction: column;
												justify-content: flex-start;
												height: 100%;
												min-height: 120px;
												min-width: 0;
												box-shadow: 0 2px 4px rgba(0,0,0,0.05);
											">
												<div style="font-size: 0.85rem; color: #475569; margin-bottom: 10px; font-weight: 600; display: flex; align-items: center;">
													<span style="width: 8px; height: 8px; background: #3b82f6; border-radius: 50%; margin-right: 8px;"></span>
													Informations Locataire
												</div>
												<div style="font-size: 0.8rem; color: #334155; line-height: 1.5;">
													<div style="margin-bottom: 6px; display: flex; justify-content: space-between;"><span style="font-weight: 500;">Nom:</span> <span>${location.locataire_nom || 'N/A'}</span></div>
													<div style="margin-bottom: 6px; display: flex; justify-content: space-between;"><span style="font-weight: 500;">Email:</span> <span style="color: #64748b;">${location.locataire_email || 'N/A'}</span></div>
													<div style="display: flex; justify-content: space-between;"><span style="font-weight: 500;">Téléphone:</span> <span style="color: #64748b;">${location.locataire_telephone || 'N/A'}</span></div>
												</div>
											</div>
									<div style="
												background: linear-gradient(135deg, #fefce8 0%, #fef3c7 100%);
												border: 1px solid #fbbf24;
												border-radius: 12px;
												padding: 14px 16px;
												display: flex;
													flex-direction: column;
													justify-content: flex-start;
													height: 100%;
													min-height: 120px;
													min-width: 0;
												box-shadow: 0 2px 4px rgba(251,191,36,0.1);
											">
												<div style="font-size: 0.85rem; color: #92400e; margin-bottom: 10px; font-weight: 600; display: flex; align-items: center;">
													<span style="width: 8px; height: 8px; background: #f59e0b; border-radius: 50%; margin-right: 8px;"></span>
													Détails du Séjour
												</div>
												<div style="font-size: 0.8rem; color: #78350f; line-height: 1.5;">
													<div style="margin-bottom: 6px; display: flex; justify-content: space-between;"><span style="font-weight: 500;">Date d'arrivée:</span> <span style="color: #a16207;">${frappe.datetime.str_to_user(location.date_debut)}</span></div>
													<div style="margin-bottom: 6px; display: flex; justify-content: space-between;"><span style="font-weight: 500;">Date de départ:</span> <span style="color: #a16207;">${frappe.datetime.str_to_user(location.date_fin)}</span></div>
													<div style="display: flex; justify-content: space-between;"><span style="font-weight: 500;">Nombre de nuits:</span> <span style="background: #f59e0b; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600;">${location.nombre_nuits || 'N/A'}</span></div>
												</div>
											</div>
									<div style="
												background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
												border: 1px solid #22c55e;
												border-radius: 12px;
												padding: 14px 16px;
												display: flex;
													flex-direction: column;
													justify-content: flex-start;
													height: 100%;
													min-height: 120px;
													min-width: 0;
												box-shadow: 0 2px 4px rgba(34,197,94,0.1);
											">
												<div style="font-size: 0.85rem; color: #166534; margin-bottom: 10px; font-weight: 600; display: flex; align-items: center;">
													<span style="width: 8px; height: 8px; background: #16a34a; border-radius: 50%; margin-right: 8px;"></span>
													Tarification
												</div>
												<div style="font-size: 0.8rem; color: #15803d; line-height: 1.5;">
													<div style="margin-bottom: 6px; display: flex; justify-content: space-between;"><span style="font-weight: 500;">Prix journalier:</span> <span style="color: #16a34a; font-weight: 600;">${format_currency(location.prix_journalier_locataire || 0, 'EUR')}</span></div>
													<div style="margin-bottom: 6px; display: flex; justify-content: space-between;"><span style="font-weight: 500;">Coût journalier:</span> <span style="color: #16a34a; font-weight: 600;">${format_currency(location.prix_journalier_proprietaire || 0, 'EUR')}</span></div>
													<div style="display: flex; justify-content: space-between; padding: 8px; background: rgba(34,197,94,0.1); border-radius: 8px; margin-top: 4px;"><span style="font-weight: 600;">Montant total:</span> <span style="color: #16a34a; font-weight: 700; font-size: 0.9rem;">${format_currency(location.montant_total_locataire || 0, 'EUR')}</span></div>
												</div>
											</div>
								</div>
								
								<div style="padding: 0 12px; display: grid; grid-template-columns: 1fr; gap: 12px;" class="location-modal-additional">
															<div style="
																background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
																border: 1px solid #64748b;
																border-radius: 12px;
																padding: 14px 16px;
																display: flex;
														flex-direction: column;
														justify-content: flex-start;
														height: 100%;
														min-height: 120px;
														min-width: 0;
																box-shadow: 0 2px 4px rgba(100,116,139,0.1);
															">
																<div style="font-size: 0.85rem; color: #334155; margin-bottom: 10px; font-weight: 600; display: flex; align-items: center;">
																	<span style="width: 8px; height: 8px; background: #64748b; border-radius: 50%; margin-right: 8px;"></span>
																	Informations Complémentaires
																</div>
																<div style="font-size: 0.8rem; color: #475569; line-height: 1.5;">
																	<div style="margin-bottom: 6px; display: flex; justify-content: space-between;"><span style="font-weight: 500;">Référent:</span> <span style="color: #64748b;">${location.referent_id || 'Aucun'}</span></div>
																	<div style="margin-bottom: 6px; display: flex; justify-content: space-between;"><span style="font-weight: 500;">Commission référent:</span> <span style="color: #64748b; font-weight: 600;">${format_currency(location.commission_referent || 0, 'EUR')}</span></div>
																	<div style="margin-bottom: 6px; display: flex; justify-content: space-between;"><span style="font-weight: 500;">Date de création:</span> <span style="color: #64748b; font-size: 0.75rem;">${frappe.datetime.str_to_user(location.creation) || 'N/A'}</span></div>
			${location.commentaires ? `<div style="margin-top: 8px; padding: 8px; background: rgba(100,116,139,0.1); border-radius: 8px;"><span style="font-weight: 500;">Commentaires:</span> <span style="color: #64748b;">${location.commentaires}</span></div>` : ''}
																			</div>
																		</div>
																	</div>
										</div>
									<style>
								@media (max-width: 768px) {
									.location-modal-grid {
										grid-template-columns: 1fr !important;
										gap: 8px !important;
										padding: 8px !important;
									}
									.location-modal-additional {
										padding: 0 8px !important;
										gap: 8px !important;
									}
									.location-modal-grid > div,
									.location-modal-additional > div {
										min-height: 100px !important;
										padding: 12px 14px !important;
									}
									.location-modal-grid > div > div:first-child,
									.location-modal-additional > div > div:first-child {
										font-size: 0.8rem !important;
										margin-bottom: 8px !important;
									}
									.location-modal-grid > div > div:last-child,
									.location-modal-additional > div > div:last-child {
										font-size: 0.75rem !important;
									}
									.location-modal-grid > div > div:last-child > div,
									.location-modal-additional > div > div:last-child > div {
										margin-bottom: 4px !important;
										flex-direction: column !important;
										align-items: flex-start !important;
										gap: 2px !important;
									}
									.location-modal-grid > div > div:last-child > div:last-child {
										padding: 6px !important;
										margin-top: 6px !important;
									}
								}
								@media (max-width: 480px) {
									.modal-dialog {
										margin: 10px !important;
										max-width: calc(100vw - 20px) !important;
									}
									.location-modal-grid,
									.location-modal-additional {
										padding: 6px !important;
										gap: 6px !important;
									}
									.location-modal-grid > div,
									.location-modal-additional > div {
										padding: 10px 12px !important;
										min-height: 90px !important;
									}
								}
							</style>
							`
							}
					],
					primary_action_label: 'Modifier',
					primary_action: function() {
						// Ouvrir le formulaire de modification
						frappe.set_route('Form', 'Location Courte Duree', location.name);
						dialog.hide();
					},
					secondary_action_label: 'Fermer',
					secondary_action: function() {
						dialog.hide();
					}
				});
				
				dialog.show();
			}
		}
	});
}