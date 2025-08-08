from __future__ import unicode_literals
import frappe
from frappe import _

def get_data():
	return {
		'fieldname': 'location_bloc_id',
		'non_standard_fieldnames': {
			'Paiement Bloc': 'location_bloc_id',
			'Location Courte Duree': 'location_bloc_id',
			'Paiement Locataire': 'location_bloc_id',
		},
		'transactions': [
			{
				'label': _('Paiements'),
				'items': ['Paiement Bloc']
			},
			{
				'label': _('Locations'),
				'items': ['Location Courte Duree']
			},
			{
				'label': _('Paiements Locataires'),
				'items': ['Paiement Locataire']
			}
		],
		'cards': [
			{
				'label': _('Paiements Propriétaire'),
				'data': [
					{
						'fieldname': 'montant_total_paye',
						'label': _('Total Payé'),
						'value': 'montant_total_paye',
						'type': 'Currency'
					},
					{
						'fieldname': 'solde_restant',
						'label': _('Solde Restant'),
						'value': 'solde_restant',
						'type': 'Currency'
					}
				]
			},
			{
				'label': _('Paiements Locataires'),
				'data': [
					{
						'fieldname': 'total_encaisse',
						'label': _('Total Encaissé'),
						'value': 'total_encaisse',
						'type': 'Currency'
					},
					{
						'fieldname': 'paiements_prevus',
						'label': _('Paiements Prévus'),
						'value': 'paiements_prevus',
						'type': 'Currency'
					}
				]
			}
		]
	}
