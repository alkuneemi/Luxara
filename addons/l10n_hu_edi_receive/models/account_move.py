# Part of Odoo. See LICENSE file for full copyright and licensing details.

import gzip

from base64 import b64decode, b64encode
from lxml import etree
from markupsafe import Markup

from odoo import Command, api, models
from odoo.addons.l10n_hu_edi.models.l10n_hu_edi_connection import XML_NAMESPACES


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _l10n_hu_edi_parse_digest_response(self, response_xml):
        digests = []
        for digest in response_xml.iterfind('api:invoiceDigestResult/api:invoiceDigest', namespaces=XML_NAMESPACES):
            invoice_number = digest.findtext('api:invoiceNumber', namespaces=XML_NAMESPACES)
            batch_index = digest.findtext('api:batchIndex', namespaces=XML_NAMESPACES)
            ref = (invoice_number + '-' + batch_index) if batch_index else invoice_number

            supplier_tax_number = digest.findtext('api:supplierTaxNumber', namespaces=XML_NAMESPACES)
            supplier_group_member_tax_number = digest.findtext('api:supplierGroupMemberTaxNumber', namespaces=XML_NAMESPACES)
            taxpayer_id = supplier_group_member_tax_number or supplier_tax_number

            move_domain = [
                *self._check_company_domain(self.env.company),
                ('move_type', 'in', self.get_purchase_types()),
                ('ref', '=', ref),
                ('partner_id.vat', '=ilike', taxpayer_id + '%'),
            ]
            if self.search(move_domain).filtered(lambda m: (m.partner_id.l10n_hu_eu_vat or '')[2:] == taxpayer_id):
                continue

            query_invoice_data_params = {
                'invoiceNumber': invoice_number,
                'invoiceDirection': 'INBOUND',
                'batchIndex': batch_index,
                'supplierTaxNumber': supplier_tax_number,
            }

            digests.append(query_invoice_data_params)

        return digests

    @api.model
    def _l10n_hu_edi_parse_query_invoice_data_response(self, response_xml):
        if response_xml.find('api:invoiceDataResult', namespaces=XML_NAMESPACES) is None:
            return [], []
        invoice_data = b64decode(response_xml.findtext('api:invoiceDataResult/api:invoiceData', namespaces=XML_NAMESPACES))
        if response_xml.findtext('api:invoiceDataResult/api:compressedContentIndicator', namespaces=XML_NAMESPACES) == 'true':
            invoice_data = gzip.decompress(invoice_data)

        audit_data = response_xml.find('api:invoiceDataResult/api:auditData', namespaces=XML_NAMESPACES)
        move_vals = {
            'l10n_hu_edi_transaction_code': audit_data.findtext('api:transactionId', namespaces=XML_NAMESPACES),
            'l10n_hu_edi_batch_upload_index': int(audit_data.findtext('api:index', namespaces=XML_NAMESPACES)),
            'l10n_hu_edi_send_time': audit_data.findtext('api:insdate', namespaces=XML_NAMESPACES).rstrip('Z').replace('T', ' '),
        }

        return self._l10n_hu_edi_parse_invoice_data_xml(etree.fromstring(invoice_data), move_vals)

    @api.model
    def _l10n_hu_edi_parse_invoice_data_xml(self, invoice_data_xml, common_move_vals=None):
        if common_move_vals is None:
            common_move_vals = {}
        common_move_vals.update({
            'ref': invoice_data_xml.findtext('data:invoiceNumber', namespaces=XML_NAMESPACES),
            'invoice_date': invoice_data_xml.findtext('data:invoiceIssueDate', namespaces=XML_NAMESPACES),
            'l10n_hu_edi_attachment': b64encode(etree.tostring(invoice_data_xml)),
        })
        moves_vals_list = []
        post_process_data_list = []

        if (invoice_xml := invoice_data_xml.find('data:invoiceMain/data:invoice', namespaces=XML_NAMESPACES)) is not None:
            move_vals, post_process_data = self._l10n_hu_edi_parse_invoice_xml(invoice_xml)
            move_vals.update(common_move_vals)
            moves_vals_list.append(move_vals)
            post_process_data_list.append(post_process_data)
        else:
            for batch_invoice in invoice_data_xml.iterfind('data:invoiceMain/data:batchInvoice', namespaces=XML_NAMESPACES):
                move_vals, post_process_data = self._l10n_hu_edi_parse_invoice_xml(batch_invoice.find('data:invoice', namespaces=XML_NAMESPACES))
                move_vals.update({
                    **common_move_vals,
                    'ref': common_move_vals['ref'] + '-' + batch_invoice.findtext('data:batchIndex', namespaces=XML_NAMESPACES),
                })
                moves_vals_list.append(move_vals)
                post_process_data_list.append(post_process_data)

        return moves_vals_list, post_process_data_list

    @api.model
    def _l10n_hu_edi_parse_invoice_xml(self, invoice_xml):
        """ Returns a tuple of (move_vals, post_process_data)

        :return: tuple(move_vals, post_process_data)
            * move_vals: dict of values to create an `account.move`.
            * post_process_data: dict containing additional data used during
            move post-processing, with the following shape:
                - gross_total (float): Gross total parsed from the XML.
                - missing_taxes_error (Markup | None): HTML formatted message
                listing missing taxes, if any.
        """
        def parse_vat(tax_number_xml):
            if tax_number_xml is None:
                return

            parts = [
                tax_number_xml.findtext('base:taxpayerId', namespaces=XML_NAMESPACES),
                tax_number_xml.findtext('base:vatCode', namespaces=XML_NAMESPACES),
                tax_number_xml.findtext('base:countyCode', namespaces=XML_NAMESPACES),
            ]

            return '-'.join(filter(None, parts))

        invoice_head = invoice_xml.find('data:invoiceHead', namespaces=XML_NAMESPACES)
        invoice_detail = invoice_head.find('data:invoiceDetail', namespaces=XML_NAMESPACES)
        invoice_category = invoice_detail.findtext('data:invoiceCategory', namespaces=XML_NAMESPACES)

        invoice_reference = invoice_xml.find('data:invoiceReference', namespaces=XML_NAMESPACES)

        if invoice_category == 'SIMPLIFIED':
            gross_total = sum(
                float(summary_simplified.findtext('data:vatContentGrossAmount', namespaces=XML_NAMESPACES))
                for summary_simplified in invoice_xml.iterfind('data:invoiceSummary/data:summarySimplified', namespaces=XML_NAMESPACES)
            )
        else:
            gross_total = (
                float(invoice_xml.findtext('data:invoiceSummary/data:summaryNormal/data:invoiceNetAmount', namespaces=XML_NAMESPACES)) +
                float(invoice_xml.findtext('data:invoiceSummary/data:summaryNormal/data:invoiceVatAmount', namespaces=XML_NAMESPACES))
            )

        move_type = 'in_invoice' if (invoice_reference is None) or (gross_total >= 0) else 'in_refund'

        supplier_info = invoice_head.find('data:supplierInfo', namespaces=XML_NAMESPACES)
        taxpayer_id = (
            supplier_info.findtext('data:groupMemberTaxNumber/base:taxpayerId', namespaces=XML_NAMESPACES) or
            supplier_info.findtext('data:supplierTaxNumber/base:taxpayerId', namespaces=XML_NAMESPACES)
        )
        partner = self.env['res.partner'].search([('vat', '=ilike', taxpayer_id + '%')]).filtered(lambda p: (p.l10n_hu_eu_vat or '')[2:] == taxpayer_id)[:1]
        if not partner:
            supplier_tax_number = parse_vat(supplier_info.find('data:supplierTaxNumber', namespaces=XML_NAMESPACES))
            supplier_group_member_tax_number = parse_vat(supplier_info.find('data:groupMemberTaxNumber', namespaces=XML_NAMESPACES))
            supplier_address = supplier_info.find('data:supplierAddress/base:simpleAddress', namespaces=XML_NAMESPACES)
            if supplier_address is None:
                supplier_address = supplier_info.find('data:supplierAddress/base:detailedAddress', namespaces=XML_NAMESPACES)

            partner = self.env['res.partner'].create({
                'name': supplier_info.findtext('data:supplierName', namespaces=XML_NAMESPACES),
                'vat': supplier_group_member_tax_number or supplier_tax_number,
                'l10n_hu_group_vat': supplier_group_member_tax_number and supplier_tax_number,
                'country_id': self.env['res.country'].search([('code', '=', supplier_address.findtext('base:countryCode', namespaces=XML_NAMESPACES))], limit=1).id,
                'zip': supplier_address.findtext('base:postalCode', namespaces=XML_NAMESPACES),
                'city': supplier_address.findtext('base:city', namespaces=XML_NAMESPACES),
                'street': supplier_address.findtext('base:additionalAddressDetail', namespaces=XML_NAMESPACES) or supplier_address.findtext('base:streetName', namespaces=XML_NAMESPACES),
            })

            if supplier_bank_account_number := supplier_info.findtext('data:supplierBankAccountNumber', namespaces=XML_NAMESPACES):
                partner.bank_ids = [Command.create({'acc_number': supplier_bank_account_number})]

        move_vals = {
            'l10n_hu_invoice_chain_index': -1 if invoice_reference is None else int(invoice_reference.findtext('data:modificationIndex', namespaces=XML_NAMESPACES)),
            'l10n_hu_payment_mode': invoice_detail.findtext('data:paymentMethod', namespaces=XML_NAMESPACES),
            'delivery_date': invoice_detail.findtext('data:invoiceDeliveryDate', namespaces=XML_NAMESPACES),
            'invoice_date_due': invoice_detail.findtext('data:paymentDate', namespaces=XML_NAMESPACES),
            'currency_id': self.env['res.currency'].with_context(active_test=False).search([('name', '=', invoice_detail.findtext('data:currencyCode', namespaces=XML_NAMESPACES))], limit=1).id,
            'invoice_currency_rate': float(invoice_detail.findtext('data:exchangeRate', namespaces=XML_NAMESPACES)),
            'move_type': move_type,
            'partner_id': partner.id,
        }

        if invoice_reference is not None:
            original_invoice_number = invoice_reference.findtext('data:originalInvoiceNumber', namespaces=XML_NAMESPACES)
            original_invoice = self.search([('ref', '=', original_invoice_number), ('partner_id', '=', partner.id)], limit=1)
            if original_invoice:
                original_invoice_field = 'reversed_entry_id' if move_type == 'in_refund' else 'debit_origin_id'
                move_vals[original_invoice_field] = original_invoice.id

        if move_type == 'in_refund':
            account_number_path = 'data:customerInfo/data:customerBankAccountNumber'
            bank_partner = self.env.company.partner_id
        else:
            account_number_path = 'data:supplierInfo/data:supplierBankAccountNumber'
            bank_partner = partner
        account_number = invoice_head.findtext(account_number_path, namespaces=XML_NAMESPACES)
        if account_number:
            partner_bank = self.env['res.partner.bank'].search([('acc_number', '=', account_number), ('partner_id', '=', bank_partner.id)], limit=1)
            if not partner_bank:
                partner_bank = self.env['res.partner.bank'].create({
                    'acc_number': account_number,
                    'partner_id': bank_partner.id,
                })
            move_vals['partner_bank_id'] = partner_bank.id

        lines_vals = []
        no_tax_logs = []
        has_downpayment_field = 'is_downpayment' in self.env['account.move.line']._fields
        for line in invoice_xml.iterfind('data:invoiceLines/data:line', namespaces=XML_NAMESPACES):
            quantity = float(line.findtext('data:quantity', namespaces=XML_NAMESPACES) or 1)
            discount = float(line.findtext('data:lineDiscountData/data:discountRate', namespaces=XML_NAMESPACES) or 0) * 100
            amounts = line.find('data:lineAmountsSimplified' if invoice_category == 'SIMPLIFIED' else 'data:lineAmountsNormal', namespaces=XML_NAMESPACES)
            skip_tax = False
            price_unit = float(line.findtext('data:unitPrice', namespaces=XML_NAMESPACES) or 0)
            if not price_unit:
                if invoice_category == 'SIMPLIFIED':
                    price_unit = float(amounts.findtext('data:lineGrossAmountSimplified', namespaces=XML_NAMESPACES) or 0)
                else:
                    net = float(amounts.findtext('data:lineNetAmountData/data:lineNetAmount', namespaces=XML_NAMESPACES) or 0)
                    vat = float(amounts.findtext('data:lineVatData/data:lineVatAmount', namespaces=XML_NAMESPACES) or 0)
                    gross = amounts.findtext('data:lineGrossAmountData/data:lineGrossAmountNormal', namespaces=XML_NAMESPACES)
                    if not net and vat:                                                # net:0, vat:x, gross:x
                        price_unit = vat
                        skip_tax = True
                    elif net and vat and (gross is not None) and (float(gross) == 0):  # net:-x, vat: x, gross:0
                        price_unit = 0
                    else:                                                              # (net:x, vat:0/y) OR (net:0, vat:0)
                        price_unit = net
                price_unit += price_unit * discount / 100
                quantity = 1

            line_vals = {
                'display_type': 'product',
                'name': line.findtext('data:lineDescription', namespaces=XML_NAMESPACES),
                'discount': discount,
                'quantity': abs(quantity) if move_type == 'in_refund' else quantity,
                'price_unit': abs(price_unit) if move_type == 'in_refund' else price_unit
            }

            if has_downpayment_field:
                line_vals['is_downpayment'] = (line.findtext('data:advanceData/data:advanceIndicator', namespaces=XML_NAMESPACES) == 'true')

            if (product_codes := line.find('data:productCodes', namespaces=XML_NAMESPACES)) is not None:
                for product_code in product_codes.iterfind('data:productCode', namespaces=XML_NAMESPACES):
                    product_info = {'name': line_vals.get('name')}
                    if product_code_own_value := product_code.findtext('data:productCodeOwnValue', namespaces=XML_NAMESPACES):
                        product_info['default_code'] = product_code_own_value
                    else:
                        product_info['extra_domain'] = [
                            ('l10n_hu_product_code_type', '=', product_code.findtext('data:productCodeCategory', namespaces=XML_NAMESPACES)),
                            ('l10n_hu_product_code', '=', product_code.findtext('data:productCodeValue', namespaces=XML_NAMESPACES)),
                        ]

                    product = self.env['product.product']._retrieve_product(**product_info)
                    if product:
                        line_vals['product_id'] = product.id
                        break

            if unit_of_measure := line.findtext('data:unitOfMeasure', namespaces=XML_NAMESPACES):
                if unit_of_measure == 'OWN':
                    uom_name = line.findtext('data:unitOfMeasureOwn', namespaces=XML_NAMESPACES)
                    uom_domain = [('name', '=', uom_name)]
                else:
                    uom_domain = [('l10n_hu_edi_code', '=', unit_of_measure)]

                if uom := self.env['uom.uom'].search(uom_domain, limit=1):
                    line_vals['product_uom_id'] = uom.id

            if not skip_tax:
                line_vat_rate = amounts.find('data:lineVatRate', namespaces=XML_NAMESPACES)
                l10n_hu_tax_type = rate = None
                if vat_percentage := line_vat_rate.findtext('data:vatPercentage', namespaces=XML_NAMESPACES):
                    rate = vat_percentage
                    l10n_hu_tax_type = 'VAT'
                elif (vat_exemption := line_vat_rate.find('data:vatExemption', namespaces=XML_NAMESPACES)) is not None:
                    l10n_hu_tax_type = vat_exemption.findtext('data:case', namespaces=XML_NAMESPACES)
                elif (vat_out_of_scope := line_vat_rate.find('data:vatOutOfScope', namespaces=XML_NAMESPACES)) is not None:
                    l10n_hu_tax_type = vat_out_of_scope.findtext('data:case', namespaces=XML_NAMESPACES)
                elif line_vat_rate.findtext('data:vatDomesticReverseCharge', namespaces=XML_NAMESPACES) == 'true':
                    l10n_hu_tax_type = 'DOMESTIC_REVERSE'
                elif margin_scheme_indicator := line_vat_rate.findtext('data:marginSchemeIndicator', namespaces=XML_NAMESPACES):
                    l10n_hu_tax_type = margin_scheme_indicator
                elif (vat_amount_mismatch := line_vat_rate.find('data:vatAmountMismatch', namespaces=XML_NAMESPACES)) is not None:
                    l10n_hu_tax_type = vat_amount_mismatch.findtext('data:case', namespaces=XML_NAMESPACES)
                    rate = vat_amount_mismatch.findtext('data:vatRate/data:vatPercentage', namespaces=XML_NAMESPACES)
                elif line_vat_rate.findtext('data:noVatCharge', namespaces=XML_NAMESPACES) == 'true':
                    l10n_hu_tax_type = 'NO_VAT'
                else:
                    rate = line_vat_rate.findtext('data:vatContent', namespaces=XML_NAMESPACES)

                tax_domain = [
                    *self.env['account.tax']._check_company_domain(self.env.company),
                    ('type_tax_use', '=', 'purchase'),
                    ('price_include', '=', invoice_category == 'SIMPLIFIED'),
                    *([('l10n_hu_tax_type', '=', l10n_hu_tax_type)] if l10n_hu_tax_type else []),
                    *([('amount', '=', float(rate) * 100)] if rate else []),
                ]
                if tax := self.env['account.tax'].search(tax_domain, limit=1):
                    line_vals['tax_ids'] = [Command.set([tax.id])]
                else:
                    tax_label = ' '.join(filter(None, [
                        rate and f"{rate}%",
                        l10n_hu_tax_type,
                    ]))
                    no_tax_logs.append(self.env._(
                        "Could not retrieve the tax: %(tax_label)s for line '%(line)s'.",
                        tax_label=tax_label,
                        line=line_vals.get('name')
                    ))

            lines_vals.append(Command.create(line_vals))

        move_vals['invoice_line_ids'] = lines_vals

        post_process_data = {
            'gross_total': gross_total,
            'missing_taxes_error': Markup("<ul>%s</ul>") % Markup().join(Markup("<li>%s</li>") % l for l in no_tax_logs) if no_tax_logs else None,
        }

        return move_vals, post_process_data

    @api.model
    def _l10n_hu_edi_post_process_data(self, moves, post_process_data_list):
        for move, post_process_data in zip(moves, post_process_data_list):
            if move.currency_id.compare_amounts(post_process_data['gross_total'], -move.amount_total_in_currency_signed) != 0:
                move.l10n_hu_edi_messages = {
                    'error_title': self.env._("Amount mismatch detected."),
                    'errors': [self.env._("The gross total on the bill received from NAV and computed is not the same. Please check XML file in 'NAV 3.0' tab.")],
                    'blocking_level': 'warning',
                }

            if missing_taxes_error := post_process_data.get('missing_taxes_error'):
                move.message_post(body=missing_taxes_error)

    def _l10n_hu_edi_invoice_decoder(self, invoice, file_data, new):
        xml_tree = file_data['xml_tree']
        root = etree.QName(xml_tree).localname
        parser = {'InvoiceData': self._l10n_hu_edi_parse_invoice_data_xml, 'QueryInvoiceDataResponse': self._l10n_hu_edi_parse_query_invoice_data_response}.get(root)
        moves_vals_list, post_process_data_list = parser(xml_tree)
        invoice.write(moves_vals_list[0])
        moves = invoice + self.create(moves_vals_list[1:])
        self._l10n_hu_edi_post_process_data(moves, post_process_data_list)
        return True

    def _get_edi_decoder(self, file_data, new=False):
        # EXTENDS 'account'
        if (
            self.country_code == 'HU'
            and file_data['type'] == 'xml'
            and etree.QName(file_data['xml_tree']).localname in ('InvoiceData', 'QueryInvoiceDataResponse')
        ):
            return self._l10n_hu_edi_invoice_decoder

        return super()._get_edi_decoder(file_data, new=new)
