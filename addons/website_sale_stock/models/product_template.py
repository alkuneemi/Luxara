# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _get_first_possible_combination(self, necessary_values=None):
        if self.env.context.get("website_id"):
            combinations = self._get_possible_combinations(necessary_values)
            return next(
                filter(self._is_combination_available, combinations),
                super()._get_first_possible_combination(necessary_values),
            )
        return super()._get_first_possible_combination(necessary_values)

    def _is_combination_available(self, combination):
        try:
            variant = self._get_variant_for_combination(combination)
            return variant and not variant._is_sold_out()
        except ValueError:
            return False
