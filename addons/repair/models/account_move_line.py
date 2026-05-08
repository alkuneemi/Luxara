from odoo import fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    repair_order_id = fields.Many2one('repair.order', string='Repair Order', index='btree_not_null', copy=False)
    repair_service_line_id = fields.Many2one('repair.service.line', check_company=True, copy=False)
    stock_move_id = fields.Many2one('stock.move', index='btree_not_null')
