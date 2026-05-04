from odoo import fields, models, api


class UomUom(models.Model):
    _inherit = "uom.uom"

    fiscal_country_codes = fields.Char(compute="_compute_fiscal_country_codes")
    fiscal_country_group_codes = fields.Json(compute='_compute_fiscal_country_group_codes')
    unece_code = fields.Char("UN/ECE Code", help="The code element for units of measurement (UoM) as specified by UN/ECE")

    @api.depends_context("allowed_company_ids")
    def _compute_fiscal_country_codes(self):
        for record in self:
            record.fiscal_country_codes = ",".join(self.env.companies.mapped("account_fiscal_country_id.code"))

    @api.depends_context('allowed_company_ids')
    def _compute_fiscal_country_group_codes(self):
        for uom in self:
            uom.fiscal_country_group_codes = list({
                code
                for company in self.env.companies
                for code in company.account_fiscal_country_group_codes
            })
