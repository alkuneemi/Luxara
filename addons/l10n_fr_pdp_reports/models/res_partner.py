from odoo import models
from odoo.addons.l10n_fr_pdp_reports.models.pdp_flow import FLOW_OPEN_STATES


TRACKED_PARTNER_KEYS = {'vat', 'country_id', 'property_account_position_id'}


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def write(self, vals):
        """Reset open PDP flows when partner VAT/country changes."""
        res = super().write(vals)
        if TRACKED_PARTNER_KEYS.intersection(vals):
            moves = self.env['account.move'].search([
                ('state', '=', 'posted'),
                ('move_type', 'in', self.env['account.move'].get_sale_types(include_receipts=True)),
                ('commercial_partner_id', 'in', self.commercial_partner_id.ids),
            ])
            if flows := moves.mapped('l10n_fr_pdp_flow_ids').filtered(lambda f: f.state in FLOW_OPEN_STATES):
                flows._mark_as_outdated()
        return res
