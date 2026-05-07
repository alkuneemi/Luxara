# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'POS Self Order SMS',
    'category': 'Sales/Point Of Sale',
    'description': """Integrates POS Self Order with SMS to send customers order confirmation and receipt.""",
    'depends': ['pos_self_order', 'pos_sms'],
    'data': [
        'views/pos_preset_views.xml',
    ],
    'assets': {
        'pos_self_order.assets': [
            'pos_self_order_sms/static/src/**/*',
        ],
        'web.assets_unit_tests': [
            'pos_self_order_sms/static/tests/unit/**/*',
        ],
    },
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'auto_install': True,
}
