// Copyright (c) 2025, IntraPro and contributors
// For license information, please see license.txt

frappe.ui.form.on("Caisse", {
	refresh: function(frm) {
		frm.trigger('update_solde_display');
	},

	solde_actuel: function(frm) {
		frm.trigger('update_solde_display');
	},

	update_solde_display: function(frm) {
		if (!frm || !frm.doc) return;
		
		// Générer le HTML du solde
		const solde_html = createCaisseDashboard(frm.doc);
		
		// Mettre à jour le champ HTML
		if (frm.fields_dict && frm.fields_dict['solde_html']) {
			$(frm.fields_dict['solde_html'].wrapper).html(solde_html);
		}
	}
});

// Fonction pour créer le dashboard de la caisse
function createCaisseDashboard(doc) {
	try {
		const solde = doc.solde_actuel || 0;
		const date_maj = doc.date_derniere_maj || "Non définie";
		
		// Déterminer la couleur et l'icône selon le solde
		let color_class, icon, status_text, status_color;
		if (solde > 0) {
			color_class = "#16a34a";
			icon = "fa fa-arrow-up";
			status_text = "Positif";
			status_color = "#dcfce7";
		} else if (solde < 0) {
			color_class = "#dc2626";
			icon = "fa fa-arrow-down";
			status_text = "Négatif";
			status_color = "#fee2e2";
		} else {
			color_class = "#f59e0b";
			icon = "fa fa-minus";
			status_text = "Nul";
			status_color = "#fef3c7";
		}
		
		// Formater le montant
		const montant_formate = format_currency_caisse(solde);
		
		// Générer le HTML
		const html = `
		<style>
			.caisse-dashboard {
				font-family: 'Inter', sans-serif;
				padding: 16px;
				max-width: 100%;
			}
			
			.caisse-card {
				background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
				border: 1px solid #ddd;
				border-radius: 12px;
				padding: 24px;
				box-shadow: 0 4px 6px rgba(0, 0, 0, 0.07);
				position: relative;
				overflow: hidden;
			}
			
			.caisse-header {
				display: flex;
				align-items: center;
				justify-content: space-between;
				margin-bottom: 20px;
			}
			
			.caisse-title {
				display: flex;
				align-items: center;
				color: #495057;
				font-size: 1.5rem;
				font-weight: 600;
				margin: 0;
			}
			
			.caisse-icon {
				margin-right: 12px;
				color: #6c757d;
				font-size: 1.8rem;
			}
			
			.caisse-status {
				background: ${status_color};
				color: ${color_class};
				padding: 8px 16px;
				border-radius: 20px;
				font-size: 0.9rem;
				font-weight: 600;
				border: 1px solid ${color_class};
			}
			
			.caisse-amount-section {
				display: flex;
				align-items: center;
				justify-content: space-between;
				margin-bottom: 20px;
			}
			
			.caisse-amount {
				color: ${color_class};
				font-size: 3rem;
				font-weight: 700;
				margin: 0;
				line-height: 1;
			}
			
			.caisse-trend-icon {
				color: ${color_class};
				font-size: 4rem;
				opacity: 0.3;
			}
			
			.caisse-footer {
				display: flex;
				justify-content: space-between;
				align-items: center;
				padding-top: 16px;
				border-top: 1px solid #dee2e6;
				font-size: 0.85rem;
				color: #6c757d;
			}
			
			.caisse-info {
				display: flex;
				align-items: center;
				gap: 6px;
			}
			
			@media (max-width: 768px) {
				.caisse-dashboard {
					padding: 12px;
				}
				
				.caisse-card {
					padding: 16px;
				}
				
				.caisse-header {
					flex-direction: column;
					align-items: flex-start;
					gap: 12px;
				}
				
				.caisse-title {
					font-size: 1.2rem;
				}
				
				.caisse-amount {
					font-size: 2.2rem;
				}
				
				.caisse-trend-icon {
					font-size: 3rem;
				}
				
				.caisse-footer {
					flex-direction: column;
					align-items: flex-start;
					gap: 8px;
				}
			}
		</style>
		
		<div class="caisse-dashboard">
			<div class="caisse-card">
				<div class="caisse-header">
					<h2 class="caisse-title">
						<i class="fa fa-university caisse-icon"></i>
						Solde de la Caisse
					</h2>
					<span class="caisse-status">${status_text}</span>
				</div>
				
				<div class="caisse-amount-section">
					<h1 class="caisse-amount">${montant_formate}</h1>
					<div class="caisse-trend-icon">
						<i class="${icon}"></i>
					</div>
				</div>
				
				<div class="caisse-footer">
					<div class="caisse-info">
						<i class="fa fa-clock-o"></i>
						<span>Dernière mise à jour: ${frappe.datetime.str_to_user(date_maj) || "Non définie"}</span>
					</div>
					
				</div>
			</div>
		</div>
		`;
		
		return html;
		
	} catch (e) {
		console.error('Erreur lors de la génération du dashboard caisse:', e);
		return '<div style="padding: 20px; color: #e74c3c;">Erreur lors de la génération du dashboard</div>';
	}
}

// Fonction pour formater les devises
function format_currency_caisse(value) {
	if (!value) value = 0;
	const formatted = parseFloat(value).toFixed(2).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
	return `€ ${formatted}`;
}
