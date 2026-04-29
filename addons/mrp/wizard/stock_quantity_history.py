from odoo import models
from odoo.fields import Domain


class StockQuantityHistory(models.TransientModel):
    _inherit = 'stock.quantity.history'

    def _get_products_domain(self):
        return super()._get_products_domain() & Domain('is_kits', '=', False)
