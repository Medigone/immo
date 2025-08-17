// Copyright (c) 2025, IntraPro and contributors
// For license information, please see license.txt

frappe.ui.form.on('Location Courte Duree', {
	refresh: function(frm) {
		// SUPPRIMÉ: Affichage du type de location
		// update_type_location_display(frm);
		
		// Ajouter les boutons de création de paiements
		if (!frm.doc.__islocal) {
			frm.add_custom_button(__('Paiement Locataire'), function() {
				create_paiement_locataire(frm);
			}, __('Créer'));
			
			frm.add_custom_button(__('Paiement Propriétaire'), function() {
				create_paiement_proprietaire(frm);
			}, __('Créer'));
			
			// Bouton pour rafraîchir le statut des paiements
			frm.add_custom_button(__('Rafraîchir Statut Paiements'), function() {
				refresh_payment_status(frm);
			}, __('Actions'));
		}
	},
	
	location_bloc_id: function(frm) {
		// SUPPRIMÉ: Mise à jour de l'affichage du type de location
		// update_type_location_display(frm);
		
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

// FONCTION SUPPRIMÉE - Affichage du type de location désactivé
// function update_type_location_display(frm) {
//	// Calculer le type de location (sans affichage)
//	const type_location = frm.doc.location_bloc_id ? 'Sous-location' : 'Directe';
//	
//	// Mettre à jour le champ caché
//	frm.set_value('type_location', type_location);
//	
//	// SUPPRIMÉ: Affichage des indicateurs visuels du type de location
//	// if (frm.doc.location_bloc_id) {
//	//	frm.dashboard.add_indicator(__('Type: Sous-location'), 'blue');
//	// } else {
//	//	frm.dashboard.add_indicator(__('Type: Location directe'), 'green');
//	// }
// }

// Fonction pour créer un paiement locataire
function create_paiement_locataire(frm) {
	// Récupérer les informations de base
	const defaultData = {
		location_courte_duree_id: frm.doc.name,
		status: 'Nouveau',
		type_paiement: 'Court Séjour',
		montant: frm.doc.montant_total_locataire || 0,
		date_paiement: frappe.datetime.get_today(),
		methode_paiement: 'Virement'
	};
	
	// Créer le prompt avec les valeurs par défaut
	const dialog = new frappe.ui.Dialog({
		title: __('Créer un Paiement Locataire'),
		fields: [
			{
				fieldtype: 'Link',
				fieldname: 'location_courte_duree_id',
				label: __('Location Courte Durée'),
				options: 'Location Courte Duree',
				default: defaultData.location_courte_duree_id,
				read_only: 1
			},
			{
				fieldtype: 'Select',
				fieldname: 'type_paiement',
				label: __('Type de Paiement'),
				options: 'Court Séjour\nAcompte\nCaution\nFrais de dossier\nPénalité\nAutre',
				default: defaultData.type_paiement
			},
			{
				fieldtype: 'Currency',
				fieldname: 'montant',
				label: __('Montant'),
				default: defaultData.montant,
				precision: 2
			},
			{
				fieldtype: 'Date',
				fieldname: 'date_paiement',
				label: __('Date de Paiement'),
				default: defaultData.date_paiement
			},
			{
				fieldtype: 'Select',
				fieldname: 'methode_paiement',
				label: __('Méthode de Paiement'),
				options: 'Virement\nChèque\nEspèces\nCarte bancaire\nPrélèvement\nPayPal\nAutre',
				default: defaultData.methode_paiement
			},
			{
				fieldtype: 'Data',
				fieldname: 'reference_paiement',
				label: __('Référence de Paiement'),
				placeholder: __('Optionnel')
			}
		],
		primary_action_label: __('Créer'),
		primary_action: function(values) {
			// Créer le document directement via l'API
			frappe.call({
				method: 'frappe.client.insert',
				args: {
					doc: {
						doctype: 'Paiement Locataire',
						location_courte_duree_id: values.location_courte_duree_id,
						status: defaultData.status,
						type_paiement: values.type_paiement,
						montant: values.montant,
						date_paiement: values.date_paiement,
						methode_paiement: values.methode_paiement,
						reference_paiement: values.reference_paiement || ''
					}
				},
				callback: function(r) {
					if (r.message) {
						frappe.msgprint({
							title: __('Succès'),
							message: __('Paiement Locataire créé avec succès'),
							indicator: 'green'
						});
						// Rafraîchir la liste des paiements si nécessaire
						// Utiliser la référence frm capturée dans la closure
						if (frm && frm.refresh) {
							frm.refresh();
						}
					}
				},
				error: function(err) {
					frappe.msgprint({
						title: __('Erreur'),
						message: __('Erreur lors de la création du paiement'),
						indicator: 'red'
					});
				}
			});
			dialog.hide();
		}
	});
	
	dialog.show();
}

// Fonction pour créer un paiement propriétaire
function create_paiement_proprietaire(frm) {
	// Récupérer les informations de l'appartement pour obtenir le propriétaire
	if (frm.doc.appartement_id) {
		frappe.call({
			method: 'frappe.client.get',
			args: {
				doctype: 'Appartement',
				name: frm.doc.appartement_id
			},
			callback: function(r) {
				if (r.message) {
					const appartement = r.message;
					
					// Créer le prompt avec les valeurs par défaut
					const defaultData = {
						location_courte_duree_id: frm.doc.name,
						appartement: frm.doc.appartement_id,
						proprietaire: appartement.proprietaire_id,
						status: 'Nouveau',
						type_paiement: 'Séjour court',
						montant: frm.doc.montant_total_proprietaire || 0,
						date_paiement: frappe.datetime.get_today(),
						methode_paiement: 'Virement bancaire'
					};
					
					show_proprietaire_prompt(defaultData, frm);
				} else {
					frappe.msgprint({
						title: 'Erreur',
						message: 'Impossible de récupérer les informations de l\'appartement.',
						indicator: 'red'
					});
				}
			}
		});
	} else {
		// Créer le prompt sans les champs appartement/propriétaire si pas d'appartement
		const defaultData = {
			location_courte_duree_id: frm.doc.name,
			status: 'Nouveau',
			type_paiement: 'Séjour court',
			montant: frm.doc.montant_total_proprietaire || 0,
			date_paiement: frappe.datetime.get_today(),
			methode_paiement: 'Virement bancaire'
		};
		
		show_proprietaire_prompt(defaultData, frm);
	}
}

// Fonction pour afficher le prompt propriétaire
function show_proprietaire_prompt(defaultData, frm) {
	const fields = [
		{
			fieldtype: 'Link',
			fieldname: 'location_courte_duree_id',
			label: __('Location Courte Durée'),
			options: 'Location Courte Duree',
			default: defaultData.location_courte_duree_id,
			read_only: 1
		}
	];
	
	// Ajouter les champs appartement et propriétaire si disponibles
	if (defaultData.appartement) {
		fields.push(
			{
				fieldtype: 'Link',
				fieldname: 'appartement',
				label: __('Appartement'),
				options: 'Appartement',
				default: defaultData.appartement,
				read_only: 1
			},
			{
				fieldtype: 'Link',
				fieldname: 'proprietaire',
				label: __('Propriétaire'),
				options: 'Proprietaire',
				default: defaultData.proprietaire,
				read_only: 1
			}
		);
	}
	
	// Ajouter les autres champs
	fields.push(
		{
			fieldtype: 'Select',
			fieldname: 'type_paiement',
			label: __('Type de Paiement'),
			options: 'Séjour court\nLoyer mensuel\nDépôt de garantie\nCharges\nAutre',
			default: defaultData.type_paiement
		},
		{
			fieldtype: 'Currency',
			fieldname: 'montant',
			label: __('Montant'),
			default: defaultData.montant,
			precision: 2
		},
		{
			fieldtype: 'Date',
			fieldname: 'date_paiement',
			label: __('Date de Paiement'),
			default: defaultData.date_paiement
		},
		{
			fieldtype: 'Select',
			fieldname: 'methode_paiement',
			label: __('Méthode de Paiement'),
			options: 'Virement bancaire\nEspèces\nChèque\nAutre',
			default: defaultData.methode_paiement
		},
		{
			fieldtype: 'Data',
			fieldname: 'reference_paiement',
			label: __('Référence de Paiement'),
			placeholder: __('Optionnel')
		}
	);
	
	const dialog = new frappe.ui.Dialog({
		title: __('Créer un Paiement Propriétaire'),
		fields: fields,
		primary_action_label: __('Créer'),
		primary_action: function(values) {
			// Créer le document directement via l'API
			const docData = {
				doctype: 'Paiement Proprietaire',
				location_courte_duree_id: values.location_courte_duree_id,
				status: defaultData.status,
				type_paiement: values.type_paiement,
				montant: values.montant,
				date_paiement: values.date_paiement,
				methode_paiement: values.methode_paiement,
				reference_paiement: values.reference_paiement || ''
			};
			
			// Ajouter les champs si disponibles
			if (values.appartement) {
				docData.appartement = values.appartement;
			}
			if (values.proprietaire) {
				docData.proprietaire = values.proprietaire;
			}
			
			frappe.call({
				method: 'frappe.client.insert',
				args: {
					doc: docData
				},
				callback: function(r) {
					if (r.message) {
						frappe.msgprint({
							title: __('Succès'),
							message: __('Paiement Propriétaire créé avec succès'),
							indicator: 'green'
						});
						// Rafraîchir la liste des paiements si nécessaire
						// Utiliser la référence frm capturée dans la closure
						if (frm && frm.refresh) {
							frm.refresh();
						}
					}
				},
				error: function(err) {
					frappe.msgprint({
						title: __('Erreur'),
						message: __('Erreur lors de la création du paiement'),
						indicator: 'red'
					});
				}
			});
			dialog.hide();
		}
	});
	
	dialog.show();
}

// Fonction pour rafraîchir le statut des paiements
function refresh_payment_status(frm) {
	frappe.call({
		method: 'immo.immo.doctype.location_courte_duree.location_courte_duree.refresh_payment_status',
		args: {
			docname: frm.doc.name
		},
		callback: function(r) {
			if (r.message) {
				// Mettre à jour les champs du formulaire
				frm.set_value('montant_paye_locataire', r.message.montant_paye_locataire);
				frm.set_value('montant_restant_locataire', r.message.montant_restant_locataire);
				frm.set_value('statut_paiement_locataire', r.message.statut_paiement_locataire);
				frm.set_value('montant_paye_proprietaire', r.message.montant_paye_proprietaire);
				frm.set_value('montant_restant_proprietaire', r.message.montant_restant_proprietaire);
				frm.set_value('statut_paiement_proprietaire', r.message.statut_paiement_proprietaire);
				
				frappe.msgprint({
					title: __('Succès'),
					message: __('Statut des paiements mis à jour'),
					indicator: 'green'
				});
			}
		},
		error: function(err) {
			frappe.msgprint({
				title: __('Erreur'),
				message: __('Erreur lors de la mise à jour du statut des paiements'),
				indicator: 'red'
			});
		}
	});
}
