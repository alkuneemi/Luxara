# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCountry(models.Model):
    _inherit = 'res.country'

    city_ids = fields.One2many(string="Cities", comodel_name="res.city", inverse_name="country_id")
    enforce_cities = fields.Boolean(
        string='Enforce Cities',
        help="Check this box to ensure every address created in that country has a 'City' chosen "
             "in the list of the country's cities."
    )

    def _get_partner_city_field(self):
        if self._enforce_city_choice():
            return "city_id"
        return "city"

    def _enforce_city_choice(self):
        if not self:
            return False

        # Only enabled on frontend for those countries for now
        # Feature has to be adapted to be more generic and less blocking
        # before being enabled for other countries
        if self.code not in ['BR', 'CL', 'PE', 'CO', 'TW']:
            return False

        self.ensure_one()
        return self.enforce_cities and bool(
            self.env['res.city'].sudo().search_count([('country_id', '=', self.id)], limit=1)
        )
