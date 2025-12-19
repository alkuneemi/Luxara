from odoo import fields, models
from odoo.exceptions import ValidationError

from odoo.addons.l10n_fr_pdp.tools.demo_utils import handle_demo


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_fr_pdp_send_to_ppf = fields.Boolean(
        related='company_id.l10n_fr_pdp_send_to_ppf', readonly=False,
        string="Send to PPF",
        help="Activate Flux 1 regulatory data, Flux 6 mandatory statuses and Flux 10 e-reporting generation for this company.",
    )

    def action_open_pdp_form(self):
        registration_wizard = self.env['pdp.registration'].create({'company_id': self.company_id.id})
        return registration_wizard._action_open_pdp_form(reopen=False)

    def action_open_peppol_form(self):
        self.ensure_one()
        if self.country_code != 'FR' and self.account_peppol_eas != '0225':
            return super().action_open_peppol_form()
        return self.action_open_pdp_form()

    @handle_demo
    def button_update_peppol_user_data(self):
        """Override `account_peppol` to unrequire the phone number"""
        self.ensure_one()

        if self._get_peppol_proxy_type() != 'pdp':
            return super().button_update_peppol_user_data()

        if not self.account_peppol_contact_email:
            raise ValidationError(self.env._("The contact email is required."))

        params = {
            'update_data': {
                'peppol_contact_email': self.account_peppol_contact_email,
            }
        }

        self.account_peppol_edi_user._call_peppol_proxy(
            endpoint=self.account_peppol_edi_user._get_peppol_proxy_endpoint('update_user'),
            params=params,
        )
        return True
