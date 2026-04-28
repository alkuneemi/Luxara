# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import SUPERUSER_ID, api


def _get_records(env, company, model_name, xmlids):
    if isinstance(xmlids, str):
        xmlids = [xmlids]

    IrModelData = env['ir.model.data']
    ids = [
        res_id
        for xmlid in xmlids
        if (res_id := IrModelData._xmlid_to_res_id(f'account.{company.id}_{xmlid}', raise_if_not_found=False))
    ]
    return env[model_name].browse(ids)


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    chart_template_model = env['account.chart.template']
    tax_group_template_data = chart_template_model._get_chart_template_model_data('ca_2023', 'account.tax.group')

    receivable_tax_accounts = [
        'l10n_ca_118100', 'l10n_ca_118200', 'l10n_ca_118300', 'l10n_ca_118400', 'l10n_ca_118500',
    ]
    payable_tax_accounts = [
        'l10n_ca_231000', 'l10n_ca_232000', 'l10n_ca_233000', 'l10n_ca_234000', 'l10n_ca_235000',
    ]

    for company in env['res.company'].search([('chart_template', '=', 'ca_2023')], order='parent_path'):
        accounts = _get_records(env, company, 'account.account', receivable_tax_accounts)
        if accounts:
            accounts.write({
                'account_type': 'asset_receivable',
                'reconcile': True,
                'non_trade': True,
            })

        accounts = _get_records(env, company, 'account.account', payable_tax_accounts)
        if accounts:
            accounts.write({
                'account_type': 'liability_payable',
                'reconcile': True,
                'non_trade': True,
            })

        for tax_group_xmlid, template_values in tax_group_template_data.items():
            tax_group = _get_records(env, company, 'account.tax.group', tax_group_xmlid)
            if not tax_group:
                continue

            values = {}
            for field_name in ('tax_payable_account_id', 'tax_receivable_account_id', 'advance_tax_payment_account_id'):
                if account_xmlid := template_values.get(field_name):
                    if account := _get_records(env, company, 'account.account', account_xmlid):
                        values[field_name] = account.id

            if values:
                tax_group.write(values)

        chart_template_model.try_loading('ca_2023', company, force_create=False)
