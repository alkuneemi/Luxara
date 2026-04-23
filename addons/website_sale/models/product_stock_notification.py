# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductStockNotification(models.Model):
    _name = "product.stock.notification"
    _description = "Product Stock Notification"

    product_id = fields.Many2one("product.product", required=True, ondelete="cascade", index=True)
    partner_id = fields.Many2one("res.partner", required=True, ondelete="cascade", index=True)
    website_id = fields.Many2one("website", required=True, ondelete="cascade", index=True)

    _unique_together = models.Constraint(
        "unique(product_id, partner_id, website_id)",
        "A stock notification already exists for this partner, product and website.",
    )
