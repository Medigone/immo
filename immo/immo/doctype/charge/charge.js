// Copyright (c) 2025, IntraPro and contributors
// For license information, please see license.txt

frappe.ui.form.on('Charge', {
	refresh: function(frm) {
		// Masquer/afficher les champs de répartition selon le responsable
		toggle_repartition_fields(frm);
	},
	
	responsable_paiement: function(frm) {
		// Mettre à jour les champs de répartition quand le responsable change
		update_repartition_values(frm);
		toggle_repartition_fields(frm);
	},
	
	montant: function(frm) {
		// Recalculer les montants quand le montant principal change
		if (frm.doc.montant) {
			calculate_amounts(frm);
		}
	},
	
	repartition_locataire: function(frm) {
		// Ajuster automatiquement la répartition propriétaire
		if (frm.doc.responsable_paiement === 'Partagé' && frm.doc.repartition_locataire !== undefined) {
			frm.set_value('repartition_proprietaire', 100 - (frm.doc.repartition_locataire || 0));
			calculate_amounts(frm);
		}
	},
	
	repartition_proprietaire: function(frm) {
		// Ajuster automatiquement la répartition locataire
		if (frm.doc.responsable_paiement === 'Partagé' && frm.doc.repartition_proprietaire !== undefined) {
			frm.set_value('repartition_locataire', 100 - (frm.doc.repartition_proprietaire || 0));
			calculate_amounts(frm);
		}
	}
});

function toggle_repartition_fields(frm) {
	/**
	 * Masque ou affiche les champs de répartition selon le responsable de paiement
	 */
	const responsable = frm.doc.responsable_paiement;
	const show_repartition = responsable === 'Partagé';
	
	// Masquer/afficher les champs de répartition
	frm.toggle_display('repartition_locataire', show_repartition);
	frm.toggle_display('repartition_proprietaire', show_repartition);
	
	// Rendre les champs obligatoires seulement pour les charges partagées
	frm.toggle_reqd('repartition_locataire', show_repartition);
	frm.toggle_reqd('repartition_proprietaire', show_repartition);
	
	// Toujours afficher les montants calculés
	frm.toggle_display('montant_locataire', true);
	frm.toggle_display('montant_proprietaire', true);
}

function update_repartition_values(frm) {
	/**
	 * Met à jour les valeurs de répartition selon le responsable de paiement
	 */
	const responsable = frm.doc.responsable_paiement;
	
	switch (responsable) {
		case 'Agent immobilier':
			frm.set_value('repartition_locataire', 0);
			frm.set_value('repartition_proprietaire', 0);
			break;
		case 'Locataire':
			frm.set_value('repartition_locataire', 100);
			frm.set_value('repartition_proprietaire', 0);
			break;
		case 'Propriétaire':
			frm.set_value('repartition_locataire', 0);
			frm.set_value('repartition_proprietaire', 100);
			break;
		case 'Partagé':
			// Garder les valeurs existantes ou utiliser les valeurs par défaut
			if (!frm.doc.repartition_locataire && !frm.doc.repartition_proprietaire) {
				frm.set_value('repartition_locataire', 0);
				frm.set_value('repartition_proprietaire', 100);
			}
			break;
	}
	
	// Recalculer les montants après mise à jour des répartitions
	calculate_amounts(frm);
}

function calculate_amounts(frm) {
	/**
	 * Calcule les montants pour le locataire et le propriétaire
	 */
	if (frm.doc.montant) {
		const montant = parseFloat(frm.doc.montant) || 0;
		const repartition_locataire = parseFloat(frm.doc.repartition_locataire) || 0;
		const repartition_proprietaire = parseFloat(frm.doc.repartition_proprietaire) || 0;
		
		const montant_locataire = (montant * repartition_locataire) / 100;
		const montant_proprietaire = (montant * repartition_proprietaire) / 100;
		
		frm.set_value('montant_locataire', montant_locataire);
		frm.set_value('montant_proprietaire', montant_proprietaire);
	}
}

// Validation côté client pour les charges partagées
frappe.ui.form.on('Charge', {
	validate: function(frm) {
		if (frm.doc.responsable_paiement === 'Partagé') {
			const total = (parseFloat(frm.doc.repartition_locataire) || 0) + 
						  (parseFloat(frm.doc.repartition_proprietaire) || 0);
			
			if (Math.abs(total - 100) > 0.01) {
				frappe.msgprint({
					title: __('Erreur de répartition'),
					message: __('La somme des répartitions doit être égale à 100%'),
					indicator: 'red'
				});
				frappe.validated = false;
			}
		}
	}
});
