from odoo import api, fields, models


class RepairServiceLine(models.Model):
    _name = 'repair.service.line'
    _description = "Repair Service Line"

    description = fields.Char()
    sequence = fields.Integer('Sequence', default=0)
    product_id = fields.Many2one(
        'product.product', string='Service',
        domain="[('type', '=', 'service'), '|', ('company_id', '=', company_id), ('company_id', '=', False)]",
        check_company=True)
    repair_id = fields.Many2one('repair.order', check_company=True, index='btree_not_null', copy=False, ondelete='cascade')
    uom_id = fields.Many2one(
        'uom.uom', 'Unit', domain="[('id', 'in', allowed_uom_ids)]",
        readonly=False, required=True, compute='_compute_uom_id', store=True, copy=True, precompute=True)
    allowed_uom_ids = fields.Many2many('uom.uom', compute='_compute_allowed_uom_ids')
    quantity = fields.Float(
        'Quantity', digits='Product Unit', required=True, default=1.0)
    company_id = fields.Many2one(
        'res.company', 'Company', index=True)
    sale_line_id = fields.One2many('sale.order.line', 'repair_service_line_id', 'Sale Line', index='btree_not_null')
    invoice_line_id = fields.One2many('account.move.line', 'repair_service_line_id', string='Invoice Line', index='btree_not_null')

    @api.depends('product_id.uom_id')
    def _compute_uom_id(self):
        for line in self:
            if not line.uom_id:
                line.uom_id = line.product_id.uom_id.id

    @api.depends('product_id', 'product_id.uom_id')
    def _compute_allowed_uom_ids(self):
        for line in self:
            line.allowed_uom_ids = line.product_id._get_available_uoms()

    def create(self, vals_list):
        repair_service_line = super().create(vals_list)
        for line in repair_service_line:
            if not line.sale_line_id and line.repair_id.sale_order_id:
                line._create_repair_sale_order_line()
            if not line.invoice_line_id and line.repair_id.invoice_id:
                line._create_repair_invoice_line()
        return repair_service_line

    def write(self, vals):
        res = super().write(vals)
        if 'quantity' in vals or 'uom_id' in vals:
            for line in self:
                if not line.sale_line_id and line.repair_id.sale_order_id:
                    line._create_repair_sale_order_line()
                elif line.sale_line_id:
                    line._update_repair_sale_order_line()

                if not line.invoice_line_id and line.repair_id.invoice_id:
                    line._create_repair_invoice_line()
                elif line.invoice_line_id:
                    line._update_repair_invoice_line()
        return res

    # To be discussed
    # @api.ondelete(at_uninstall=False)
    # def _unlink_repair_service_line(self):
    #     self.filtered(
    #         lambda r: r.repair_id and r.sale_line_id
    #     ).mapped('sale_line_id').write({'product_uom_qty': 0.0})

    #     self.filtered(
    #         lambda r: r.repair_id and r.invoice_line_id
    #     ).mapped('invoice_line_id').write({'quantity': 0.0})

    def unlink(self):
        self.filtered(
            lambda r: r.repair_id and r.sale_line_id
        ).mapped('sale_line_id').write({'product_uom_qty': 0.0})

        self.filtered(
            lambda r: r.repair_id and r.invoice_line_id
        ).mapped('invoice_line_id').write({'quantity': 0.0})
        return super().unlink()

    def _update_repair_invoice_line(self):
        if self.repair_id.invoice_id.state == 'posted':
            return
        for line in self:
            line.invoice_line_id.quantity = line.quantity
            line.invoice_line_id.product_uom_id = line.uom_id

    def _update_repair_sale_order_line(self):
        for line in self:
            line.sale_line_id.product_uom_qty = line.quantity
            line.sale_line_id.product_uom_id = line.uom_id

    def _prepare_repair_service_line_common_vals(self):
        self.ensure_one()
        comman_vals = {
            'product_id': self.product_id.id,
            'product_uom_id': self.uom_id.id,
            'repair_service_line_id': self.id,
        }
        if self.repair_id.under_warranty:
            comman_vals['price_unit'] = 0.0
        return comman_vals

    def _create_repair_sale_order_line(self):
        vals_list = []

        for line in self:
            if line.sale_line_id or not line.repair_id.sale_order_id:
                continue

            vals_list.append({
                **line._prepare_repair_service_line_common_vals(),
                'order_id': line.repair_id.sale_order_id.id,
                'product_uom_qty': line.quantity,
                'qty_delivered': line.quantity if line.repair_id.state == 'done' else 0.0,
            })

        if vals_list:
            self.env['sale.order.line'].create(vals_list)

    def _create_repair_invoice_line(self):
        vals_list = []

        for line in self:
            if line.invoice_line_id or not line.repair_id.invoice_id:
                continue

            vals_list.append({
                **line._prepare_repair_service_line_common_vals(),
                'move_id': line.repair_id.invoice_id.id,
                'quantity': line.quantity,
            })

        if vals_list:
            self.env['account.move.line'].create(vals_list)

    def _set_service_qty_delivered(self):
        for line in self.sale_line_id:
            line.qty_delivered = line.product_uom_qty

    def action_add_service_from_repair_catalog(self):
        repair_order = self.env['repair.order'].browse(self.env.context.get('order_id'))
        repair_order.service_catalog = True
        return repair_order.action_add_from_catalog()

    def _get_product_catalog_lines_data(self, parent_record=False, **kwargs):
        if not (parent_record and self):
            return {
                'quantity': 0,
            }
        self.product_id.ensure_one()
        return {
            'price': self.product_id.lst_price,
            'quantity': self[0].quantity,
            'readOnly': len(self) > 1,
            **parent_record._get_product_catalog_uom_data(self.product_id, self[0].uom_id),
        }
