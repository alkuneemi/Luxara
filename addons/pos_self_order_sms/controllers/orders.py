# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http

from odoo.addons.pos_self_order.controllers.orders import PosSelfOrderController


class PosSelfOrderSMSController(PosSelfOrderController):
    @http.route()
    def pos_self_order_send_order_receipt(self, access_token, order_id):
        result = super().pos_self_order_send_order_receipt(access_token, order_id)
        if result:
            pos_config = self._verify_pos_config(access_token)
            order = pos_config.env['pos.order'].browse(order_id)
            if order.preset_id.sms_receipt_template_id:
                order.sudo().action_sent_message_on_sms(order.mobile, from_self_order=True)
        return result
