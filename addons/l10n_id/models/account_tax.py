# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_id_ebupot_code = fields.Many2one('l10n_id.ebupot.tax.category', string="E-Bupot Object Code")
    l10n_id_ebupot_facility = fields.Many2one('l10n_id.ebupot.tax.facility', string="E-Bupot Facility Code")
