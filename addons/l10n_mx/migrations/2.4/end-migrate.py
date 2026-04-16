from odoo import api, SUPERUSER_ID


def _get_accounts(env, company, xmlids):
    if isinstance(xmlids, str):
        xmlids = [xmlids]
    IrModelData = env['ir.model.data']
    ids = [
        res_id for xmlid in xmlids
        if (res_id := IrModelData._xmlid_to_res_id(f'account.{company.id}_{xmlid}'))
    ]
    return env['account.account'].browse(ids)

def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    for company in env['res.company'].search([('chart_template', '=', 'mx')], order="parent_path"):
        accounts = _get_accounts(env, company, [
            'cuenta171_02_01', 'cuenta171_03_01', 'cuenta171_04_01', 'cuenta171_05_01',
            'cuenta171_16_01', 'cuenta171_17_01', 'cuenta171_18_01',
            'cuenta183_01_01', 'cuenta183_07_01',
        ])
        if accounts:
            accounts.account_type = 'asset_non_current'

        accounts = _get_accounts(env, company, [
            'cuenta613_02_01', 'cuenta613_03_01', 'cuenta613_04_01', 'cuenta613_05_01',
            'cuenta613_16_01', 'cuenta613_17_01', 'cuenta613_18_01',
            'cuenta614_01_01', 'cuenta614_07_01',
        ])
        if accounts:
            accounts.account_type = 'expense_depreciation'

        asset_model = env.ref(f'account.{company.id}_asset_80_month_linear', raise_if_not_found=False)
        asset_mappings = [
            ('cuenta153_01_01', 'cuenta171_02_01', 'cuenta613_02_01'),  # Machinery & equipment
            ('cuenta154_01_01', 'cuenta171_03_01', 'cuenta613_03_01'),  # Vehicles
            ('cuenta155_01_01', 'cuenta171_04_01', 'cuenta613_04_01'),  # Furniture & Office Equipment
            ('cuenta156_01_01', 'cuenta171_05_01', 'cuenta613_05_01'),  # Technology
            ('cuenta168_01_01', 'cuenta171_16_01', 'cuenta613_16_01'),  # Renewable Energy
            ('cuenta169_01_01', 'cuenta171_18_01', 'cuenta613_18_01'),  # Other Machines & Equipment
            ('cuenta170_01_01', 'cuenta171_17_01', 'cuenta613_17_01'),  # Upgrades and Retrofits
            ('cuenta179_01_01', 'cuenta183_07_01', 'cuenta614_07_01'),  # Brands and Patents
            ('cuenta173_01', 'cuenta183_01_01', 'cuenta614_01_01'),  # Deferred Expenses
        ]
        for asset_xmlid, dep_xmlid, exp_xmlid in asset_mappings:
            account = _get_accounts(env, company, asset_xmlid)
            if not account:
                continue
            vals = {}
            vals['depreciation_model_id'] = asset_model.id
            vals['asset_depreciation_account_id'] = _get_accounts(env, company, dep_xmlid).id
            vals['asset_expense_account_id'] = _get_accounts(env, company, exp_xmlid).id
            if vals:
                account.write(vals)

        # Reload template to populate any remaining new template fields
        env['account.chart.template'].try_loading('mx', company, force_create=False)

