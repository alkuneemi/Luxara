# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockQuant(models.Model):
    _inherit = "stock.quant"

    def _apply_inventory(self, date=None):
        """Sync website publish state after manual inventory adjustments.

        Templates are captured before super() because _apply_inventory
        clears inventory_quantity on the quants as part of its work.
        """
        templates = self.mapped("product_id.product_tmpl_id")
        res = super()._apply_inventory(date=date)
        if templates:
            self.env["stock.quant"].flush_model()
            self.env["product.product"].invalidate_model(["free_qty", "qty_available"])
            templates._sync_website_published_state()
        return res
