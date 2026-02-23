from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_fr_pdp_declarant_siren = fields.Char(
        string="PDP Declarant SIREN Override",
        help="Optional SIREN override used in Flux 10 headers for qualification test datasets.",
    )
    l10n_fr_pdp_fiscal_representative_vat = fields.Char(
        string="PDP Fiscal Representative VAT",
        help="TT-122 VAT number used when seller VAT is not available on exempt invoices (tax category E).",
    )
    l10n_fr_pdp_periodicity = fields.Selection(
        selection=[
            ('decade', "Decade (1-10 / 11-20 / 21-fin)"),
            ('monthly', "Monthly"),
            ('bimonthly', "Bimonthly"),
            ('quarterly', "Quarterly"),
        ],
        string="Transaction Periodicity",
        default='decade',
        required=True,
        help="Legal reporting period for transaction flows according to the TVA regime table.",
    )
    l10n_fr_pdp_payment_periodicity = fields.Selection(
        selection=[('monthly', "Monthly"), ('bimonthly', "Bimonthly")],
        string="Payment Periodicity",
        default='monthly',
        required=True,
        help="Frequency applied to payment flows; defaults to the monthly deadline described in Tableau 12.",
    )
    l10n_fr_pdp_tax_due_code = fields.Selection(
        selection=[('1', "Debits"), ('2', "Deliveries/Services"), ('3', "Receipts")],
        # selection=[('1', "Débits"), ('2', "Livraisons/Prestations"), ('3', "Encaissements")],
        string="Tax Due Date Type Code",
        default='3',
        required=True,
        help="TT-64 code used for tax due date type in Flux 10 (1=Débits, 2=Livraisons/Prestations, 3=Encaissements).",
    )
    l10n_fr_pdp_send_mode = fields.Selection(
        selection=[('auto', "Automatic cron"), ('manual', "Manual only")],
        string="PDP Send Mode",
        default='auto',
        help="Choose whether the sending cron dispatches ready flows automatically.",
        required=True,
    )

    def _l10n_fr_pdp_ensure_journal(self):
        """Create the e-reporting journal for each FR company with PDP enabled."""
        Journal = self.env['account.journal']

        for company in self:
            if company.country_code != 'FR' or not company.l10n_fr_pdp_send_to_ppf:
                continue

            existing = Journal.search([
                ('company_id', '=', company.id),
                ('code', '=', 'EREP'),
            ], limit=1)
            if existing:
                continue

            Journal.with_company(company.id).create({
                'name': "E-Reporting",
                'code': 'EREP',
                'type': 'sale',
                'show_on_dashboard': True,
                'company_id': company.id,
            })

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        for company in companies:
            if company.country_code == 'FR' and company.l10n_fr_pdp_send_to_ppf:
                company._l10n_fr_pdp_ensure_journal()
        return companies

    def write(self, vals):
        res = super().write(vals)

        if 'l10n_fr_pdp_send_to_ppf' in vals:
            enabled = self.filtered(lambda c: c.l10n_fr_pdp_send_to_ppf and c.country_code == 'FR')
            enabled._l10n_fr_pdp_ensure_journal()

        return res
