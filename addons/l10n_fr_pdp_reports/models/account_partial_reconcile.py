from odoo import api, fields, models

from odoo.addons.l10n_fr_pdp_reports.models.pdp_flow import FLOW_SENT_STATES


class AccountPartialReconcile(models.Model):
    _inherit = 'account.partial.reconcile'

    @api.ondelete(at_uninstall=False)
    def _l10n_fr_pdp_ondelete_account_partial_reconcile(self):
        Flow = self.env['l10n.fr.pdp.reports.flow']
        for partial in self:
            payment_move = None
            if partial.debit_move_id.l10n_fr_pdp_is_flow_10_scope:
                payment_move = partial.credit_move_id
            elif partial.credit_move_id.l10n_fr_pdp_is_flow_10_scope:
                payment_move = partial.debit_move_id
            if payment_move:
                # ensure one open flow exists where the new payment situation will be reflected
                Flow._get_open_flow_and_create_if_needed(
                    move=payment_move,
                    report_type='payment',
                )
