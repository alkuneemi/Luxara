{
    'name': "Georgia - Accounting",
    'category': "Accounting/Localizations/Account Charts",
    'summary': "Georgian accounting localization package",
    'countries': ['GE'],
    'description': """
This module provides the basic accounting configuration required to use Odoo Accounting in Georgia, including:

* Georgian chart of accounts
* Tax groups and taxes
* Fiscal Positions
* VAT configuration:
    - 18% VAT
    - 0% VAT
    - Exempt taxes
    - Reverse charge VAT
* Withholding taxes:
    - 0%, 4%, 5%, 10%, and 15%
    - Gross and deducted withholding flows
* Export taxes
* Georgian tax reports:
    - VAT Report
    - Withholding Tax Report

The module is designed to provide a standard accounting setup for companies operating in Georgia and can be extended further based on specific business or legal requirements.
    """,
    'author': "Odoo S.A.",
    'depends': [
        'account',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'data': [
        'data/account_tax_report_data.xml',
        'data/account_tax_report_withholding_data.xml',
    ],
    'license': "LGPL-3",
}
