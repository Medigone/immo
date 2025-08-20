// Copyright (c) 2025, IntraPro and contributors
// For license information, please see license.txt

// Appartement JavaScript - Dashboard avec calendrier d'occupation
frappe.ui.form.on("Appartement", {
	onload: function (frm) {
		frm.trigger('update_dashboard');
	},

	validate: function (frm) {
		frm.trigger('update_dashboard');
	},

	after_save: function (frm) {
		frm.trigger('update_dashboard');
	},

	refresh: function (frm) {
		frm.trigger('update_dashboard');
	},

	update_dashboard: function(frm) {
		// Vérifier si le document existe et n'est pas un nouveau document
		if (!frm.doc.name || frm.doc.__islocal || frm.doc.name.startsWith('new-')) {
			// Afficher un message pour les nouveaux documents
			let placeholder_html = `
				<div style="
					display: flex;
					justify-content: center;
					align-items: center;
					height: 200px;
					font-family: 'Inter', sans-serif;
					color: #6b7280;
				">
					<div>Le dashboard sera disponible après la sauvegarde de l'appartement</div>
				</div>
			`;
			
			if (frm.fields_dict['dashboard']) {
				$(frm.fields_dict['dashboard'].wrapper).html(placeholder_html);
			}
			return;
		}
		
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
		
		if (frm.fields_dict['dashboard']) {
			$(frm.fields_dict['dashboard'].wrapper).html(loading_html);
		}
		
		// Charger les données du dashboard
		frm.trigger('load_dashboard_data');
	},

	load_dashboard_data: function(frm) {
		// Vérifier si le document existe et n'est pas un nouveau document
		if (!frm.doc.name || frm.doc.__islocal || frm.doc.name.startsWith('new-')) return;
		
		frappe.call({
			method: 'immo.api.appartement.get_appartement_dashboard_data',
			args: {
				appartement_id: frm.doc.name
			},
			callback: function(r) {
				if (r.message && !r.message.error) {
					const data = r.message;
					const dashboard_html = createAppartementDashboard(data, frm.doc);
					$(frm.fields_dict['dashboard'].wrapper).html(dashboard_html);
				} else {
					// Afficher un message d'erreur
					const error_html = `
						<div style="
							display: flex;
							justify-content: center;
							align-items: center;
							height: 200px;
							font-family: 'Inter', sans-serif;
							color: #dc2626;
						">
							<div>Erreur lors du chargement du dashboard</div>
						</div>
					`;
					$(frm.fields_dict['dashboard'].wrapper).html(error_html);
				}
			}
		});
	},

	/**
	 * Met à jour l'adresse complète quand un des champs d'adresse change
	 * @param {Object} frm - Le formulaire Frappe
	 */
	update_adresse_complete(frm) {
		const adresse_parts = [];
		
		// Ajoute la rue si elle existe
		if (frm.doc.rue) {
			adresse_parts.push(frm.doc.rue.trim());
		}
		
		// Ajoute le complément d'adresse si il existe
		if (frm.doc.complement_ad) {
			adresse_parts.push(frm.doc.complement_ad.trim());
		}
		
		// Ajoute la ville si elle existe
		if (frm.doc.ville) {
			adresse_parts.push(frm.doc.ville.trim());
		}
		
		// Met à jour le champ adresse_complete
		frm.set_value('adresse_complete', adresse_parts.join(', '));
	},
	
	// Événements sur les champs individuels
	rue(frm) {
		frm.events.update_adresse_complete(frm);
	},
	
	complement_ad(frm) {
		frm.events.update_adresse_complete(frm);
	},
	
	ville(frm) {
		frm.events.update_adresse_complete(frm);
	}
});

// Fonction pour créer le dashboard de l'appartement
function createAppartementDashboard(data, appartement) {
	const stats = data.stats || {};
	const calendrier = data.calendrier || [];
	
	// Extraire les données simplifiées
	const revenus_total = stats.revenus_total || 0;
	const charges_total = stats.charges_total || 0;
	const marge = stats.marge || 0;
	
	// Calculer le pourcentage de marge
	const marge_percentage = revenus_total > 0 ? ((marge / revenus_total) * 100) : 0;
	
	let dashboard_html = `
		<div style="
			display: grid;
			grid-template-rows: auto auto;
			gap: 16px;
			font-family: 'Inter', sans-serif;
			padding: 16px;
		">
			<!-- Section Financière -->
			<div>
				<h3 style="margin: 0 0 12px 0; font-size: 1.1rem; font-weight: 600; color: #111827;">Statistiques Financières</h3>
				<div style="
					display: grid;
					grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
					gap: 12px;
					align-items: stretch;
				">
					${createStatCard("Revenus", format_currency(revenus_total, 'EUR'), "Paiements Locataire", null)}
					${createStatCard("Charges", format_currency(charges_total, 'EUR'), "Paiements Propriétaire", null)}
					${createStatCard("Marge", format_currency(marge, 'EUR'), "Marge : " + marge_percentage.toFixed(1) + "%", marge_percentage)}
				</div>
			</div>
			
			<!-- Ligne du calendrier en pleine largeur -->
			<div style="
				width: 100%;
			">
				${createAppartementOccupationCalendar(calendrier)}
			</div>
		</div>
	`;
	
	return dashboard_html;
}

// Fonction pour créer une carte de statistique (réutilisée de Location Bloc)
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

// Fonction pour formater les devises
function format_currency(value, currency) {
	// Formatage manuel pour éviter le HTML généré par frappe.format
	if (!value) value = 0;
	const formatted = parseFloat(value).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
	return `€ ${formatted}`;
}

// Fonction pour créer le calendrier d'occupation de l'appartement
function createAppartementOccupationCalendar(calendrier) {
	if (!calendrier || calendrier.length === 0) {
		return `
			<div style="
				background: #fff;
				border: 1px solid #e5e7eb;
				border-radius: 10px;
				padding: 16px;
				display: flex;
				flex-direction: column;
				justify-content: center;
				align-items: center;
				height: 200px;
				font-family: 'Inter', sans-serif;
			">
				<div style="font-size: 0.9rem; color: #6b7280; margin-bottom: 8px; font-weight: 600;">Calendrier d'Occupation</div>
				<div style="font-size: 0.8rem; color: #9ca3af;">Aucune donnée disponible</div>
			</div>
		`;
	}

	// Générer un ID unique pour ce calendrier
	const calendarId = 'calendar_' + Math.random().toString(36).substr(2, 9);

	// Grouper les jours par mois
	const moisGroupes = {};
	calendrier.forEach(jour => {
		const date = new Date(jour.date);
		const moisKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
		if (!moisGroupes[moisKey]) {
			moisGroupes[moisKey] = {
				mois: date.toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' }),
				moisCourt: date.toLocaleDateString('fr-FR', { month: 'short', year: 'numeric' }),
				jours: []
			};
		}
		moisGroupes[moisKey].jours.push(jour);
	});

	// Calculer les statistiques d'occupation
	const totalJours = calendrier.length;
	const joursOccupes = calendrier.filter(j => j.occupe).length;
	const tauxOccupation = totalJours > 0 ? (joursOccupes / totalJours) * 100 : 0;

	// Obtenir les clés des mois triées
	const moisKeys = Object.keys(moisGroupes).sort();
	
	// Calculer les dates par défaut (3 mois avant et 3 mois après aujourd'hui)
	const aujourdhui = new Date();
	const dateDebutDefaut = new Date(aujourdhui.getFullYear(), aujourdhui.getMonth() - 3, 1);
	const dateFinDefaut = new Date(aujourdhui.getFullYear(), aujourdhui.getMonth() + 3 + 1, 0);
	
	// Formater les dates pour les inputs
	const formatDateForInput = (date) => {
		return date.getFullYear() + '-' + String(date.getMonth() + 1).padStart(2, '0') + '-' + String(date.getDate()).padStart(2, '0');
	};
	
	const dateDebutStr = formatDateForInput(dateDebutDefaut);
	const dateFinStr = formatDateForInput(dateFinDefaut);

	let calendar_html = `
		<div id="${calendarId}" style="
			background: #fff;
			border: 1px solid #e5e7eb;
			border-radius: 10px;
			padding: 16px;
			font-family: 'Inter', sans-serif;
		">
			<!-- En-tête avec titre, sélecteur et statistiques -->
			<div style="
				display: flex;
				justify-content: space-between;
				align-items: center;
				margin-bottom: 16px;
				padding-bottom: 12px;
				border-bottom: 1px solid #e5e7eb;
				flex-wrap: wrap;
				gap: 12px;
			">
				<div style="flex: 1; min-width: 200px;">
					<h3 style="margin: 0; font-size: 1rem; font-weight: 600; color: #111827;">Calendrier d'Occupation</h3>
					<p id="${calendarId}_info" style="margin: 4px 0 0 0; font-size: 0.8rem; color: #6b7280;">${moisKeys.length} mois affichés</p>
				</div>
				<div style="display: flex; align-items: center; gap: 12px; flex-wrap: wrap;">
					<div style="display: flex; align-items: center; gap: 8px; font-size: 0.8rem;">
						<label style="color: #374151; font-weight: 500;">Du:</label>
						<input type="date" id="${calendarId}_dateDebut" value="${dateDebutStr}" onchange="filterCalendarByDates('${calendarId}')" style="
							padding: 4px 8px;
							border: 1px solid #d1d5db;
							border-radius: 4px;
							font-size: 0.8rem;
							color: #374151;
							background: #fff;
							outline: none;
						">
					</div>
					<div style="display: flex; align-items: center; gap: 8px; font-size: 0.8rem;">
						<label style="color: #374151; font-weight: 500;">Au:</label>
						<input type="date" id="${calendarId}_dateFin" value="${dateFinStr}" onchange="filterCalendarByDates('${calendarId}')" style="
							padding: 4px 8px;
							border: 1px solid #d1d5db;
							border-radius: 4px;
							font-size: 0.8rem;
							color: #374151;
							background: #fff;
							outline: none;
						">
					</div>
					<button onclick="resetCalendarDates('${calendarId}')" style="
						padding: 4px 8px;
						border: 1px solid #d1d5db;
						border-radius: 4px;
						font-size: 0.75rem;
						color: #6b7280;
						background: #f9fafb;
						cursor: pointer;
						outline: none;
						transition: all 0.2s ease;
					" onmouseover="this.style.background='#f3f4f6'" onmouseout="this.style.background='#f9fafb'">Reset</button>
					<div style="text-align: right;">
					
				</div>
				</div>
			</div>

			<!-- Légende -->
			<div style="
				display: flex;
				align-items: center;
				gap: 16px;
				margin-bottom: 20px;
				font-size: 0.8rem;
				color: #374151;
			">
				<span style="display: flex; align-items: center; gap: 6px;">
					<div style="width: 12px; height: 12px; background: #16a34a; border-radius: 3px;"></div>
					Courte Durée
				</span>
				<span style="display: flex; align-items: center; gap: 6px;">
					<div style="width: 12px; height: 12px; background: #3b82f6; border-radius: 3px;"></div>
					Longue Durée
				</span>
				<span style="display: flex; align-items: center; gap: 6px;">
					<div style="width: 12px; height: 12px; background: #f3f4f6; border: 1px solid #d1d5db; border-radius: 3px;"></div>
					Libre
				</span>
			</div>

			<!-- Grille des mois -->
			<div id="${calendarId}_grid" style="
				display: grid;
				grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
				gap: 10px;
				max-height: 400px;
				overflow-y: auto;
			">
	`;

	// Générer le calendrier pour chaque mois en grille
	moisKeys.forEach((moisKey, index) => {
		const moisData = moisGroupes[moisKey];
		
		calendar_html += `
			<div class="calendar-month" data-month-index="${index}" data-month-key="${moisKey}" style="
				border: 1px solid #e5e7eb;
				border-radius: 4px;
				padding: 6px;
				background: #fafbfc;
				transition: opacity 0.3s ease;
			">
				<div style="
					margin-bottom: 6px;
					color: #374151;
					font-size: 0.7rem;
					font-weight: 600;
					text-align: center;
					text-transform: capitalize;
				">${moisData.mois}</div>
				<div style="
					display: grid;
					grid-template-columns: repeat(7, 1fr);
					gap: 1px;
				">
		`;

		// En-têtes des jours de la semaine
		const joursNoms = ['D', 'L', 'M', 'M', 'J', 'V', 'S'];
		joursNoms.forEach(jour => {
			calendar_html += `
				<div style="
					padding: 2px 1px;
					text-align: center;
					font-size: 0.6rem;
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
					calendar_html += '<div style="height: 18px;"></div>';
				}

		// Créer un tableau de tous les jours du mois
		const dernierJour = new Date(premierJour.getFullYear(), premierJour.getMonth() + 1, 0).getDate();
		const joursParDate = {};
		moisData.jours.forEach(jour => {
			const date = new Date(jour.date);
			joursParDate[date.getDate()] = jour;
		});

		// Ajouter tous les jours du mois
		for (let jourNum = 1; jourNum <= dernierJour; jourNum++) {
			const jour = joursParDate[jourNum];
			const isOccupe = jour ? jour.occupe : false;
			const isLongueduree = jour ? jour.type_location === 'Longue Durée' : false;
			
			let bgColor, textColor, borderColor;
			if (isOccupe) {
				if (isLongueduree) {
					bgColor = '#3b82f6';  // Bleu pour longue durée
					borderColor = '#2563eb';
				} else {
					bgColor = '#16a34a';  // Vert pour courte durée
					borderColor = '#15803d';
				}
				textColor = '#fff';
			} else {
				bgColor = '#f9fafb';
				textColor = '#374151';
				borderColor = '#e5e7eb';
			}
			
			const tooltip = jour && isOccupe ? `${jour.type_location} - ${jour.locataire}` : 'Libre';
			const clickHandler = jour && jour.occupe && jour.location_id ? `onclick="showAppartementLocationDetails('${jour.location_id}', '${jour.type_location}')"` : '';
			
			calendar_html += `
				<div style="
					height: 18px;
					display: flex;
					align-items: center;
					justify-content: center;
					background: ${bgColor};
					color: ${textColor};
					border: 1px solid ${borderColor};
					border-radius: 2px;
					font-size: 0.6rem;
					font-weight: ${isOccupe ? '600' : '400'};
					cursor: ${jour && jour.occupe ? 'pointer' : 'default'};
					transition: all 0.2s ease;
					box-shadow: ${isOccupe ? '0 1px 1px rgba(0, 0, 0, 0.06)' : 'none'};
				" title="${tooltip}" ${clickHandler} onmouseover="this.style.transform='scale(1.05)'; this.style.zIndex='10';" onmouseout="this.style.transform='scale(1)'; this.style.zIndex='1';">
					${jourNum}
				</div>
			`;
		}

		calendar_html += '</div></div>';
	});

	calendar_html += '</div></div>';
	
	// Ajouter les données et la fonction de filtrage
	calendar_html += `
		<script>
			// Stocker les données du calendrier
			window.calendarData = window.calendarData || {};
			window.calendarData['${calendarId}'] = {
				moisKeys: ${JSON.stringify(moisKeys)},
				moisGroupes: ${JSON.stringify(moisGroupes)},
				totalJours: ${totalJours},
				joursOccupes: ${joursOccupes},
				dateDebutDefaut: '${dateDebutStr}',
				dateFinDefaut: '${dateFinStr}'
			};
			
			// Fonction de filtrage par dates
			window.filterCalendarByDates = function(calendarId) {
				const dateDebutInput = document.getElementById(calendarId + '_dateDebut');
				const dateFinInput = document.getElementById(calendarId + '_dateFin');
				
				// Vérifier que les éléments existent avant d'accéder à leurs propriétés
				if (!dateDebutInput || !dateFinInput) {
					return;
				}
				
				const dateDebut = new Date(dateDebutInput.value);
				const dateFin = new Date(dateFinInput.value);
				
				if (!dateDebutInput.value || !dateFinInput.value) {
					return;
				}
				
				const grid = document.getElementById(calendarId + '_grid');
				const months = grid.querySelectorAll('.calendar-month');
				const data = window.calendarData[calendarId];
				
				let visibleMonths = 0;
				let filteredJours = 0;
				let filteredOccupes = 0;
				
				months.forEach((month) => {
					const monthKey = month.getAttribute('data-month-key');
					const [annee, mois] = monthKey.split('-');
					const premierJourMois = new Date(parseInt(annee), parseInt(mois) - 1, 1);
					const dernierJourMois = new Date(parseInt(annee), parseInt(mois), 0);
					
					// Vérifier si le mois chevauche avec la période sélectionnée
					const shouldShow = (premierJourMois <= dateFin && dernierJourMois >= dateDebut);
					
					if (shouldShow) {
						month.style.display = 'block';
						month.style.opacity = '1';
						visibleMonths++;
						
						// Calculer les statistiques pour ce mois (seulement les jours dans la période)
						const monthData = data.moisGroupes[monthKey];
						if (monthData) {
							monthData.jours.forEach(jour => {
								const dateJour = new Date(jour.date);
								if (dateJour >= dateDebut && dateJour <= dateFin) {
									filteredJours++;
									if (jour.occupe) {
										filteredOccupes++;
									}
								}
							});
						}
					} else {
						month.style.display = 'none';
						month.style.opacity = '0';
					}
				});
				
				// Mettre à jour les statistiques
				const tauxFiltre = filteredJours > 0 ? (filteredOccupes / filteredJours) * 100 : 0;
				const infoElement = document.getElementById(calendarId + '_info');
				const tauxElement = document.getElementById(calendarId + '_taux');
				
				if (infoElement) {
					infoElement.textContent = visibleMonths + ' mois affichés';
				}
				if (tauxElement) {
					tauxElement.textContent = tauxFiltre.toFixed(1) + '%';
				}
			};
			
			// Fonction de reset des dates
			window.resetCalendarDates = function(calendarId) {
				const data = window.calendarData[calendarId];
				const dateDebutInput = document.getElementById(calendarId + '_dateDebut');
				const dateFinInput = document.getElementById(calendarId + '_dateFin');
				
				if (!dateDebutInput || !dateFinInput || !data) {
					return;
				}
				
				dateDebutInput.value = data.dateDebutDefaut;
				dateFinInput.value = data.dateFinDefaut;
				filterCalendarByDates(calendarId);
			};
			
			// Appliquer le filtre par défaut
			setTimeout(() => filterCalendarByDates('${calendarId}'), 100);
		</script>
	`;
	
	return calendar_html;
}

// Fonction globale pour afficher les détails d'une location dans un modal
window.showAppartementLocationDetails = function(location_id, type_location) {
	const doctype = type_location === 'Longue Durée' ? 'Location Longue Duree' : 'Location Courte Duree';
	
	frappe.call({
		method: 'frappe.client.get',
		args: {
			doctype: doctype,
			name: location_id
		},
		callback: function(r) {
			if (r.message) {
				const location = r.message;
				
				// Créer le modal avec les informations de la location
				const dialog = new frappe.ui.Dialog({
					title: `Détails de la ${type_location} - ${location.name}`,
					size: 'large',
					fields: [
						{
							fieldtype: 'HTML',
							fieldname: 'location_details',
							options: createLocationDetailsHTML(location, type_location)
						}
					],
					primary_action_label: __('Voir'),
					primary_action: function() {
						// Naviguer vers la location
						frappe.set_route('Form', doctype, location_id);
						dialog.hide();
					}
				});
				dialog.show();
			}
		}
	});
};

// Fonction pour créer le HTML des détails de location
function createLocationDetailsHTML(location, type_location) {
	const isLongueduree = type_location === 'Longue Durée';
	
	return `
		<div style="padding: 12px; display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; align-items: stretch;">
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
					<div style="margin-bottom: 6px; display: flex; justify-content: space-between;"><span style="font-weight: 500;">Date début:</span> <span style="color: #a16207;">${frappe.datetime.str_to_user(location.date_debut)}</span></div>
					<div style="margin-bottom: 6px; display: flex; justify-content: space-between;"><span style="font-weight: 500;">Date fin:</span> <span style="color: #a16207;">${frappe.datetime.str_to_user(location.date_fin)}</span></div>
					<div style="display: flex; justify-content: space-between;"><span style="font-weight: 500;">${isLongueduree ? 'Durée:' : 'Nuits:'}</span> <span style="background: #f59e0b; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600;">${isLongueduree ? 'Mensuel' : (location.nombre_nuits || 'N/A')}</span></div>
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
					${isLongueduree ? `
						<div style="margin-bottom: 6px; display: flex; justify-content: space-between;"><span style="font-weight: 500;">Loyer mensuel:</span> <span style="color: #16a34a; font-weight: 600;">${format_currency(location.loyer_mensuel_locataire || 0, 'EUR')}</span></div>
						<div style="margin-bottom: 6px; display: flex; justify-content: space-between;"><span style="font-weight: 500;">Coût mensuel:</span> <span style="color: #16a34a; font-weight: 600;">${format_currency(location.loyer_mensuel_proprietaire || 0, 'EUR')}</span></div>
					` : `
						<div style="margin-bottom: 6px; display: flex; justify-content: space-between;"><span style="font-weight: 500;">Prix journalier:</span> <span style="color: #16a34a; font-weight: 600;">${format_currency(location.prix_journalier_locataire || 0, 'EUR')}</span></div>
						<div style="margin-bottom: 6px; display: flex; justify-content: space-between;"><span style="font-weight: 500;">Coût journalier:</span> <span style="color: #16a34a; font-weight: 600;">${format_currency(location.prix_journalier_proprietaire || 0, 'EUR')}</span></div>
					`}
					<div style="display: flex; justify-content: space-between; padding: 8px; background: rgba(34,197,94,0.1); border-radius: 8px; margin-top: 4px;"><span style="font-weight: 600;">Montant total:</span> <span style="color: #16a34a; font-weight: 700; font-size: 0.9rem;">${format_currency((isLongueduree ? location.loyer_mensuel_locataire : location.montant_total_locataire) || 0, 'EUR')}</span></div>
				</div>
			</div>
		</div>
	`;
}
