from odoo import models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _get_sms_receipt_template(self, from_self_order=False):
        return self.config_id.sms_receipt_template_id

    def action_sent_message_on_sms(self, phone, from_self_order=False):
        receipt_template = self._get_sms_receipt_template(from_self_order=from_self_order)
        if (not from_self_order and not self.config_id.module_pos_sms) or not (self and receipt_template and phone):
            return
        self.ensure_one()
        sms_composer = self.env['sms.composer'].with_context(active_id=self.id).create(
            {
                'composition_mode': 'comment',
                'numbers': phone,
                'recipient_single_number_itf': phone,
                'template_id': receipt_template.id,
                'res_model': 'pos.order'
            }
        )
        self.mobile = phone
        sms_composer.action_send_sms()
