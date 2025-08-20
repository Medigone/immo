# Copyright (c) 2024, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
import re


class Referent(Document):
	"""Doctype pour gérer les référents et leurs commissions"""
	
	def validate(self):
		"""Validation des données du référent"""
		self.validate_email()
		self.validate_commission_percentage()
	
	def validate_email(self):
		"""Valide le format de l'email"""
		if self.email:
			email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
			if not re.match(email_pattern, self.email):
				frappe.throw(_("Format d'email invalide"))
	
	def validate_commission_percentage(self):
		"""Valide le pourcentage de commission"""
		if self.pourcentage_commission_defaut is not None:
			if self.pourcentage_commission_defaut < 0 or self.pourcentage_commission_defaut > 100:
				frappe.throw(_("Le pourcentage de commission doit être entre 0 et 100"))
	
	def before_save(self):
		"""Actions avant sauvegarde"""
		# Normalise le nom complet
		if self.nom_complet:
			self.nom_complet = self.nom_complet.strip().title()
	
	def on_update(self):
		"""Actions après mise à jour"""
		# Si le référent devient inactif, met à jour les locations courtes durée en cours
		if not self.actif:
			self.update_active_short_term_rentals()
	
	def update_active_short_term_rentals(self):
		"""Met à jour les locations courtes durée actives si le référent devient inactif"""
		active_rentals = frappe.get_all(
			"Location Courte Duree",
			filters={
				"referent_id": self.name,
				"statut": ["in", ["Brouillon", "Confirmé"]]
			},
			fields=["name"]
		)
		
		for rental in active_rentals:
			rental_doc = frappe.get_doc("Location Courte Duree", rental.name)
			rental_doc.add_comment(
				"Comment",
				f"Référent {self.nom_complet} désactivé - Commission mise à jour"
			)
	
	@frappe.whitelist()
	def get_commissions(self, limit=None):
		"""Récupère les commissions du référent avec limite optionnelle"""
		query_params = {
			"doctype": "Commission",
			"filters": {"referent_id": self.name},
			"fields": [
				"name", "location_courte_duree_id", "montant_commission",
				"pourcentage_commission", "date_creation", "statut_paiement"
			],
			"order_by": "date_creation desc"
		}
		
		# Ajouter la limite si spécifiée
		if limit:
			query_params["limit"] = limit
			
		return frappe.get_all(**query_params)
	
	@frappe.whitelist()
	def get_total_commissions(self, start_date=None, end_date=None):
		"""Calcule le total des commissions sur une période"""
		filters = {"referent_id": self.name}
		
		if start_date:
			filters["date_creation"] = [">=", start_date]
		if end_date:
			if "date_creation" in filters:
				filters["date_creation"] = ["between", [start_date, end_date]]
			else:
				filters["date_creation"] = ["<=", end_date]
		
		commissions = frappe.get_all(
			"Commission",
			filters=filters,
			fields=["montant_commission", "statut_paiement"]
		)
		
		total_commissions = sum(c.montant_commission for c in commissions)
		commissions_payees = sum(
			c.montant_commission for c in commissions 
			if c.statut_paiement == "Payé"
		)
		commissions_en_attente = total_commissions - commissions_payees
		
		return {
			"total_commissions": total_commissions,
			"commissions_payees": commissions_payees,
			"commissions_en_attente": commissions_en_attente,
			"nombre_commissions": len(commissions)
		}
	
	@frappe.whitelist()
	def get_recent_short_term_rentals(self, limit=10):
		"""Récupère les locations courtes durée récentes du référent"""
		return frappe.get_all(
			"Location Courte Duree",
			filters={"referent_id": self.name},
			fields=[
				"name", "appartement_id", "locataire_nom", "date_debut",
				"date_fin", "montant_total_locataire", "commission_referent", "statut"
			],
			order_by="date_debut desc",
			limit=limit
		)
	
	@frappe.whitelist()
	def calculate_performance_metrics(self, year=None):
		"""Calcule les métriques de performance du référent"""
		if not year:
			year = frappe.utils.nowdate()[:4]
		
		start_date = f"{year}-01-01"
		end_date = f"{year}-12-31"
		
		# Récupère les locations courtes durée de l'année
		rentals = frappe.get_all(
			"Location Courte Duree",
			filters={
				"referent_id": self.name,
				"date_debut": ["between", [start_date, end_date]]
			},
			fields=[
				"montant_total_locataire", "commission_referent",
				"nombre_nuits", "statut"
			]
		)
		
		confirmed_rentals = [r for r in rentals if r.statut in ["Confirmé", "Terminé"]]
		
		total_revenue = sum(r.montant_total_locataire for r in confirmed_rentals)
		total_commission = sum(r.commission_referent for r in confirmed_rentals)
		total_nights = sum(r.nombre_nuits for r in confirmed_rentals)
		
		return {
			"annee": year,
			"nombre_locations": len(confirmed_rentals),
			"chiffre_affaires_genere": total_revenue,
			"total_commissions": total_commission,
			"total_nuits_vendues": total_nights,
			"commission_moyenne_par_location": total_commission / len(confirmed_rentals) if confirmed_rentals else 0,
			"taux_commission_moyen": (total_commission / total_revenue * 100) if total_revenue > 0 else 0
		}
	
	@frappe.whitelist()
	def get_dashboard_html(self):
		"""Génère le HTML du tableau de bord des commissions avec le style moderne"""
		commission_data = self.get_total_commissions()
		
		# Récupérer les commissions récentes pour affichage (limitées à 10 max)
		commissions_recentes = self.get_commissions(limit=10)
		
		# Calculer le pourcentage de paiement
		total_commissions = commission_data.get('total_commissions', 0)
		commissions_payees = commission_data.get('commissions_payees', 0)
		pourcentage_paiement = (commissions_payees / total_commissions * 100) if total_commissions > 0 else 0
		
		html = f"""
		<style>
			.dashboard-container {{
				display: grid;
				grid-template-rows: auto auto;
				gap: 16px;
				font-family: 'Inter', sans-serif;
				padding: 16px;
				max-width: 100%;
				overflow-x: hidden;
			}}
			
			.stats-grid {{
				display: grid;
				grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
				gap: 12px;
				align-items: stretch;
			}}
			
			.details-grid {{
				display: grid;
				grid-template-columns: 1fr;
				gap: 20px;
			}}
			
			@media (max-width: 768px) {{
				.dashboard-container {{
					padding: 12px;
					gap: 12px;
				}}
				
				.stats-grid {{
					grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
					gap: 8px;
				}}
				
				.stat-card {{
					min-height: 100px !important;
					padding: 8px 10px !important;
				}}
				
				.stat-title {{
					font-size: 0.75rem !important;
				}}
				
				.stat-value {{
					font-size: 1.1rem !important;
				}}
			}}
			
			@media (max-width: 480px) {{
				.dashboard-container {{
					padding: 8px;
				}}
				
				.stats-grid {{
					grid-template-columns: 1fr 1fr;
					gap: 6px;
				}}
				
				.stat-card {{
					min-height: 90px !important;
					padding: 6px 8px !important;
				}}
				
				.stat-title {{
					font-size: 0.7rem !important;
					line-height: 1.1 !important;
				}}
				
				.stat-value {{
					font-size: 1rem !important;
				}}
			}}
		</style>
		<div class="dashboard-container">
			<!-- Ligne des 4 cartes statistiques -->
			<div class="stats-grid">
				{self._create_stat_card("Total Commissions", f"{commission_data.get('total_commissions', 0):,.2f} €", "Montant total généré", None)}
				{self._create_stat_card("Commissions Payées", f"{commission_data.get('commissions_payees', 0):,.2f} €", "Montant déjà versé", pourcentage_paiement)}
				{self._create_stat_card("En Attente", f"{commission_data.get('commissions_en_attente', 0):,.2f} €", "Montant à verser", None)}
				{self._create_stat_card("Nombre Total", str(commission_data.get('nombre_commissions', 0)), "Commissions créées", None)}
			</div>
			
			<!-- Section des commissions récentes -->
			<div class="details-grid">
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
						gap: 8px;
					">
						<span style="
							width: 8px; 
							height: 8px; 
							background: #3b82f6; 
							border-radius: 50%; 
							margin-right: 8px;
						"></span>
						Commissions Récentes
					</div>
					
					<!-- Barre de progression -->
					<div style="margin-bottom: 16px;">
						<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
							<span style="font-weight: 500; color: #495057; font-size: 0.8rem;">Taux de paiement:</span>
							<span style="font-weight: bold; color: {'#16a34a' if pourcentage_paiement >= 80 else '#f59e0b' if pourcentage_paiement >= 50 else '#dc2626'}; font-size: 0.85rem;">
								{pourcentage_paiement:.1f}%
							</span>
						</div>
						<div style="background: #e9ecef; border-radius: 10px; height: 8px; overflow: hidden;">
							<div style="background: {'#16a34a' if pourcentage_paiement >= 80 else '#f59e0b' if pourcentage_paiement >= 50 else '#dc2626'}; height: 100%; width: {pourcentage_paiement}%; transition: width 0.3s ease;"></div>
						</div>
					</div>
					
					<!-- Liste des commissions -->
					<div style="font-size: 0.8rem; color: #6b7280; line-height: 1.6;">
						{self._generate_commissions_list(commissions_recentes)}
					</div>
				</div>
			</div>
		</div>
		"""
		
		return html
	
	def _create_stat_card(self, title, main_value, footer_value, percentage):
		"""Crée une carte de statistique avec le style moderne"""
		show_badge = percentage is not None
		if percentage is not None:
			badge_color = '#16a34a' if percentage >= 80 else '#f59e0b' if percentage >= 50 else '#dc2626' if percentage > 0 else '#6b7280'
		else:
			badge_color = '#6b7280'
		
		return f"""
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
			<div class="stat-title" style="font-size: 0.8rem; color: #6b7280; line-height: 1.2;">{title}</div>
			
			<div class="stat-content" style="display: flex; align-items: center; justify-content: space-between; margin: 6px 0; flex-wrap: wrap; gap: 4px;">
				<div class="stat-value" style="font-size: 1.2rem; font-weight: 700; color: #111827; word-break: break-word; flex: 1; min-width: 0;">{main_value}</div>
				{f'<div class="stat-badge" style="font-size: 0.7rem; padding: 2px 6px; border-radius: 9999px; border: 1px solid {badge_color}; color: {badge_color}; background: transparent; white-space: nowrap; flex-shrink: 0;">{percentage:.0f}%</div>' if show_badge else ''}
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
				{footer_value}
			</div>
		</div>
		"""
	
	def _generate_commissions_list(self, commissions):
		"""Génère la liste des commissions récentes (limitée pour l'affichage)"""
		if not commissions:
			return '<div style="text-align: center; color: #9ca3af; font-style: italic; padding: 20px;">Aucune commission trouvée</div>'
		
		# Limiter l'affichage à 8 commissions maximum pour éviter une liste trop longue
		commissions_to_display = commissions[:8]
		total_commissions = len(commissions)
		is_truncated = total_commissions > 8
		
		commissions_html = ""
		for commission in commissions_to_display:
			status_color = self._get_status_color(commission.statut_paiement)
			# Créer les liens cliquables pour les IDs en utilisant les routes Frappe appropriées
			# Utiliser onclick avec frappe.set_route pour une navigation appropriée dans Frappe
			commission_onclick = f"frappe.set_route('Form', 'Commission', '{commission.name}'); return false;"
			location_onclick = f"frappe.set_route('Form', 'Location Courte Duree', '{commission.location_courte_duree_id}'); return false;" if commission.location_courte_duree_id else ""
			
			# Créer le HTML de la location séparément pour éviter les problèmes d'échappement
			if commission.location_courte_duree_id:
				location_html = ('<a href="#" onclick="{onclick}" style="color: #059669; text-decoration: none; border-bottom: 1px dotted #059669; cursor: pointer;" '
								'onmouseover="this.style.color=\'#047857\'; this.style.borderBottom=\'1px solid #047857\'" '
								'onmouseout="this.style.color=\'#059669\'; this.style.borderBottom=\'1px dotted #059669\'" '
								'title="Cliquer pour ouvrir la location">{location_id}</a>').format(
									onclick=location_onclick, 
									location_id=commission.location_courte_duree_id
								)
			else:
				location_html = 'N/A'
			
			commissions_html += f"""
			<div style="
				display: flex;
				justify-content: space-between;
				align-items: center;
				padding: 8px;
				margin-bottom: 6px;
				background: #f9fafb;
				border-radius: 6px;
				border-left: 3px solid {status_color['border']};
				font-size: 0.75rem;
			">
				<div style="flex: 1; min-width: 0;">
					<div style="font-weight: 600; color: #374151; margin-bottom: 2px;">
						<a href="#" onclick="{commission_onclick}" style="
							color: #2563eb;
							text-decoration: none;
							border-bottom: 1px dotted #2563eb;
							cursor: pointer;
						" 
						 onmouseover="this.style.color='#1d4ed8'; this.style.borderBottom='1px solid #1d4ed8'" 
						 onmouseout="this.style.color='#2563eb'; this.style.borderBottom='1px dotted #2563eb'"
						 title="Cliquer pour ouvrir la commission">{commission.name}</a>
					</div>
					<div style="color: #6b7280; font-size: 0.7rem;">
						{location_html}
					</div>
				</div>
				<div style="text-align: right;">
					<div style="font-weight: 700; color: #111827; margin-bottom: 2px;">{commission.montant_commission:,.2f} €</div>
					<div style="
						background: {status_color['background']};
						color: {status_color['text']};
						padding: 1px 4px;
						border-radius: 4px;
						font-size: 0.6rem;
						font-weight: 600;
					">{commission.statut_paiement}</div>
				</div>
			</div>
			"""
		
		# Ajouter un message si la liste est tronquée
		if is_truncated:
			commissions_html += f"""
			<div style="
				text-align: center;
				color: #6b7280;
				font-style: italic;
				padding: 12px 8px;
				border-top: 1px solid #e5e7eb;
				margin-top: 8px;
				font-size: 0.7rem;
			">
				... et {total_commissions - 8} autres commissions
				<br><span style="font-size: 0.65rem;">Consultez la liste complète dans l'onglet Commissions</span>
			</div>
			"""
		
		return commissions_html
	
	def _get_status_color(self, status):
		"""Retourne les couleurs pour les statuts de paiement"""
		if status == 'Payé':
			return {
				'background': '#dcfce7',
				'text': '#166534',
				'border': '#16a34a'
			}
		elif status == 'En attente':
			return {
				'background': '#fef3c7',
				'text': '#92400e',
				'border': '#f59e0b'
			}
		elif status == 'Annulé':
			return {
				'background': '#fee2e2',
				'text': '#991b1b',
				'border': '#dc2626'
			}
		else:
			return {
				'background': '#f3f4f6',
				'text': '#374151',
				'border': '#9ca3af'
			}