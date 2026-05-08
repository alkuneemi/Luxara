from odoo import http
from odoo.http import request


class PosCustomerDisplay(http.Controller):
    @http.route("/pos_customer_display/<id_>/<identifier>", auth="public", type="http", website=True)
    def pos_customer_display(self, id_, identifier, **kw):
        pos_config_sudo = request.env["pos.config"].sudo().browse(int(id_))
        return request.render(
            "point_of_sale.customer_display_index",
            {
                "session_info": {
                    "user_context": {
                      "lang":  request.env.user.lang or pos_config_sudo.company_id.partner_id.lang
                    },
                    **request.env["ir.http"].get_frontend_session_info(),
                    **pos_config_sudo._get_customer_display_data(),
                    'identifier': identifier,
                },
            },
        )

    @http.route('/pos_webrtc_signaling', auth='public', type='jsonrpc')
    def pos_webrtc_signaling(self, pos_config_id, payload, identifier=0):
        pos_config_sudo = request.env['pos.config'].sudo().browse(int(pos_config_id)).exists()
        if pos_config_sudo:
            pos_config_sudo._notify(f'POS_WEBRTC_SIGNALING-{identifier}', payload)
