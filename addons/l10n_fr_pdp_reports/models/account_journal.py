from odoo import _, fields, models
from odoo.tools.misc import format_date
from odoo.addons.l10n_fr_pdp_reports.models.pdp_flow import FLOW_OPEN_STATES


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _get_journal_dashboard_data_batched(self):
        dashboard_data = super()._get_journal_dashboard_data_batched()

        # Filter journals for PDP-enabled companies
        pdp_enabled_journals = self.filtered(
            lambda j: (j.type == 'sale' and j.company_id.l10n_fr_f10_enable_reporting)
        )
        if not pdp_enabled_journals:
            return dashboard_data

        def _get_due(company, report_type):
            flow = self.env['l10n.fr.pdp.reports.flow'].search(
                [
                    ('company_id', '=', company.id),
                    ('report_type', '=', report_type),
                    ('state', 'in', FLOW_OPEN_STATES),
                ],
                limit=1,
                order='due_date asc',
            )
            if not flow:
                return False, False, False
            has_errors = flow.state == 'error' or bool(flow.error_move_ids)
            return flow.due_date, format_date(self.env, flow.due_date), has_errors

        # Compute PDP data per company
        for company, journals in pdp_enabled_journals.grouped('company_id').items():

            # Next due dates
            transaction_due_raw, transaction_due_str, transaction_has_errors = _get_due(company, 'transaction')
            payment_due_raw, payment_due_str, payment_has_errors = _get_due(company, 'payment')

            # Errors
            error_count = self.env['account.move'].search_count([
                ('company_id', '=', company.id),
                ('l10n_fr_pdp_status', '=', 'error'),
            ])

            if error_count:
                has_warning = True
                deadlines = [d for d in (transaction_due_raw, payment_due_raw) if d]
                has_danger = deadlines and (min(deadlines) - fields.Date.context_today(self)).days <= 3
            else:
                has_warning = False
                has_danger = False

            # Apply data to all journals in this company
            for journal in journals:
                data = dashboard_data[journal.id]

                # EREP (e-reporting) journal has more data
                if journal.code == 'EREP':
                    data['pdp_is_ereporting_journal'] = True
                    data['pdp_transaction_due'] = transaction_due_str
                    data['pdp_payment_due'] = payment_due_str
                    data['pdp_transaction_has_errors'] = transaction_has_errors
                    data['pdp_payment_has_errors'] = payment_has_errors

                # Add error info to ALL sale journals
                data['pdp_error_count'] = error_count
                data['pdp_has_warning'] = has_warning
                data['pdp_has_danger'] = has_danger

        return dashboard_data

    def _action_open_next_flow(self, report_type):
        """Open the next flow with upcoming due date for given report kind."""
        self.ensure_one()
        flow = self.env['l10n.fr.pdp.reports.flow'].search(
            [
                ('company_id', '=', self.company_id.id),
                ('report_type', '=', report_type),
                ('state', 'in', FLOW_OPEN_STATES),
            ],
            limit=1,
            order='due_date asc',
        )
        if flow:
            return flow._get_records_action()
        return False

    def action_open_next_transaction_flow(self):
        """Open the next transaction flow with upcoming due date."""
        return self._action_open_next_flow('transaction')

    def action_open_next_payment_flow(self):
        """Open the next payment flow with upcoming due date."""
        return self._action_open_next_flow('payment')

    def action_open_pdp_error_moves(self):
        """Open in-scope accounting documents currently in PDP error for this company."""
        self.ensure_one()
        return self._get_records_action(
            name=_("E-Reporting Error Documents"),
            domain=[
                ('company_id', '=', self.company_id.id),
                ('l10n_fr_pdp_status', '=', 'error'),
            ],
            context={'search_default_group_by_move_type': 1},
            res_model='account.move',
        )
