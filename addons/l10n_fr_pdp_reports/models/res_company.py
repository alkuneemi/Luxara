from odoo import api, fields, models



class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_fr_pdp_fiscal_representative_vat = fields.Char(
        string="PDP Fiscal Representative VAT",
        help="TT-122 VAT number used when seller VAT is not available on exempt invoices (tax category E).",
    )
    l10n_fr_pdp_periodicity = fields.Selection(  # TODO prevent chaning if flows exist ?
        selection=[
            ('normal_monthly', "Real Monthly Normal Regime"),
            ('normal_quarterly', "Real Normal Quarterly Regime"),
            ('simplified_monthly', "Simplified VAT Regime (Monthly)"),
            ('simplified_bimonthly', "Franchised VAT Regime (Bimonthly)"),
        ],
        string="Flow 10 Report Periodicity",
        default='normal_monthly',
        required=True,
        help="""Legal reporting period for transaction and payments flows according to the TVA regime table.
        Real Monthly Normal Regime : transactions reported by decade, payments reported monthly
        Real Normal Quarterly Regime : transactions reported monthly, payments reported monthly
        Simplified VAT Regime (Monthly) : transactions reported monthly, payments reported monthly
        Franchised VAT Regime (Bimonthly) : transactions reported bimonthly, payments reported bimonthly
        """,
    )
    l10n_fr_pdp_send_mode = fields.Selection(
        selection=[('auto', "Automatic cron"), ('manual', "Manual only")],
        string="PDP Send Mode",
        default='auto',
        help="Choose whether the sending cron dispatches ready flows automatically.",
        required=True,
    )
    l10n_fr_f10_enable_reporting = fields.Boolean(
        string="Enable Flux 10 Reporting",
        compute='_compute_l10n_fr_f10_enable_reporting',
        store=True,
        readonly=True,
    )


    @api.depends('l10n_fr_pdp_send_to_ppf', 'country_code', 'account_peppol_edi_user')
    def _compute_l10n_fr_f10_enable_reporting(self):
        for company in self:
            enable_reporting = (
                company.l10n_fr_pdp_send_to_ppf
                and company.account_peppol_edi_user
                and company.country_code == 'FR'
            )
            company.l10n_fr_f10_enable_reporting = enable_reporting
            if enable_reporting:
                company._l10n_fr_pdp_ensure_journal()

    def _l10n_fr_pdp_ensure_journal(self):
        """Create the e-reporting journal for each FR company with PDP enabled."""
        Journal = self.env['account.journal']
        company_with_erep_journal = [record['company_id'][0] for record in Journal.search_read(
            [('company_id', 'in', self.ids), ('code', '=', 'EREP')],
            ['company_id'],
        )]
        for company in self:
            if company.id in company_with_erep_journal:
                continue
            Journal.with_company(company.id).create({
                'name': "E-Reporting",
                'code': 'EREP',
                'type': 'sale',
                'show_on_dashboard': True,
                'company_id': company.id,
            })
