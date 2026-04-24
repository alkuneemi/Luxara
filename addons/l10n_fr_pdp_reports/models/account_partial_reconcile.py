from odoo import api, fields, models

from odoo.addons.l10n_fr_pdp_reports.models.pdp_flow import FLOW_SENT_STATES


class AccountPartialReconcile(models.Model):
    _inherit = 'account.partial.reconcile'
    l10n_fr_pdp_flow_id = fields.Many2one(
        comodel_name='l10n.fr.pdp.reports.flow',
        string="PDP Flow",
    )

    # @api.ondelete(at_uninstall=False)
    # def _l10n_fr_pdp_ondelete_account_partial_reconcile(self):
    #     self.l10n_fr_pdp_flow_id._create_rectificative_flow_if_needed()
