# Part of Odoo. See LICENSE file for full copyright and licensing details.

from markupsafe import Markup

from odoo import _, api, fields, models


class DeliveryNoteWizard(models.TransientModel):
    _name = "delivery.note.wizard"
    _description = "Delivery Note Wizard"

    name = fields.Char(string="Note Reference", default="/")
    note_line_ids = fields.One2many(
        string="Operations", comodel_name="delivery.note.wizard.line", inverse_name="note_id"
    )
    dm_id = fields.Many2one(
        string="Delivery method", comodel_name="delivery.carrier", check_company=True
    )
    tracking_ref = fields.Char(string="Tracking Reference")
    tracking_url = fields.Char(string="Tracking URL", compute="_compute_tracking_url")
    shipping_date = fields.Date(string="Shipping Date", default=fields.Date.today)
    so_id = fields.Many2one(string="Sales Order", comodel_name="sale.order")
    so_reference = fields.Char(string="Order reference", related="so_id.name")
    company_id = fields.Many2one(related="so_id.company_id")
    partner_id = fields.Many2one(comodel_name="res.partner", related="so_id.partner_id")

    # === COMPUTE METHODS ===#

    @api.depends("dm_id", "tracking_ref")
    def _compute_tracking_url(self):
        for note in self:
            if note.dm_id.tracking_url and note.tracking_ref:
                note.tracking_url = note.dm_id.tracking_url.replace(
                    "<shipmenttrackingnumber>", note.tracking_ref
                )
            else:
                note.tracking_url = False

    # === BUSINESS METHODS ===#

    def action_confirm(self):
        for note in self:
            lines_to_ship = note.note_line_ids.filtered(lambda _line: _line.product_uom_qty)
            if not lines_to_ship:  # No products to ship.
                continue

            # Generate reference.
            note.name = self.env["ir.sequence"].next_by_code("delivery.note.wizard")

            # Log the confirmation message and send the email.
            note._log_shipping_confirmation_msg(lines_to_ship)
            note._send_shipping_confirmation_email()

            # Update the SO lines.
            lines_to_ship._update_sol_qty_delivered()

            # Set the delivery line as delivered
            for line in note.so_id.order_line.filtered("is_delivery"):
                line.qty_delivered = line.product_uom_qty

    def _log_shipping_confirmation_msg(self, lines_to_ship):
        """Log a message on the sale order confirming the shipment.

        :param delivery.note.wizard.line lines_to_ship: list of delivery note lines to ship
        """
        self.ensure_one()
        msg = _("A shipment has been confirmed with %s containing:", self.dm_id.name)
        product_lines = Markup("<ul>%s</ul>") % Markup("").join([
            Markup("<li>%s</li>") % line._get_line_representation() for line in lines_to_ship
        ])
        tracking_url = (
            Markup("<a href='%s'>%s</a>") % (self.tracking_url, _("Track Shipping"))
            if self.tracking_url
            else ""
        )
        message_body = Markup("%s%s%s") % (msg, product_lines, tracking_url)
        self.so_id.message_post(body=message_body)

    def _send_shipping_confirmation_email(self):
        """Send an email to the customer confirming the shipment."""
        self.ensure_one()
        delivery_note_template = self.env.ref(
            "delivery.mail_template_data_delivery_note", raise_if_not_found=False
        )
        if delivery_note_template:
            delivery_note_template.send_mail(
                self.id, email_values={"model": "sale.order", "res_id": self.so_id.id}
            )

    def _get_undelivered_lines(self):
        self.ensure_one()
        return self.note_line_ids.filtered(
            lambda line: (
                (line.sol_id.product_uom_qty - line.sol_id.qty_delivered)
                and (
                    line.product_uom_qty < (line.sol_id.product_uom_qty - line.sol_id.qty_delivered)
                    if line.product_uom_qty >= 0
                    else line.product_uom_qty
                    > (line.sol_id.product_uom_qty - line.sol_id.qty_delivered)
                )
            )
        )

    def _get_report_lang(self):
        """Determine language to use for translated description."""
        return self.partner_id.lang or self.env.lang
