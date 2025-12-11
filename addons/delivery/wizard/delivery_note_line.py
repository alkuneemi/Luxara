# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class DeliveryNoteWizardLine(models.TransientModel):
    _name = "delivery.note.wizard.line"
    _description = "Delivery Note Line"

    note_id = fields.Many2one(string="Delivery Note Reference", comodel_name="delivery.note.wizard")
    sol_id = fields.Many2one(string="Source Sale Order Line", comodel_name="sale.order.line")
    product_id = fields.Many2one(comodel_name="product.product", related="sol_id.product_id")
    product_image = fields.Image(related="product_id.image_128")
    product_uom_id = fields.Many2one(comodel_name="uom.uom", related="sol_id.product_uom_id")
    product_uom_qty = fields.Float(
        string="Quantity", compute="_compute_product_uom_qty", store=True, readonly=False
    )

    @api.depends("sol_id.product_uom_qty", "sol_id.qty_delivered")
    def _compute_product_uom_qty(self):
        for line in self:
            line.product_uom_qty = line.sol_id.product_uom_qty - line.sol_id.qty_delivered

    def _update_sol_qty_delivered(self):
        """Update the quantity delivered of the related sale order line."""
        for line in self:
            line.sol_id.qty_delivered += line.product_uom_qty

    def _get_line_representation(self):
        self.ensure_one()
        return "%d %s %s" % (
            self.product_uom_qty,
            self.product_id.with_context(display_default_code=False).display_name,
            self.product_uom_id.name
            if self.env["res.groups"]._is_feature_enabled("uom.group_uom")
            else "",
        )

    def _get_lang(self):
        """Determine language to use for translated description."""
        return self.note_id.partner_id.lang or self.env.user.lang
