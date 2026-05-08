from lxml import etree
from odoo.fields import Date
from odoo.addons.account_edi_ubl_cii.tools.ubl_20_optional_fields import PEPPOL_INVOICE_OPTIONAL_FIELDS, PEPPOL_INVOICE_OPTIONAL_LINE_FIELDS, PEPPOL_CREDIT_NOTE_OPTIONAL_FIELDS, PEPPOL_CREDIT_NOTE_OPTIONAL_LINE_FIELDS
from odoo.addons.account_edi_ubl_cii.tests.test_ubl_import_bis3_invoice_be import TestUblImportBis3InvoiceBE
from odoo.tests import tagged


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestUblImportBis3InvoiceBEOptionalFields(TestUblImportBis3InvoiceBE):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ubl_namespaces = {
            'cbc': "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            'cac': "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
        }

    def test_import_invoice_optional_fields(self):
        test_file = 'test_import_invoice_optional_fields'
        _fn, file_content = self._import_file_content(test_file, 'xml')

        xml_tree = etree.fromstring(file_content)

        tax_point_date = xml_tree.find('.//cbc:TaxPointDate', self.ubl_namespaces)
        contract_document_reference_id = xml_tree.find('.//cac:ContractDocumentReference/cbc:ID', self.ubl_namespaces)
        despatch_document_reference_id = xml_tree.find('.//cac:DespatchDocumentReference/cbc:ID', self.ubl_namespaces)
        accounting_cost = xml_tree.find('.//cbc:AccountingCost', self.ubl_namespaces)
        project_reference_id = xml_tree.find('.//cac:ProjectReference/cbc:ID', self.ubl_namespaces)
        order_reference_id = xml_tree.find('.//cac:OrderReference/cbc:ID', self.ubl_namespaces)
        invoice_period_start_date = xml_tree.find('.//cac:InvoicePeriod/cbc:StartDate', self.ubl_namespaces)
        invoice_period_end_date = xml_tree.find('.//cac:InvoicePeriod/cbc:EndDate', self.ubl_namespaces)
        order_line_reference_id = xml_tree.find('.//cac:InvoiceLine/cac:OrderLineReference/cbc:LineID', self.ubl_namespaces)
        buyers_item_id = xml_tree.find('.//cac:InvoiceLine/cac:Item/cac:BuyersItemIdentification/cbc:ID', self.ubl_namespaces)

        invoice_fields = {
            'x_studio_peppol_tax_point_date': Date.from_string(tax_point_date.text),
            'x_studio_peppol_contract_document_reference_id': contract_document_reference_id.text,
            'x_studio_peppol_despatch_document_reference_id': despatch_document_reference_id.text,
            'x_studio_peppol_accounting_cost': accounting_cost.text,
            'x_studio_peppol_order_reference_id': project_reference_id.text,
            'x_studio_peppol_invoice_period_start_date': Date.from_string(invoice_period_start_date.text),
            'x_studio_peppol_invoice_period_end_date': Date.from_string(invoice_period_end_date.text),
            'x_studio_peppol_project_reference_id': order_reference_id.text,
        }
        line_fields = {
            'x_studio_peppol_order_line_reference_id': order_line_reference_id.text,
            'x_studio_peppol_buyers_item_id': buyers_item_id.text,
        }

        # create the account.move fields.
        model_id = self.env["ir.model"]._get_id("account.move")
        self.env["ir.model.fields"].create([{
                "name": invoice_field,
                "model": "account.move",
                "model_id": model_id,
                "ttype": PEPPOL_INVOICE_OPTIONAL_FIELDS[invoice_field].get('type'),
                "state": "manual",
            }
            for invoice_field in invoice_fields
        ])

        # create the account.move.line fields.
        model_id = self.env["ir.model"]._get_id("account.move.line")
        self.env["ir.model.fields"].create([{
                "name": line_field,
                "model": "account.move",
                "model_id": model_id,
                "ttype": PEPPOL_INVOICE_OPTIONAL_LINE_FIELDS[line_field].get('type'),
                "state": "manual",
            }
            for line_field in line_fields
        ])

        # create the invoice
        invoice = self._import_invoice_as_attachment_on(
            test_name=test_file,
            journal=self.company_data['default_journal_purchase'],
        )

        for invoice_field_name, invoice_field_value in invoice_fields.items():
            self.assertEqual(invoice[invoice_field_name], invoice_field_value)

        for line_field_name, line_field_value in line_fields.items():
            self.assertEqual(invoice.invoice_line_ids[line_field_name], line_field_value)

    def test_import_credit_note_with_optional_fields(self):
        test_file = 'test_import_credit_note_optional_fields'
        _fn, file_content = self._import_file_content(test_file, 'xml')

        xml_tree = etree.fromstring(file_content)

        tax_point_date = xml_tree.find('.//cbc:TaxPointDate', self.ubl_namespaces)
        contract_document_reference_id = xml_tree.find('.//cac:ContractDocumentReference/cbc:ID', self.ubl_namespaces)
        despatch_document_reference_id = xml_tree.find('.//cac:DespatchDocumentReference/cbc:ID', self.ubl_namespaces)
        accounting_cost = xml_tree.find('.//cbc:AccountingCost', self.ubl_namespaces)
        order_reference_id = xml_tree.find('.//cac:OrderReference/cbc:ID', self.ubl_namespaces)
        invoice_period_start_date = xml_tree.find('.//cac:InvoicePeriod/cbc:StartDate', self.ubl_namespaces)
        invoice_period_end_date = xml_tree.find('.//cac:InvoicePeriod/cbc:EndDate', self.ubl_namespaces)
        order_line_reference_id = xml_tree.find('.//cac:CreditNoteLine/cac:OrderLineReference/cbc:LineID', self.ubl_namespaces)
        buyers_item_id = xml_tree.find('.//cac:CreditNoteLine/cac:Item/cac:BuyersItemIdentification/cbc:ID', self.ubl_namespaces)

        invoice_fields = {
            'x_studio_peppol_tax_point_date': Date.from_string(tax_point_date.text),
            'x_studio_peppol_contract_document_reference_id': contract_document_reference_id.text,
            'x_studio_peppol_despatch_document_reference_id': despatch_document_reference_id.text,
            'x_studio_peppol_accounting_cost': accounting_cost.text,
            'x_studio_peppol_order_reference_id': order_reference_id.text,
            'x_studio_peppol_invoice_period_start_date': Date.from_string(invoice_period_start_date.text),
            'x_studio_peppol_invoice_period_end_date': Date.from_string(invoice_period_end_date.text),
        }
        line_fields = {
            'x_studio_peppol_order_line_reference_id': order_line_reference_id.text,
            'x_studio_peppol_buyers_item_id': buyers_item_id.text,
        }

        # create the account.move fields.
        model_id = self.env["ir.model"]._get_id("account.move")
        self.env["ir.model.fields"].create([{
                "name": invoice_field,
                "model": "account.move",
                "model_id": model_id,
                "ttype": PEPPOL_CREDIT_NOTE_OPTIONAL_FIELDS[invoice_field].get('type'),
                "state": "manual",
            }
            for invoice_field in invoice_fields
        ])

        # create the account.move.line fields.
        model_id = self.env["ir.model"]._get_id("account.move.line")
        self.env["ir.model.fields"].create([{
                "name": line_field,
                "model": "account.move",
                "model_id": model_id,
                "ttype": PEPPOL_CREDIT_NOTE_OPTIONAL_LINE_FIELDS[line_field].get('type'),
                "state": "manual",
            }
            for line_field in line_fields
        ])

        # create the invoice
        invoice = self._import_invoice_as_attachment_on(
            test_name=test_file,
            journal=self.company_data['default_journal_purchase'],
        )

        for invoice_field_name, invoice_field_value in invoice_fields.items():
            self.assertEqual(invoice[invoice_field_name], invoice_field_value)

        for line_field_name, line_field_value in line_fields.items():
            self.assertEqual(invoice.invoice_line_ids[line_field_name], line_field_value)
