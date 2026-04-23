
from odoo.http import request
from odoo.addons.l10n_es.controllers.portal import L10nESPortalAccount


class L10nESEcommerceL10nES(L10nESPortalAccount):

    def _get_mandatory_billing_address_fields(self, country_sudo):
        field_names = super()._get_mandatory_billing_address_fields(country_sudo)
        order_id = request.session.get('sale_order_id')
        order = request.env['sale.order'].sudo().browse(order_id)
        simplified_invoice_limit = self.env['ir.config_parameter'].sudo().search(
            [('key', '=', 'l10n_es_ecommerce.simplified_invoice_limit')], limit=1)

        try:
            threshold_amount = float(simplified_invoice_limit.value)
        except (ValueError, TypeError):
            threshold_amount = 400.0
        # Super method already adds 'vat' for Spanish companies, so we only need to remove it if the order total is below the threshold
        if order.amount_total <= threshold_amount and field_names and 'vat' in field_names:
            field_names.remove('vat')

        return field_names
