# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from odoo.tools.float_utils import float_compare
from odoo.exceptions import ValidationError


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _l10n_id_ebupot_build_invoice_line_vals(self, vals, allocated_base=None):
        self.ensure_one()

        base_amount = allocated_base if allocated_base is not None else self.price_subtotal
        if float_compare(base_amount, 0.0, precision_rounding=self.currency_id.rounding) < 0:
            raise ValidationError(_("Price for line '%s' cannot be a negative amount.", self.name))
        ChartTemplate = self.env['account.chart.template'].with_company(self.company_id)
        pph_tax_groups = {
            ChartTemplate.ref('l10n_id_tax_group_pph22', raise_if_not_found=False),
            ChartTemplate.ref('l10n_id_tax_group_pph23', raise_if_not_found=False),
            ChartTemplate.ref('l10n_id_tax_group_pph42', raise_if_not_found=False),
        }

        pph_tax = self.tax_ids.filtered(lambda tax: tax.tax_group_id in pph_tax_groups)
        if pph_tax:
            vals.update({
                "TaxCertificate": self.tax_ids.l10n_id_ebupot_facility.code,
                "TaxObjectCode": self.tax_ids.l10n_id_ebupot_code.code,
                "TaxBase": base_amount,
                "Rate": abs(self.tax_ids.amount),
            })
