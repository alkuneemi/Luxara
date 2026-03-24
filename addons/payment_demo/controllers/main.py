# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request


class PaymentDemoController(http.Controller):
    _simulation_url = "/payment/demo/simulate_payment"

    @http.route(_simulation_url, type="jsonrpc", auth="public")
    def demo_simulate_payment(self, **data):
        """Simulate the response of a payment request.

        :param dict data: The simulated payment data.
        :return: None
        """
        tx_sudo = request.env["payment.transaction"].sudo()._search_by_reference("demo", data)
        tx_sudo._record(data)
