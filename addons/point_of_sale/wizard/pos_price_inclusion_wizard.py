from odoo import fields, models


class PosPriceInclusionWizard(models.TransientModel):
    _name = 'pos.price.inclusion.wizard'
    _description = 'Point of Sale Price Inclusion Wizard'

    config_id = fields.Many2one('pos.config', required=True, readonly=True)

    def action_tax_included(self):
        self.ensure_one()
        self.config_id.company_id.sudo().account_price_include = 'tax_included'
        return self.config_id.open_ui()

    def action_tax_excluded(self):
        self.ensure_one()
        self.config_id.company_id.sudo().account_price_include = 'tax_excluded'
        return self.config_id.open_ui()

    def action_discard(self):
        return {"type": "ir.actions.act_window_close"}
