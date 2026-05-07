# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Indonesia E-Bupot',
    'icon': '/account/static/description/l10n.png',
    'description': """
        (TEMP)
    """,
    'category': 'Accounting/Localizations/EDI',
    'depends': ['l10n_id'],
    'data': [
        # New Data Import
        "data/ebupot_templates.xml",
        "data/ir_action.xml",

        # Views
        "views/ebupot_document.xml",
        "views/account_move_views.xml",
        "views/account_payment_register_views.xml",
        "views/account_payment_views.xml",

        # Accesses
        "security/ir.model.access.csv",
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}
