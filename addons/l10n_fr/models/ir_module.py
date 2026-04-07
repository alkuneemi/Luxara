# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrModuleModule(models.Model):
    _inherit = 'ir.module.module'

    def button_immediate_install(self):
        should_apply_worldline_branding = any(
            module.name == 'payment_worldline' and module.state != 'installed'
            for module in self
        )
        result = super().button_immediate_install()
        if should_apply_worldline_branding:
            self.env['res.company'].sudo().search([]).apply_worldline_branding()
        return result
