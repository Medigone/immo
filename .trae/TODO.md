# TODO:

- [x] create_child_paiement_locataire: Create child table version of Paiement Locataire doctype with istable=1 and parent fields (priority: High)
- [x] create_child_paiement_proprietaire: Create child table version of Paiement Proprietaire doctype with istable=1 and parent fields (priority: High)
- [x] update_mensualite_table_fields: Update Mensualite doctype table field options to reference the new child table doctypes (priority: High)
- [x] create_commission_item_child: Create Commission Item child table doctype with istable=1 and parent fields (priority: High)
- [x] update_referent_table_field: Update Referent doctype commissions_tab field to reference Commission Item instead of Commission (priority: High)
- [x] test_migration: Test the fix by running bench migrate and checking if the error is resolved (priority: Medium)
- [ ] migrate_referent_fix: Run bench migrate to apply the Commission Item fix (**IN PROGRESS**) (priority: Medium)
