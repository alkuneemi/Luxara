# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from collections import defaultdict

from odoo.exceptions import AccessError, MissingError
from odoo.http import request, route
from odoo.http.stream import content_disposition

from odoo.addons.sale.controllers import portal as sale_portal


class CustomerPortal(sale_portal.CustomerPortal):

    @route(
        "/return/order/content",
        type="jsonrpc", auth="user", website=True, readonly=True
    )
    def return_order_content(self, order_id, access_token):
        """Prepare return details of order depending on deliveries.

        :param int order_id: The order for which we are preparing return content.
        :param str access_token: The access token used to authenticate the request.
        :return: A dict containing a list of returnable lines vals depending on deliveries.
        :rtype: dict.
        """
        try:
            sale_order = self._document_check_access(
                "sale.order", order_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return request.redirect('/my')

        return_data = {
            "company_name": sale_order.company_id.name,
            "warehouse_address": sale_order.warehouse_id.partner_id.address,
            "returnable_lines": [],
            "return_reasons": [{
                "id": reason.id,
                "name": reason.name,
            } for reason in request.env["return.reason"].search([])],
        }
        for line in sale_order.order_line:
            if not line._is_returnable():
                continue
            common_line_vals = {
                "name": line.product_id.with_context(display_default_code=False).display_name,
                "currency_id": line.currency_id.id,
                "description_sale": line.name,
                "price": line.price_unit,
                "product_id": line.product_id.id,
            }
            for move in line.move_ids:
                picking = move.picking_id
                if picking.picking_type_code != "outgoing" or picking.state != "done":
                    continue
                returned_qty = sum(
                    rm.quantity for rm in move.returned_move_ids if rm.state == "done"
                )
                remaining_delivered_qty = move.quantity - returned_qty
                if remaining_delivered_qty:
                    return_data["returnable_lines"].append({
                        **common_line_vals,
                        **picking._get_return_details(),
                        "delivered_qty": remaining_delivered_qty,
                        "lot_name": move.lot_ids and ", ".join(move.lot_ids.mapped("name")) or "",
                    })

        return return_data

    @route("/my/orders/<int:order_id>/download_return_label", type="http", auth="user")
    def return_order_dowload_label(
        self, order_id, access_token=False, picking_details="", return_reason=""
    ):
        """Return return pdf of picking for selected products with return reason.

        :param int order_id: The order for which we are preparing return content.
        :param str access_token: The access token used to authenticate the request.
        :param str selected_lines: Selected products in json formated string.
        :param str return_reason: Selected return reason id in string.
        :return: A pdf of picking for selected products with return reason.
        :rtype: bytes.
        """
        try:
            sale_order = self._document_check_access(
                "sale.order", int(order_id), access_token=access_token
            )
        except (AccessError, MissingError):
            return request.redirect('/my')

        picking_details = json.loads(picking_details)
        qty_by_delivery = defaultdict(dict)
        for delivery_id, products in picking_details.items():
            delivery_id = int(delivery_id)
            for product_id, qty in products:
                qty_by_delivery[delivery_id][product_id] = qty

        return_data = {
            "wh_address_id": sale_order.warehouse_id.partner_id,
            "qty_by_delivery": qty_by_delivery,
            "return_reason": self.env["return.reason"].browse(int(return_reason)),
        }
        pdf = request.env['ir.actions.report'].sudo()._render_qweb_pdf(
            "sale_stock.action_report_return_label",
            list(qty_by_delivery.keys()), data=return_data,
        )[0]

        pdfhttpheaders = [
            ("Content-Disposition", content_disposition(
                f"Return - {sale_order.name}.pdf", "inline"
            )),
            ("Content-Type", "application/pdf"),
            ("Content-Length", len(pdf)),
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)
