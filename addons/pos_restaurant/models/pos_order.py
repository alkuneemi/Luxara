# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

class PosOrder(models.Model):
    _inherit = 'pos.order'

    table_id = fields.Many2one('restaurant.table', string='Table', help='The table where this order was served', index='btree_not_null', readonly=True)
    customer_count = fields.Integer(string='Guests', help='The amount of customers that have been served by this order.', readonly=True)
    course_ids = fields.One2many('restaurant.order.course', 'order_id', string="Courses")
    duration = fields.Char(string='Table Duration', compute='_compute_duration', store=True)

    @api.depends('state')
    def _compute_duration(self):
        now = fields.Datetime.now()
        for order in self:
            if not order.table_id:
                order.duration = False
                continue

            start = order.create_date
            end = now if order.state == "draft" else order.date_order
            mins = abs(int((end - start).total_seconds() // 60))
            h, m = divmod(mins, 60)
            if h and m:
                order.duration = f"{h}h{m}'"
            elif h:
                order.duration = f"{h}h"
            else:
                order.duration = f"{m}'"

    def _get_open_order(self, order):
        config_id = self.env['pos.session'].browse(order.get('session_id')).config_id
        if not config_id.module_pos_restaurant:
            return super()._get_open_order(order)

        domain = []
        if order.get('table_id', False) and order.get('state') == 'draft':
            domain += ['|', ('uuid', '=', order.get('uuid')), '&', ('table_id', '=', order.get('table_id')), ('state', '=', 'draft')]
        else:
            domain += [('uuid', '=', order.get('uuid'))]
        return self.env["pos.order"].search(domain, limit=1, order='id desc')

    def read_pos_data(self, data, config):
        result = super().read_pos_data(data, config)
        result['restaurant.order.course'] = self.env['restaurant.order.course']._load_pos_data_read(self.course_ids, config)
        return result
