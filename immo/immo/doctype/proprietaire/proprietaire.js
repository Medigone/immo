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
			<!-- Section Financière -->
			<div>
				
				<div style="
					display: grid;
					grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
					gap: 12px;
					align-items: stretch;
				">
					${createStatCard("Appartements", general.total_appartements || 0, "Total possédés", null)}
					${createStatCard("Revenus Annuels", format_currency(financial.total_revenus_locataire || 0, 'EUR'), "Année en cours", null)}
					${createStatCard("Marge Nette", format_currency(financial.marge_nette || 0, 'EUR'), "Rentabilité : " + marge_percentage.toFixed(1) + "%", marge_percentage)}
				</div>
			</div>
			
			<!-- Section Paiements -->
			<div>
				
				<div style="
					display: grid;
					grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
					gap: 12px;
					align-items: stretch;
				">
					${createStatCard("Paiements Reçus", format_currency(payments.montant_proprietaires_paye || 0, 'EUR'), "Versements effectués", null)}
					${createStatCard("En Attente", format_currency(payments.montant_proprietaires_en_attente || 0, 'EUR'), "Versements à faire", null)}
					${createStatCard("Montant Versé", format_currency(payments.montant_proprietaires_paye || 0, 'EUR'), "Total année", null)}
				</div>
			</div>
		</div>
	`;

	return dashboard_html;
}

// Fonction utilitaire pour créer une carte de statistique (style appartement.js)
function createStatCard(title, mainValue, footerValue, percentage) {
	let showBadge = percentage !== null && percentage !== undefined;
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

// Fonction utilitaire pour formater les devises (style appartement.js)
function format_currency(value, currency) {
	// Formatage manuel pour éviter le HTML généré par frappe.format
	if (!value) value = 0;
	const formatted = parseFloat(value).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
	return `€ ${formatted}`;
}
