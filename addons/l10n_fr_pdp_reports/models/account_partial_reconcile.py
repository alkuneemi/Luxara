from odoo import api, fields, models

from odoo.addons.l10n_fr_pdp_reports.models.pdp_flow import FLOW_SENT_STATES


class AccountPartialReconcile(models.Model):
    _inherit = 'account.partial.reconcile'

    @api.ondelete(at_uninstall=False)
    def _l10n_fr_pdp_ondelete_create_unreconcile_events(self):
        event_vals_by_key = {}
        event_date = fields.Date.context_today(self)
        for partial in set(self):
            for vals in partial._l10n_fr_pdp_prepare_unreconcile_events(event_date):
                key = (vals['source_partial_id'], vals['move_id'])
                event_vals_by_key[key] = vals
        if event_vals_by_key:
            self.env['l10n.fr.pdp.reports.payment.event'].sudo().create(list(event_vals_by_key.values()))

    def _l10n_fr_pdp_prepare_unreconcile_events(self, event_date):
        self.ensure_one()
        event_vals = []
        pairings = (
            (self.debit_move_id, self.credit_move_id, self.debit_amount_currency),
            (self.credit_move_id, self.debit_move_id, self.credit_amount_currency),
        )
        for invoice_line, payment_line, partial_amount_currency in pairings:
            invoice = invoice_line.move_id
            if not invoice.is_sale_document(include_receipts=True):
                continue
            if invoice.state != 'posted':
                continue
            if not invoice.company_id.l10n_fr_pdp_send_to_ppf or invoice.company_id.country_code != 'FR':
                continue
            if not invoice._get_l10n_fr_pdp_transaction_type():
                continue
            if not (payment_line.move_id.origin_payment_id or payment_line.move_id.statement_line_id):
                continue
            if not invoice.l10n_fr_pdp_flow_ids.filtered(lambda f: f.report_type == 'payment' and f.state in FLOW_SENT_STATES):
                continue
            signed_amount = self._l10n_fr_pdp_compute_signed_payment_amount(
                invoice=invoice,
                payment_line=payment_line,
                partial_amount_currency=partial_amount_currency,
            )
            if not signed_amount:
                continue
            event_vals.append({
                'move_id': invoice.id,
                'company_id': invoice.company_id.id,
                'currency_id': (invoice.currency_id or invoice.company_id.currency_id).id,
                'payment_move_id': payment_line.move_id.id,
                'source_partial_id': self.id,
                'event_date': event_date,
                # Unreconcile must generate the opposite payment sign in the next flow.
                'amount': -signed_amount,
            })
        return event_vals

    @staticmethod
    def _l10n_fr_pdp_compute_signed_payment_amount(invoice, payment_line, partial_amount_currency):
        flow_currency = invoice.currency_id or invoice.company_id.currency_id
        move_currency = invoice.currency_id
        amount = partial_amount_currency
        if payment_line.currency_id and flow_currency and payment_line.currency_id == flow_currency:
            amount = abs(payment_line.amount_currency)
        if move_currency and flow_currency and move_currency != flow_currency:
            amount = abs(
                payment_line.balance
                if flow_currency == invoice.company_id.currency_id
                else payment_line.amount_currency
            )
        if amount and payment_line.balance > 0 and amount > 0:
            amount = -amount
        return amount
