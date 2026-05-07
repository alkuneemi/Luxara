# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _is_out_of_stock_for_website(self, warehouse):
        """Return whether this variant is out of stock for the given warehouse.

        Uses free_qty (on-hand minus reservations) in the context of the website's warehouse.
        When packagings (extra UoMs) exist on the variant, the threshold is the quantity
        represented by the smallest available packaging; otherwise the threshold is 1.

        :param stock.warehouse warehouse: warehouse linked to the website (may be falsy)
        :return: True if the variant is out of stock
        :rtype: bool
        """
        self.ensure_one()
        sudo = self.sudo()
        ctx = {"warehouse_id": warehouse.id} if warehouse else {}
        qty = sudo.with_context(**ctx).free_qty
        if sudo.extra_uom_ids:
            threshold = min(uom._compute_quantity(1.0, sudo.uom_id) for uom in sudo.extra_uom_ids)
        else:
            threshold = 1.0
        return qty < threshold


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _sync_website_published_state(self):
        """Auto-unpublish or republish products based on current stock availability.

        For each website with the setting enabled:
        - Unpublish if all active variants are out of stock and the product
          was not manually published by the merchant.
        - Republish if stock is restored and the system was the one that unpublished it.
        """
        if not self:
            return

        websites = (
            self.env["website"].sudo().search([("website_sale_unpublish_out_of_stock", "=", True)])
        )
        if not websites:
            return

        for website in websites:
            warehouse = website.warehouse_id
            templates = self.filtered(lambda t, w=website: not t.website_id or t.website_id == w)
            if not templates:
                continue

            for template in templates:
                if not template.is_storable:
                    continue

                if template.allow_out_of_stock_order:
                    if not template.is_published and template.website_sale_auto_unpublished:
                        template.sudo().with_context(website_sale_syncing_published=True).write({
                            "is_published": True,
                            "website_sale_auto_unpublished": False,
                            "website_sale_manual_published": False,
                        })
                    continue

                variants = template.product_variant_ids.filtered("active")
                if not variants:
                    continue

                is_all_out_of_stock = all(
                    variant._is_out_of_stock_for_website(warehouse) for variant in variants
                )

                if is_all_out_of_stock:
                    if template.is_published and not template.website_sale_manual_published:
                        template.sudo().with_context(website_sale_syncing_published=True).write({
                            "is_published": False,
                            "website_sale_auto_unpublished": True,
                        })
                elif not template.is_published and template.website_sale_auto_unpublished:
                    template.sudo().with_context(website_sale_syncing_published=True).write({
                        "is_published": True,
                        "website_sale_auto_unpublished": False,
                        "website_sale_manual_published": False,
                    })


class Website(models.Model):
    _inherit = "website"

    warehouse_id = fields.Many2one("stock.warehouse", string="Warehouse")

    # === CRUD METHODS ===#

    def write(self, vals):
        """Unpublish out-of-stock products immediately when the setting is first enabled."""
        newly_enabled = (
            self.filtered(lambda w: not w.website_sale_unpublish_out_of_stock)
            if vals.get("website_sale_unpublish_out_of_stock")
            else self.env["website"]
        )

        res = super().write(vals)

        for website in newly_enabled:
            templates = (
                self
                .env["product.template"]
                .sudo()
                .search([
                    ("is_published", "=", True),
                    "|",
                    ("website_id", "=", website.id),
                    ("website_id", "=", False),
                ])
            )
            templates._sync_website_published_state()

        return res

    def _get_product_available_qty(self, product, **_kwargs):
        """Override of _get_product_available_qty in website_sale module
        Give the available quantity of a given product.

        NB: this method is only meant to be used on the shop before the checkout.
        For checkout steps, please use `cart._get_free_qty` instead to consider
        the chosen warehouse for delivery (website_sale_collect).

        :param product: product.product record
        :param dict kwargs: unused parameters, available for overrides
        :return: available quantity
        :rtype: float
        """
        return product.with_context(warehouse_id=self.warehouse_id.id).free_qty
