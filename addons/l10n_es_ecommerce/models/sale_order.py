# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models


class SaleOrder(models.Model):

    _inherit = 'sale.order'

    def _create_account_invoices(self, invoice_vals_list):
        res = super()._create_account_invoices(invoice_vals_list)
        simplified_invoice_limit = self.env['ir.config_parameter'].sudo().search([('key', '=', 'l10n_es_ecommerce.simplified_invoice_limit')], limit=1)
        try:
            journal_id = self.env["ir.config_parameter"].sudo().search([('key', '=', 'l10n_es_ecommerce.default_simplified_journal_id')], limit=1)
        except (ValueError, TypeError):
            journal_id = self.env["account.journal"].search([('key', '=', 'account.1_sale')], limit=1)
        try:
            threshold_amount = float(simplified_invoice_limit.value)
        except (ValueError, TypeError):
            threshold_amount = 400.0
        for move in res:
            if move.country_code == 'ES' and move.amount_total < threshold_amount:
                move['journal_id'] = self.env["account.journal"].sudo().search([('id', '=', journal_id.value)])
        return res
