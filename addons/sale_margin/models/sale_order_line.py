# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    margin = fields.Float(
        "Margin",
        compute="_compute_margin",
        min_display_digits="Product Price",
        readonly=False,
        store=True,
        groups="base.group_user",
        copy=False,
        precompute=True,
    )
    margin_percent = fields.Float(
        "Margin (%)",
        compute="_compute_margin",
        readonly=False,
        store=True,
        groups="base.group_user",
        copy=False,
        precompute=True,
    )
    purchase_price = fields.Float(
        string="Unit Cost",
        compute="_compute_purchase_price",
        min_display_digits="Product Price",
        store=True,
        readonly=False,
        copy=False,
        precompute=True,
        groups="base.group_user",
    )

    @api.depends("product_id", "company_id", "currency_id", "product_uom_id")
    def _compute_purchase_price(self):
        for line in self:
            if not line.product_id:
                line.purchase_price = 0.0
                continue
            line = line.with_company(line.company_id)

            # Convert the cost to the line UoM
            product_cost = line.product_id.uom_id._compute_price(
                line.product_id.standard_price, line.product_uom_id
            )

            line.purchase_price = line._convert_to_sol_currency(
                product_cost, line.product_id.cost_currency_id
            )

    @api.depends("price_subtotal", "product_uom_qty", "purchase_price")
    def _compute_margin(self):
        for line in self:
            # Find alternative calculation when line is added to order from delivery
            if line.qty_delivered and not line.product_uom_qty:
                calculated_subtotal = line.price_unit * line.qty_delivered
                line.margin = calculated_subtotal - (line.purchase_price * line.qty_delivered)
                line.margin_percent = calculated_subtotal and line.margin / calculated_subtotal
            else:
                line.margin = line.price_subtotal - (line.purchase_price * line.product_uom_qty)
                line.margin_percent = line.price_subtotal and line.margin / line.price_subtotal

    @api.onchange("margin")
    def _onchange_margin(self):
        for line in self:
            if line.qty_delivered and not line.product_uom_qty:
                computed_price = line.margin / line.qty_delivered + line.purchase_price
            elif line.product_uom_qty:
                computed_price = line.margin / line.product_uom_qty + line.purchase_price
            if computed_price:
                line._set_price_based_on_tax(computed_price)
            line.margin_percent = line.price_unit and 1 - line.purchase_price / line.price_unit

    @api.onchange("margin_percent")
    def _onchange_margin_percent(self):
        for line in self:
            if line.margin_percent == 1 and line.purchase_price != 0:
                raise UserError(
                    self.env._("If the cost is not 0, it is not possible to set the margin to 100%")
                )
            discount = (1 - line.discount / 100) if line.discount else 1
            if line.purchase_price != 0:
                computed_price = (line.purchase_price) / (1 - line.margin_percent) / discount
                line._set_price_based_on_tax(computed_price)
            line_difference = line.price_unit - line.purchase_price
            if line.qty_delivered and not line.product_uom_qty:
                line.margin = line_difference * line.qty_delivered
            else:
                line.margin = line_difference * line.product_uom_qty

    def _set_price_based_on_tax(self, price):
        """Update the line price based on tax configuration.
        If any tax on the line is price-included, update `price_total`.
        Otherwise, update `price_unit`.

        :param float price: The price value to assign.
        """
        if any(self.tax_ids.filtered(lambda tax: tax.price_include)):
            self.price_total = price
        else:
            self.price_unit = price
