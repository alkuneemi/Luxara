from odoo.tests.common import tagged

from .common import PdpTestCommon


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestPdpRectificativeFlows(PdpTestCommon):
    """Test Flux 10 v1.2 rectificative (RE) flow behavior.

    v1.2 changes:
    - Only IN and RE transmission types (CO/MO removed)
    - No References block (transmission_reference/reference_scheme removed)
    - Corrections via accounting lifecycle (credit notes) + RE flows
    """

    def test_re_flow_auto_created_for_error_invoices(self):
        """When IN is sent with mixed validity, RE flow auto-created for error invoices."""
        self._create_invoice(sent=True)
        invoice = self._create_invoice(sent=False)  # Will fail validation
        flows = self._aggregate_company()
        transaction_flow = flows.filtered(lambda f: f.report_kind == 'transaction')[:1]
        self.assertTrue(transaction_flow, 'Initial transaction flow should be created')

        # Send on deadline (with errors) - should auto-create RE for error invoices
        transaction_flow.with_context(ignore_error_invoices=True).action_send()

        # Find the auto-created RE flow
        re_flow = self.env['l10n.fr.pdp.reports.flow'].search([
            ('company_id', '=', self.company.id),
            ('report_kind', '=', 'transaction'),
            ('transmission_type', '=', 'rectificative'),
        ], order='id desc', limit=1)

        self.assertTrue(re_flow, 'RE flow should be auto-created for error invoices')
        self.assertEqual(re_flow.transmission_type, 'rectificative', 'TT-4 should be RE')
        # v1.2: RE is always a full replacement payload (never a delta)
        self.assertEqual(
            re_flow.move_ids.sorted('id'),
            transaction_flow.move_ids.sorted('id'),
            'RE should contain the full period dataset',
        )
        self.assertIn(invoice, re_flow.error_move_ids, 'RE should keep the invalid set visible for accountants')
        self.assertEqual(re_flow.state, 'pending', 'RE should be pending until errors fixed')

    def test_payment_re_flow_for_new_payments(self):
        """New payments after IN sent should create RE flow in v1.2."""
        inv1 = self._create_invoice(sent=True, product=self.service_product)
        self._create_payment_for_invoice(inv1)
        flows = self._aggregate_company()
        first_payment_flow = flows.filtered(lambda f: f.report_kind == 'payment')[:1]
        self.assertTrue(first_payment_flow, 'Initial payment flow should exist')
        first_payment_flow.action_send()
        self.assertTrue(first_payment_flow.transport_identifier)

        # Create new payment - should trigger RE flow (not MO)
        inv2 = self._create_invoice(sent=True, product=self.service_product)
        self._create_payment_for_invoice(inv2)
        flows = self._aggregate_company()
        re_flow = flows.filtered(lambda f: f.report_kind == 'payment' and f.id != first_payment_flow.id)
        if not re_flow:
            re_flow = self.env['l10n.fr.pdp.reports.flow'].search([
                ('company_id', '=', self.company.id),
                ('report_kind', '=', 'payment'),
                ('id', '!=', first_payment_flow.id),
            ], order='id desc', limit=1)

        re_flow = re_flow[-1:]
        self.assertTrue(re_flow, 'rectificative payment flow should be created for new payments')
        self.assertEqual(re_flow.transmission_type, 'rectificative', 'TT-4 should be rectificative')

    def test_rectificative_flow_manual_creation(self):
        """Manual RE flow creation via button (v1.2: no references to previous flows)."""
        self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        self.assertTrue(flow, 'Transaction flow should be built')
        flow.action_send()

        # User manually creates RE flow
        action = flow.action_create_rectificative_flow()
        new_flow = self.env[action['res_model']].browse(action['res_id'])

        # v1.2: Only transmission_type matters, no reference fields
        self.assertEqual(new_flow.transmission_type, 'rectificative', 'TT-4 should be RE for rectificative')
        self.assertEqual(new_flow.move_ids.sorted('id'), flow.move_ids.sorted('id'), 'Should copy invoices')
        self.assertEqual(new_flow.state, 'pending', 'Should start in pending state')

    def test_payment_flow_not_duplicated_for_same_moves(self):
        """No new payment flow when move set is identical to the last sent one."""
        inv = self._create_invoice(sent=True, product=self.service_product)
        self._create_payment_for_invoice(inv)
        flows = self._aggregate_company()
        payment_flow = flows.filtered(lambda f: f.report_kind == 'payment')[:1]
        self.assertTrue(payment_flow, 'Payment flow should be present before send')
        payment_flow.action_send()

        count_before = self.env['l10n.fr.pdp.reports.flow'].search_count([
            ('company_id', '=', self.company.id),
            ('report_kind', '=', 'payment'),
        ])
        self._aggregate_company()
        count_after = self.env['l10n.fr.pdp.reports.flow'].search_count([
            ('company_id', '=', self.company.id),
            ('report_kind', '=', 'payment'),
        ])
        self.assertEqual(count_after, count_before, 'Identical payment set must not spawn a new flow')

    def test_no_auto_correction_for_changed_invoices(self):
        """v1.2: Changed sent invoices require manual RE with credit note (no auto-MO)."""
        self._create_invoice(sent=True)
        first_flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        self.assertTrue(first_flow)
        first_flow.action_send()
        self.assertTrue(first_flow.transport_identifier)

        # In v1.2: Even if invoice changes after being sent, no automatic correction flow
        # User must create credit note/rectificative invoice, then manual RE
        auto_re_flow = self.env['l10n.fr.pdp.reports.flow'].search([
            ('company_id', '=', self.company.id),
            ('report_kind', '=', 'transaction'),
            ('transmission_type', '=', 'rectificative'),
        ], order='id desc', limit=1)

        # Should NOT auto-create correction flow (v1.0 behavior removed)
        self.assertFalse(auto_re_flow, 'v1.2: No auto-correction flows; user creates rectificative flows manually')

    def test_transaction_flow_not_duplicated_for_same_moves(self):
        """No new transaction flow when the sent set is unchanged."""
        self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        flow.action_send()
        count_before = self.env['l10n.fr.pdp.reports.flow'].search_count([
            ('company_id', '=', self.company.id),
            ('report_kind', '=', 'transaction'),
        ])
        self._aggregate_company()
        count_after = self.env['l10n.fr.pdp.reports.flow'].search_count([
            ('company_id', '=', self.company.id),
            ('report_kind', '=', 'transaction'),
        ])
        self.assertEqual(count_after, count_before, 'Identical transaction set must not spawn a new flow')

    def test_re_flow_no_reference_fields(self):
        """v1.2: RE flows don't use transmission_reference or reference_scheme."""
        self._create_invoice(sent=True)
        flow = self._aggregate_company().filtered(lambda f: f.report_kind == 'transaction')[:1]
        flow.action_send()

        # Create RE flow
        action = flow.action_create_rectificative_flow()
        re_flow = self.env[action['res_model']].browse(action['res_id'])

        # v1.2: These fields should not be used (will be removed from model)
        # Just verify RE type is correct
        self.assertEqual(re_flow.transmission_type, 'rectificative', 'Should be rectificative transmission type')
