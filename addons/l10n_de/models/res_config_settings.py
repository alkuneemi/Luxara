from odoo import api, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    @api.depends('country_code')
    def _compute_force_restrictive_audit_trail_reason(self):
        super()._compute_force_restrictive_audit_trail_reason()
        for config in self:
            if config.country_code == 'DE':
                config.force_restrictive_audit_trail_reason = self.env._("Audit Trail is mandatory in Germany owing to GoBD compliance.")
