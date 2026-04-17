# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    # === BUSINESS METHODS === #

    def _get_pending_msg(self, *, from_website=False, **kwargs):
        """Override to return a specific pending message for website orders."""
        if from_website and self.custom_mode in self._get_custom_bank_related_modes():
            return self.env._("Your order will be confirmed after payment is received.")

        return super()._get_pending_msg(from_website=from_website, **kwargs)
