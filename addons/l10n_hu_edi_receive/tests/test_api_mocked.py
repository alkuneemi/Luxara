# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from odoo.addons.l10n_hu_edi.tests.common import L10nHuEdiTestCommon
from odoo.addons.l10n_hu_edi.models.l10n_hu_edi_connection import XML_NAMESPACES
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestApiMocked(L10nHuEdiTestCommon):

    def _get_mocked_requests(self):
        return ['queryInvoiceDigest', 'queryInvoiceData']

    def _get_request_file_name(self, service, data):
        batch_suffix = '_batch' if b'batchIndex' in data else ''
        return f'{service + batch_suffix}_request'

    def _get_response_file_name(self, service, data):
        if service == 'queryInvoiceDigest':
            file_name = 'queryInvoiceDigest_response'
        else:
            query = (etree.fromstring(data)).find('api:invoiceNumberQuery', namespaces=XML_NAMESPACES)
            file_name = query.findtext('api:invoiceNumber', namespaces=XML_NAMESPACES).replace('/', '_')
            if batch_index := query.findtext('api:batchIndex', namespaces=XML_NAMESPACES):
                file_name += ('_' + batch_index)

        return file_name

    def test_fetching_bills_from_nav(self):
        wizard = self.env['l10n_hu_edi_receive.bills.wizard'].create({})
        with self.patch_post():
            action = wizard.action_receive_bills()
        move_ids = action['params']['next']['domain'][0][2]
        moves = self.env['account.move'].browse(move_ids)
        self.assertRecordValues(moves, [
            {'ref': 'INV/2026/00003', 'move_type': 'in_invoice', 'amount_total': 771.75},
            {'ref': 'INV/2026/00004', 'move_type': 'in_invoice', 'amount_total': 298.45},
            {'ref': 'BATCH_MOD_2026_0002-1', 'move_type': 'in_refund', 'amount_total': 771.75},
            {'ref': 'BATCH_MOD_2026_0002-2', 'move_type': 'in_refund', 'amount_total': 298.45},
        ])
