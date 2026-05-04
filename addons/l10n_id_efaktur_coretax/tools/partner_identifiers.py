# Part of Odoo. See LICENSE file for full copyright and licensing details.

"""Register Indonesia CoreTax TKU as a supported ``additional_identifiers`` key.

Canonical storage is ``res.partner.additional_identifiers['TKU']``.
"""

from odoo.tools.translate import LazyTranslate

from odoo.addons.account.tools import partner_identifiers as pi

_lt = LazyTranslate(__name__)

_TKU_METADATA = {
    'sequence': 12,
    'label': _lt('TKU'),
    'help': _lt('Branch Number of your company, leave empty for headquarters.'),
    'placeholder': '000000',
    'category': 'EN',
    'countries': ['ID'],
}

pi.IDENTIFIERS_METADATA['TKU'] = _TKU_METADATA
pi.ADDITIONAL_IDENTIFIERS_METADATA['TKU'] = _TKU_METADATA
