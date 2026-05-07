# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _action_done(self, cancel_backorder=False):
        """Sync website publish state after stock moves are confirmed.

        Templates are captured before super() because _action_done returns
        backorder moves, not the moves that were actually confirmed.
        """
        templates = self.product_id.product_tmpl_id
        res = super()._action_done(cancel_backorder=cancel_backorder)
        if templates:
            self.env["stock.quant"].flush_model()
            self.env["product.product"].invalidate_model(["free_qty", "qty_available"])
            templates._sync_website_published_state()
        return res
