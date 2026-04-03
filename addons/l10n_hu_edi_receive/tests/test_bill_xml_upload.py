# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.l10n_hu_edi.tests.common import L10nHuEdiTestCommon
from odoo.tests import tagged
from odoo.tools.misc import file_open


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestBillXmlUpload(L10nHuEdiTestCommon):

    def upload_xml(self, filename):
        file_path = f'l10n_hu_edi_receive/tests/invoice_xmls/{filename}'
        with file_open(file_path, 'rb') as file:
            content = file.read()
        attachment = self.env['ir.attachment'].create({
            'raw': content,
            'name': filename,
        })
        return self.company_data['default_journal_purchase'].with_context(default_move_type='in_invoice')._create_document_from_attachment(attachment.id)

    def test_normal_invoice_upload(self):
        bill = self.upload_xml('normal_invoice.xml')
        self.assertRecordValues(bill, [{
            'amount_total': 37677.0,
            'move_type': 'in_invoice',
            'ref': '2023/CT23026441',
        }])
        self.assertRecordValues(bill.partner_id, [{
            'name': 'Hadik András 2',
            'vat': '99999394-2-44',
        }])

    def test_simplified_invoice_upload(self):
        bill = self.upload_xml('simplified_invoice.xml')
        self.assertRecordValues(bill, [{
            'amount_total': 21794.0,
            'move_type': 'in_invoice',
            'ref': 'A06600324/1285/00009',
        }])

    def test_batch_modifications_upload(self):
        self.upload_xml('batch_modifications.xml')
        refunds = self.env['account.move'].search([('ref', '=ilike', '1562695%')])
        self.assertRecordValues(refunds, [
            {'amount_total': 1200.0, 'move_type': 'in_refund', 'ref': '1562695-2'},
            {'amount_total': 6035.65, 'move_type': 'in_refund', 'ref': '1562695-1'},
        ])

    def test_query_invoice_data_response_upload(self):
        bill = self.upload_xml('query_invoice_data_response.xml')
        self.assertRecordValues(bill, [{
            'amount_total': 189090.0,
            'move_type': 'in_invoice',
            'ref': '2023/XT23022800',
            'l10n_hu_edi_transaction_code': '4A0GZERATZ6GZ19L',
        }])

    def test_query_invoice_data_response_gzip_upload(self):
        bill = self.upload_xml('query_invoice_data_response_gzip.xml')
        self.assertRecordValues(bill, [{
            'amount_total': 159129.79,
            'move_type': 'in_invoice',
            'ref': '9859711680',
            'l10n_hu_edi_transaction_code': '4L21E9MOAB7T6DC7',
        }])

    def test_credit_note_upload(self):
        bill = self.upload_xml('credit_note_original_bill.xml')
        credit_note = self.upload_xml('credit_note.xml')
        self.assertEqual(credit_note.reversed_entry_id, bill)

    def test_debit_note_upload(self):
        bill = self.upload_xml('debit_note_original_bill.xml')
        debit_note = self.upload_xml('debit_note.xml')
        self.assertEqual(debit_note.debit_origin_id, bill)
