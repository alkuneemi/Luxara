# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _get_sms_receipt_template(self, from_self_order=False):
        if from_self_order:
            return self.preset_id.sms_receipt_template_id
        return super()._get_sms_receipt_template(from_self_order=from_self_order)
