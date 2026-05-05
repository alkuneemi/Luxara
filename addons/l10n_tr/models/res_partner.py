from odoo import api, models

from odoo.addons.account.tools.partner_identifiers import get_additional_identifiers_metadata_of_country


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.model
    def get_available_additional_identifiers_metadata(self, country_code, seq_min=0, seq_max=199):
        if country_code == 'TR':
            return get_additional_identifiers_metadata_of_country(
                country_code, include_international=False, seq_min=seq_min, seq_max=seq_max,
            )
        return super().get_available_additional_identifiers_metadata(country_code, seq_min=seq_min, seq_max=seq_max)
