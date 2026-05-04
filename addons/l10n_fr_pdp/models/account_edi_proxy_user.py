import logging
from lxml import etree
from markupsafe import Markup

from odoo import api, fields, models, tools
from odoo.exceptions import UserError
from odoo.tools.translate import LazyTranslate

from odoo.addons.account_edi_proxy_client.models.account_edi_proxy_user import AccountEdiProxyError
from odoo.addons.account_peppol.models.account_edi_proxy_user import IAP_ENDPOINT_MAP
from odoo.addons.l10n_fr_pdp.tools.demo_utils import handle_demo
from odoo.addons.l10n_fr_pdp.utils.cdar import _parse_datetime_node as _parse_cdar_datetime_node

_logger = logging.getLogger(__name__)
_lt = LazyTranslate(__name__)
BATCH_SIZE = 50

CDAR_NSMAP = {
    'qdt': "urn:un:unece:uncefact:data:standard:QualifiedDataType:100",
    'rsm': "urn:un:unece:uncefact:data:standard:CrossDomainAcknowledgementAndResponse:100",
    'ram': "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    'udt': "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
    'xsi': "http://www.w3.org/2001/XMLSchema-instance",
}

PROCESS_CONDITION_CODE_TO_RESPONSE_CODE = {
    # PDP
    '200': 'submitted',  # PA-S (sending platform)
    '202': 'received',  # PA-R (receiving platform)
    '203': 'made_available',  # PA-R
    '204': 'in_hand',  # R (receiver)
    '205': 'approved',  # R
    '207': 'contested',  # R
    '210': 'refused',  # R
    '211': 'payment_sent',  # R
    '212': 'paid',  # S (sender)
    '213': 'rejected',  # PA-R
    '220': 'cancelled',  # S
    # PPF
    '500': 'received',
    '501': 'rejected',
    '250': 'approved',
    '251': 'refused',
    '300': 'approved',
    '301': 'refused',
    '400': 'approved',
    '401': 'refused',
    '601': 'refused',
}

STATUS_TO_PROCESS_CONDITION_CODE = {status: code for code, status in PROCESS_CONDITION_CODE_TO_RESPONSE_CODE.items()}

PAYMENT_TYPE_CODES = {
    'RAP': _lt("Amount remaining due"),  # Reste à payer
    'ESC': _lt("Early Payment Discount granted"),  # Escompte accordé
    'RAB': _lt("Discount granted"),  # Rabais accordé
    'REM': _lt("Discount granted"),  # Remise accordée
    'MPA': _lt("Amount paid"),  # Montant payé
    'MEN': _lt("Amount collected (including VAT)"),  # Montant encaissé (TTC)
}

FULLY_PAID_CODES = {'MPA', 'MEN'}


class AccountEdiProxyClientUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    proxy_type = fields.Selection(selection_add=[('pdp', 'Approved Platform')], ondelete={'pdp': 'cascade'})

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    @api.model
    def _get_peppol_proxy_types(self):
        # Extend 'account_peppol'
        return super()._get_peppol_proxy_types() + ['pdp']

    def _get_proxy_urls(self):
        urls = super()._get_proxy_urls()
        urls['pdp'] = {
            'prod': 'https://pdp.api.odoo.com',
            'test': 'https://pdp.test.odoo.com',
            'demo': 'demo',
        }
        return urls

    @handle_demo
    def _call_peppol_proxy(self, endpoint, params=None):
        return super()._call_peppol_proxy(endpoint, params=params)

    def _get_proxy_identification(self, company, proxy_type):
        if proxy_type != 'pdp':
            return super()._get_proxy_identification(company, proxy_type)
        if not company.pdp_identifier:
            scheme = dict(self.env["res.partner"]._fields['peppol_eas']._description_selection(self.env))["0225"]
            raise UserError(self.env._("Please fill the Peppol Endpoint field with scheme '%s' on the company partner.", scheme))
        return f'0225:{company.pdp_identifier}'

    @handle_demo
    def _register_proxy_user(self, company, proxy_type, edi_mode):
        """ Override to avoid using the deprecated route on IAP """
        if proxy_type != 'pdp':
            return super()._register_proxy_user(company, proxy_type, edi_mode)

        private_key_sudo = self.env['certificate.key'].sudo()._generate_rsa_private_key(
            company,
            name=f"{proxy_type}_{edi_mode}_{company.id}.key",
        )
        peppol_identifier = self._get_proxy_identification(company, proxy_type)
        if edi_mode == 'demo':
            # simulate registration
            response = {'id_client': f'demo{company.id}{proxy_type}', 'refresh_token': 'demo'}
        else:
            try:
                # b64encode returns a bytestring, we need it as a string
                response = self._make_request(self._get_server_url(proxy_type, edi_mode) + IAP_ENDPOINT_MAP['pdp']["connect"], params={
                    'dbuuid': company.env['ir.config_parameter'].get_param('database.uuid'),
                    'company_id': company.id,
                    'peppol_identifier': peppol_identifier,
                    'public_key': private_key_sudo._get_public_key_bytes(encoding='pem').decode(),
                })
            except AccountEdiProxyError as e:
                raise UserError(e.message)

        if error_message := response.get('error'):
            raise UserError(error_message)

        return self.create({
            'id_client': response['id_client'],
            'company_id': company.id,
            'proxy_type': 'pdp',
            'edi_mode': edi_mode,
            'edi_identification': peppol_identifier,
            'private_key_id': private_key_sudo.id,
            'refresh_token': response['refresh_token'],
        })

    @handle_demo
    def _peppol_register_receiver(self):
        self.ensure_one()
        if self.proxy_type != 'pdp':
            return super()._peppol_register_receiver()

        company = self.company_id
        if company.account_peppol_proxy_state in {'smp_registration', 'receiver'}:
            # a participant can only try registering as a receiver if they are not registered
            proxy_state_translated = dict(company._fields['account_peppol_proxy_state']._description_selection(self.env))[company.account_peppol_proxy_state]
            raise UserError(self.env._('Cannot register a user with a %s application', proxy_state_translated))

        super()._peppol_register_receiver()

        datetime_in_1_hour = fields.Datetime.add(fields.Datetime.now(), hours=1)
        self.env.ref('account_peppol.ir_cron_peppol_get_participant_status')._trigger(at=datetime_in_1_hour)

    def _pdp_get_new_regulatory_documents(self):
        job_count = BATCH_SIZE
        need_retrigger = False
        for edi_user in self:
            edi_user = edi_user.with_company(edi_user.company_id)
            if edi_user.proxy_type != 'pdp':
                continue
            try:
                # request all messages that haven't been acknowledged
                messages = edi_user._call_peppol_proxy(
                    endpoint=edi_user._get_peppol_proxy_endpoint('get_all_regulatory_documents'),
                )
            except AccountEdiProxyError as e:
                _logger.error('Error while receiving the document from Peppol Proxy: %s', e.message)
                continue

            message_uuids = [
                message['uuid']
                for message in messages.get('messages', [])
            ]
            if not message_uuids:
                continue

            need_retrigger = need_retrigger or len(message_uuids) > job_count
            message_uuids = message_uuids[:job_count]

            # retrieve attachments for filtered messages
            all_messages = edi_user._call_peppol_proxy(
                endpoint=edi_user._get_peppol_proxy_endpoint('get_regulatory_document'),
                params={'ppf_message_uuids': message_uuids},
            )
            processed_uuid_to_record = edi_user._pdp_process_new_regulatory_messages(all_messages)

            if not tools.config['test_enable']:
                self.env.cr.commit()
            if processed_uuid_to_record:
                edi_user._call_peppol_proxy(
                    endpoint=edi_user._get_peppol_proxy_endpoint('ack_regulatory'),
                    params={'message_uuids': list(processed_uuid_to_record)},
                )
        if need_retrigger:
            self.env.ref('l10n_fr_pdp.ir_cron_pdp_get_new_regulatory_documents')._trigger()

    def _peppol_process_messages_status(self, messages, uuid_to_record):
        self.ensure_one()
        processed_message_uuids = []
        other_messages = {}
        for uuid, content in messages.items():

            peppol_response = uuid_to_record[uuid]
            # In case of error we do not have a 'document_type'
            if peppol_response._name != 'account.peppol.response' or content['document_type'] != 'CrossDomainAcknowledgementAndResponse':
                other_messages[uuid] = content
                continue

            if content.get('error'):
                if content['error'].get('code') == 702:
                    # "Peppol request not ready" error:
                    # thrown when the IAP is still processing the message
                    continue
                if content['error'].get('code') == 207:
                    peppol_response.peppol_state = 'not_serviced'
                else:
                    peppol_response.peppol_state = 'error'
                    peppol_response.move_id._message_log(
                        body=self.env._("French e-invoicing response error: %s", content['error'].get('data', {}).get('message') or content['error']['message']),
                    )
                processed_message_uuids.append(uuid)
                continue

            peppol_response.peppol_state = content['state']
            processed_message_uuids.append(uuid)

            origin_move = peppol_response.move_id
            decoded_document = self._peppol_get_decoded_document(content)
            filename = content["filename"] or 'lifecycle'
            attachment = self.env["ir.attachment"].create(
                {
                    "name": f"{filename}.xml",
                    "raw": decoded_document,
                    "type": "binary",
                    "mimetype": "application/xml",
                    "res_id": origin_move.id,
                    "res_model": 'account.move',
                }
            )
            response_code_to_description_map = dict(peppol_response._fields['response_code']._description_selection(self.env))
            response_code_description = response_code_to_description_map.get(peppol_response.response_code, peppol_response.response_code)
            origin_move._message_log(
                body=self.env._(
                    "The Response issued on %(issue_date)s with Response Code '%(response_code)s' was sent by the access point.",
                    response_code=response_code_description,
                    issue_date=peppol_response.pdp_issue_date,
                ),
                attachment_ids=attachment.ids,
            )
        return processed_message_uuids + super()._peppol_process_messages_status(other_messages, uuid_to_record)

    def _pdp_send_response(self, reference_moves, status, additional_info=None):
        self.ensure_one()
        reference_moves = reference_moves.filtered(lambda rm: rm.pdp_can_send_response)
        if not reference_moves:
            return
        additional_info = additional_info or {}

        response_code_to_description_map = dict(self.env['account.peppol.response']._fields['response_code']._description_selection(self.env))
        if status not in response_code_to_description_map:
            raise UserError(self.env._("Unsupported response status: '%s'.", status))
        status_string = response_code_to_description_map[status]

        try:
            issue_time = fields.Datetime.now()
            additional_info['issue_datetime'] = fields.Datetime.to_string(issue_time)
            response = self._call_peppol_proxy(
                "/api/pdp/1/send_response",
                params={
                    'reference_uuids': reference_moves.mapped('peppol_message_uuid'),
                    'status': status,
                    'additional_info': additional_info,
                },
            )
        except UserError as e:
            log_message = Markup(self.env._(
                "An error occurred with the French e-invoicing proxy while sending a response.<br/>Status: %(status)s - %(error)s",
                status=status_string,
                error=str(e),
            ))
            reference_moves._message_log_batch(
                bodies={move.id: log_message for move in reference_moves},
            )
            return

        if response.get('error'):
            log_message = Markup(self.env._(
                "An error occurred with the French e-invoicing server while sending a response.<br/>Status: %(status)s - %(error)s",
                status=status_string,
                error=response['error']['message'],
            ))
            reference_moves._message_log_batch(
                bodies={move.id: log_message for move in reference_moves},
            )
            return
        status_infos = [{'note': additional_info.get('note')}]  # We only put the note since we have all other info
        self.env['account.peppol.response'].create([
            {
                'peppol_message_uuid': message['message_uuid'],
                'response_code': status,
                'peppol_state': 'processing',
                'move_id': move.id,
                'pdp_status_info': "\n\n".join([self._format_status_info(status) for status in status_infos]),
                'pdp_issue_date': issue_time,
                'pdp_flow_number': '2',
            }
            for message, move in zip(response.get('messages'), reference_moves)
        ])
        log_message = self.env._(
            "A French e-invoicing response with Response Code '%(status)s' was sent to the French e-invoicing Access Point.",
            status=status_string,
        )
        reference_moves._message_log_batch(bodies={move.id: log_message for move in reference_moves})

    def _peppol_process_new_messages(self, messages):
        self.ensure_one()
        # Note: We process the invoices first to avoid importing a response before its origin move
        other_uuids, moves = super()._peppol_process_new_messages(messages)

        processed_uuids = []
        response_uuids = [uuid for uuid in other_uuids if messages[uuid]['document_type'] == 'CrossDomainAcknowledgementAndResponse']

        origin_message_uuids = [messages[uuid]['origin_message_uuid'] for uuid in response_uuids]
        relevant_moves_domain = [
            ('peppol_message_uuid', 'in', origin_message_uuids),
            ('company_id', '=', self.company_id.id),
        ]
        uuid_to_move_map = self.env['account.move'].search(relevant_moves_domain).grouped('peppol_message_uuid')
        for uuid in response_uuids:
            content = messages[uuid]
            origin_uuid = content['origin_message_uuid']
            origin_move = uuid_to_move_map.get(origin_uuid)
            if not origin_move:
                _logger.warning('The French e-invoicing response with UUID %s could not be imported: Original journal entry (UUID %s) not found.', uuid, origin_uuid)
                continue
            if self._pdp_import_response(uuid, content, origin_move[:1]):
                processed_uuids.append(uuid)

        return other_uuids + processed_uuids, moves

    def _pdp_process_new_regulatory_messages(self, messages):
        self.ensure_one()
        processed_messages = {}
        origin_peppol_message_uuids = [content['origin_peppol_message_uuid'] for content in messages.values() if content['origin_peppol_message_uuid']]
        origin_domain = [
            ('peppol_message_uuid', 'in', origin_peppol_message_uuids),
            ('company_id', '=', self.company_id.id),
        ]
        original_moves = self.env['account.move'].search(origin_domain).grouped('peppol_message_uuid')

        for uuid, content in messages.items():
            if content['document_type'] != 'CrossDomainAcknowledgementAndResponse':
                continue
            flow_number = content['flow_number']
            if flow_number == '1':
                origin_uuid = content['origin_peppol_message_uuid']
                origin_move = original_moves.get(origin_uuid)
                if not origin_uuid or not origin_move:
                    _logger.warning('[Flow 1] The tax extract response from the PPF with UUID %s could not be imported: Original journal entry (UUID %s) not found.', uuid, origin_uuid)
                    continue
                if response := self._pdp_import_response(uuid, content, origin_move[:1]):
                    processed_messages[uuid] = response
            elif flow_number == '6':
                origin_uuid = content['origin_peppol_message_uuid']
                origin_move = original_moves.get(origin_uuid)
                if not origin_uuid or not origin_move:
                    _logger.warning('[Flow 6] The status response from the PPF with UUID %s could not be imported: Original journal entry (UUID %s) not found.', uuid, origin_uuid)
                    continue
                if response := self._pdp_import_response(uuid, content, origin_move[:1]):
                    processed_messages[uuid] = response

        return processed_messages

    def _pdp_import_response(self, uuid, content, origin_move):
        response = self.env['account.peppol.response']
        if not origin_move:
            return response

        flow_number = content.get('flow_number') or '2'
        decoded_document = self._peppol_get_decoded_document(content)
        info = self._pdp_extract_response_info(decoded_document)
        response_code = info['response_code']
        issue_date = info['issue_date']
        status_infos = info['status_infos']
        origin_ref_status_code = content.get("origin_ref_status_code")
        origin_ref_status = PROCESS_CONDITION_CODE_TO_RESPONSE_CODE.get(origin_ref_status_code)
        markup_status_info = Markup('<br/><br/>').join([self._format_status_info(status, separator=Markup('<br/>')) for status in status_infos])
        response_code_to_description_map = dict(response._fields['response_code']._description_selection(self.env))
        ref_status_code_to_description_map = dict(response._fields['pdp_ref_response_code']._description_selection(self.env))
        ref_status_code_description = ref_status_code_to_description_map.get(origin_ref_status)

        if response_code not in response_code_to_description_map or not issue_date or (flow_number == '6' and not ref_status_code_description):
            origin_move._message_log(
                body=self.env._(
                    "[Flow %(flow_number)s] Failed to process incoming response%(ref_status_info)s (Response Code = %(response_code)s; Issue Date = %(issue_date)s).%(br)s%(status_info)s",
                    flow_number=flow_number,
                    ref_status_info=f" for status {ref_status_code_description or origin_ref_status_code}" if origin_ref_status_code else '',
                    response_code=response_code,
                    issue_date=issue_date,
                    status_info=markup_status_info,
                    br=Markup('<br/>It included the following status info:<br/>') if markup_status_info else '',
                ),
            )
            return response

        filename = content["filename"] or 'lifecycle'
        attachment = self.env["ir.attachment"].create(
            {
                "name": f"{filename}.xml",
                "raw": decoded_document,
                "type": "binary",
                "mimetype": "application/xml",
                "res_id": origin_move.id,
                "res_model": 'account.move',
            }
        )

        response_code_description = response_code_to_description_map[response_code]
        response = self.env['account.peppol.response'].create({
            'peppol_message_uuid': uuid,
            'response_code': response_code,
            'peppol_state': content['state'],
            'move_id': origin_move.id,
            'pdp_ref_response_code': PROCESS_CONDITION_CODE_TO_RESPONSE_CODE.get(origin_ref_status_code),
            'pdp_status_info': '\n\n'.join([self._format_status_info(status, separator=Markup('\n')) for status in status_infos]),
            'pdp_issue_date': issue_date,
            'pdp_flow_number': flow_number,
            'pdp_fully_paid': any(payment.get('type_code') in FULLY_PAID_CODES for status in status_infos for payment in status.get('payments', []))
        })
        if content['state'] == 'done':
            origin_move._message_log(
                body=self.env._(
                    "[Flow %(flow_number)s] Received response%(ref_status_info)s with Response Code '%(response_code)s' issued on %(issue_date)s.%(br)s%(status_info)s",
                    flow_number=flow_number,
                    ref_status_info=f" for status {ref_status_code_description or origin_ref_status_code}" if origin_ref_status_code else '',
                    response_code=response_code_description,
                    issue_date=issue_date,
                    status_info=markup_status_info,
                    br=Markup('<br/>It included the following status info:<br/>') if markup_status_info else '',
                ),
                attachment_ids=attachment.ids,
            )
        return response

    @api.model
    def _pdp_parse_included_note(self, note_node):
        subject_code = note_node.findtext('./ram:SubjectCode', namespaces=CDAR_NSMAP)
        content = note_node.findtext('./ram:Content', namespaces=CDAR_NSMAP)
        return (f"({subject_code})" if subject_code else "") + content

    @api.model
    def _pdp_extract_response_info(self, document):
        xml_node = etree.fromstring(document)
        status_nodes = xml_node.findall("rsm:AcknowledgementDocument/ram:ReferenceReferencedDocument/ram:SpecifiedDocumentStatus", namespaces=CDAR_NSMAP)
        process_condition_code = xml_node.findtext("rsm:AcknowledgementDocument/ram:ReferenceReferencedDocument/ram:ProcessConditionCode", namespaces=CDAR_NSMAP)
        status_infos = [
            {
              'index': node.findtext("./ram:SequenceNumeric", namespaces=CDAR_NSMAP),
              'reason_code': node.findtext("./ram:ReasonCode", namespaces=CDAR_NSMAP),
              'reason': node.findtext("./ram:Reason", namespaces=CDAR_NSMAP),
              'payments': [
                  {
                      'type_code': pay_node.findtext("./ram:TypeCode", namespaces=CDAR_NSMAP),
                      'value_amount': pay_node.findtext("./ram:ValueAmount", namespaces=CDAR_NSMAP),
                      'value_amount_currency': n.get("currencyID") if (n := pay_node.find("./ram:ValueAmount", namespaces=CDAR_NSMAP)) is not None else None,
                      'value_percent': pay_node.findtext("./ram:ValuePercent", namespaces=CDAR_NSMAP),
                  }
                  for pay_node in node.findall("./ram:SpecifiedDocumentCharacteristic", namespaces=CDAR_NSMAP)
              ],
              'note': "\n".join([
                  note
                  for note_node in node.findall("./ram:IncludedNote", namespaces=CDAR_NSMAP)
                  if (note := self._pdp_parse_included_note(note_node))
              ]),
            } for node in status_nodes
        ] if status_nodes is not None else []

        return {
            'process_condition_code': process_condition_code,
            'response_code': PROCESS_CONDITION_CODE_TO_RESPONSE_CODE.get(process_condition_code, process_condition_code),
            'issue_date': _parse_cdar_datetime_node(xml_node.find("rsm:AcknowledgementDocument/ram:IssueDateTime/udt:DateTimeString", namespaces=CDAR_NSMAP)),
            'status_infos': status_infos,
        }

    @api.model
    def _format_payment_info(self, info, separator='\n'):
        type_code = info.get('type_code')
        type_string = PAYMENT_TYPE_CODES.get(type_code)
        value_amount = info.get('value_amount')
        value_amount_currency = info.get('value_amount_currency')
        value_percent = info.get('value_percent')

        infos = []
        if type_code and type_string:
            infos.append(f"[{type_code}] {type_string}")
        elif type_code:
            infos.append(f"[{type_code}]")
        if value_amount and value_percent:
            infos.append(self.env._("%(amount)s %(currency_code)s (including %(tax_percent)s%% VAT)",
                                    amount=value_amount, currency_code=value_amount_currency, tax_percent=value_percent))
        elif value_amount:
            infos.append(self.env._("%(amount)s %(currency_code)s", amount=value_amount, currency_code=value_amount_currency))

        return separator.join(infos)

    @api.model
    def _format_status_info(self, status, separator='\n'):
        reason_code = status.get('reason_code')
        reason = status.get('reason')
        note = status.get('note')

        infos = []
        # Reason
        if reason_code and reason:
            infos.append(f"[{reason_code}] {reason}")
        elif reason_code:
            infos.append(f"[{reason_code}]")
        elif reason:
            infos.append(reason)
        # Note
        if note:
            infos.append(note)
        # Payments
        payments = status.get('payments')
        if payments:
            infos.append(self.env._("Payment Info:"))
            for payment in payments:
                infos.append(self._format_payment_info(payment, separator=separator))

        return separator.join(infos)

    def _peppol_get_filetype(self, content):
        if content['document_type'] == 'Factur-X':
            return "pdf", "application/pdf"
        return super()._peppol_get_filetype(content)

    # -------------------------------------------------------------------------
    # CRONS
    # -------------------------------------------------------------------------

    def _cron_pdp_get_new_regulatory_documents(self):
        edi_users = self.search([('company_id.account_peppol_proxy_state', '=', 'receiver'), ('proxy_type', '=', 'pdp')])
        edi_users._pdp_get_new_regulatory_documents()
