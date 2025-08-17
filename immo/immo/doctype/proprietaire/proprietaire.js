// Copyright (c) 2025, IntraPro and contributors
// For license information, please see license.txt

frappe.ui.form.on("Proprietaire", {
	refresh(frm) {
		if (frm.doc.name && !frm.is_new()) {
			frm.trigger('load_dashboard');
		}
	},

	load_dashboard(frm) {
		// Afficher un indicateur de chargement
		const loading_html = `
			<div style="
				display: flex;
				justify-content: center;
				align-items: center;
				height: 200px;
				font-family: 'Inter', sans-serif;
				color: #6b7280;
			">
				<div>Chargement des métriques...</div>
			</div>
		`;
		$(frm.fields_dict['dashboard'].wrapper).html(loading_html);

		// Appeler l'API pour récupérer les statistiques du propriétaire
		frappe.call({
			method: 'immo.api.proprietaire.get_proprietaire_dashboard_data',
			args: {
				proprietaire_id: frm.doc.name
			},
			callback: function(r) {
				if (r.message && r.message.success) {
					const data = r.message;
					const dashboard_html = createProprietaireDashboard(data, frm.doc);
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
							<div>Erreur lors du chargement des métriques</div>
						</div>
					`;
					$(frm.fields_dict['dashboard'].wrapper).html(error_html);
				}
			}
		});
	}
});

// Fonction pour créer le dashboard du propriétaire
function createProprietaireDashboard(data, proprietaire) {
	const general = data.general || {};
	const financial = data.financial || {};
	const payments = data.payments || {};
	const occupancy = data.occupancy || {};

	// Calculer les pourcentages pour les barres de progression
	const taux_occupation = occupancy.taux_occupation || 0;
	const marge_percentage = financial.marge_percentage || 0;
	const taux_paiement = payments.taux_paiement_locataires || 0;

	let dashboard_html = `
		<div style="
			display: grid;
			grid-template-rows: auto auto;
			gap: 16px;
			font-family: 'Inter', sans-serif;
			padding: 16px;
		">
			<!-- Ligne des 4 cartes statistiques principales -->
			<div style="
				display: grid;
				grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
				gap: 12px;
				align-items: stretch;
			">
				${createStatCard("Appartements", general.total_appartements || 0, "Total possédés", null)}
				${createStatCard("Revenus Annuels", format_currency(financial.total_revenus_locataire || 0, 'EUR'), "Année en cours", null)}
				${createStatCard("Marge Nette", format_currency(financial.marge_nette || 0, 'EUR'), "Rentabilité : " + marge_percentage.toFixed(1) + "%", marge_percentage)}
				${createStatCard("Taux d'Occupation", taux_occupation.toFixed(1) + "%", "Moyenne portfolio", taux_occupation)}
			</div>
			<!-- Ligne des métriques de paiement -->
			<div style="
				display: grid;
				grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
				gap: 12px;
				align-items: stretch;
			">
				${createStatCard("Paiements Reçus", payments.proprietaires_payes || 0, "Versements effectués", null)}
				${createStatCard("En Attente", payments.proprietaires_en_attente || 0, "Versements à faire", null)}
				${createStatCard("Montant Versé", format_currency(payments.montant_proprietaires_paye || 0, 'EUR'), "Total année", null)}
				${createStatCard("Taux de Paiement", taux_paiement.toFixed(1) + "%", "Locataires à jour", taux_paiement)}
			</div>
		</div>
	`;

	return dashboard_html;
}

// Fonction utilitaire pour créer une carte de statistique
function createStatCard(title, value, subtitle, percentage) {
	let progressBar = '';
	let progressColor = '#10b981'; // Vert par défaut

	if (percentage !== null && percentage !== undefined) {
		// Déterminer la couleur selon le pourcentage
		if (percentage >= 80) {
			progressColor = '#10b981'; // Vert
		} else if (percentage >= 60) {
			progressColor = '#f59e0b'; // Orange
		} else {
			progressColor = '#ef4444'; // Rouge
		}

		progressBar = `
			<div style="
				width: 100%;
				height: 4px;
				background-color: #e5e7eb;
				border-radius: 2px;
				margin-top: 8px;
				overflow: hidden;
			">
				<div style="
					width: ${Math.min(percentage, 100)}%;
					height: 100%;
					background-color: ${progressColor};
					transition: width 0.3s ease;
				"></div>
			</div>
		`;
	}

	return `
		<div style="
			background: #fff;
			border: 1px solid #e5e7eb;
			border-radius: 10px;
			padding: 16px;
			box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
			transition: transform 0.2s ease, box-shadow 0.2s ease;
			cursor: default;
		" onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 4px 12px rgba(0, 0, 0, 0.15)'" onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 1px 3px rgba(0, 0, 0, 0.1)'">
			<div style="
				font-size: 0.875rem;
				font-weight: 500;
				color: #6b7280;
				margin-bottom: 4px;
			">${title}</div>
			<div style="
				font-size: 1.5rem;
				font-weight: 700;
				color: #111827;
				margin-bottom: 4px;
			">${value}</div>
			<div style="
				font-size: 0.75rem;
				color: #9ca3af;
			">${subtitle}</div>
			${progressBar}
		</div>
	`;
}

// Fonction utilitaire pour formater les devises
function format_currency(amount, currency) {
	if (typeof amount !== 'number') {
		amount = parseFloat(amount) || 0;
	}
	return new Intl.NumberFormat('fr-FR', {
		style: 'currency',
		currency: currency || 'EUR'
	}).format(amount);
}
