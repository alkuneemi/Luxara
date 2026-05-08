import base64
import calendar
import json
import logging
import re
import uuid

from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import Command, _, api, fields, models, tools
from odoo.exceptions import UserError

from ..utils.vat import is_valid_vat

_logger = logging.getLogger(__name__)

# Blocking rejection codes from Flux 10 v1.2 specification (Tableau 14)
# REJ_UNI is handled separately as duplicate acknowledgement (G8.05).
REJECTION_CODES = {
    'REJ_PER',  # Contrôle du format/période
    'REJ_COH',  # Contrôle de cohérence
}
DUPLICATE_ACK_CODES = {
    'REJ_UNI',  # Contrôle d'unicité (treated as duplicate transmission)
}
PDP_INTERFACE_CODE = 'FFE1025A'
PDP_APP_CODE_QUAL = 'PPF262'  # ODOO raccordement EDI QUAL
PDP_APP_CODE_PROD = 'PDP257'  # ODOO raccordement EDI PROD
PDP_APP_CODE_FALLBACK_QUAL = 'PPF000'
PDP_APP_CODE_FALLBACK_PROD = 'PDP000'
PDP_FILENAME_ID_LENGTH = 19
# ready ──> sent ┬─> completed
#             ^  └─> error ─┐
#             └─────────────┘
FLOW_OPEN_STATES_SELECTION = [
    ('ready', 'Ready'),
    ('error', 'Error'),
]
FLOW_SENT_STATES_SELECTION = [
    ('sent', 'Sent'),
    ('completed', 'Completed')
]  # once a flow is sent, sent move_id's and xml payload must stay immutable
FLOW_OPEN_STATES = tuple(dict(FLOW_OPEN_STATES_SELECTION))
FLOW_SENT_STATES = tuple(dict(FLOW_SENT_STATES_SELECTION))


class PdpFlow(models.Model):
    _name = 'l10n.fr.pdp.reports.flow'
    _description = 'French PDP Flow'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char()
    state = fields.Selection(
        selection=FLOW_OPEN_STATES_SELECTION + FLOW_SENT_STATES_SELECTION,
        string="Status",
        required=True,
        default='ready',
    )
    payload_id = fields.Many2one('ir.attachment', string="XML Payload", compute='_compute_payload_attachment')
    transport_identifier = fields.Char(help="Identifier returned by the PDP transport API.")
    transport_status = fields.Char(help="Raw status returned by the PDP transport API.")
    transport_message = fields.Text(help="Additional message or error returned by the PDP transport API.")
    report_type = fields.Selection(
        selection=[('transaction', "Transaction"), ('payment', "Payment")],
        required=True,
        default='transaction',
    )
    operation_type = fields.Selection(
        selection=[('sale', "Sales"), ('purchase', "Acquisitions")],
        required=True,
        default='sale',
        help="Defines whether the flow reports sales or acquisition transactions.",
    )
    transmission_type = fields.Selection(
        selection=[('initial', "Initial"), ('rectificative', "Rectificative")],
        help="Type of flow transmission.",
        compute='_compute_transmission_type',
    )
    initial_flow_id = fields.Many2one(comodel_name='l10n.fr.pdp.reports.flow')
    rectificative_flow_ids = fields.One2many(comodel_name='l10n.fr.pdp.reports.flow', inverse_name='initial_flow_id')
    tracking_id = fields.Char(help="External tracking identifier sent to the Flow Service.")
    period_start = fields.Date(required=True)
    period_end = fields.Date(required=True)
    due_date = fields.Date(required=True)
    periodicity_code = fields.Char()
    last_send_datetime = fields.Datetime(string="Last Send On")
    send_datetime = fields.Datetime(string="Sent On")
    acknowledgement_status = fields.Selection(
        selection=[('pending', "Pending"), ('ok', "Accepted"), ('error', "Error")],
        string="Last Known Status",
        default='pending',
    )
    acknowledgement_details = fields.Json()
    company_id = fields.Many2one(
        comodel_name='res.company',
        string="Company",
        required=True,
        default=lambda self: self.env.company,
    )
    move_ids = fields.Many2many(
        comodel_name='account.move',
        help="Invoices/Payments reported in this flow.",
        compute='_compute_move_ids',
    )
    error_moves_count = fields.Integer(compute='_compute_move_ids')
    error_move_message = fields.Text(string="Invalid Invoice Details")
    period_status = fields.Selection(
        selection=[('open', "Open"), ('grace', "Grace"), ('closed', "Closed")],
        string="Period Status",
        compute='_compute_period_status',
        help="Current status of the reporting period: Open (before grace), Grace (can send), Closed (after deadline).",
    )

    # -------------------------------------------------------------------------
    # Compute Methods
    # -------------------------------------------------------------------------

    def _compute_move_ids(self):
        # get all the moves for which this is the orignial flow but also all the moves linked to any flow with same scope
        for flow in self:
            if flow.initial_flow_id:
                # flow is rectificative, get it's initial flow and all rectificative flows
                all_flows = flow.initial_flow_id + flow.initial_flow_id.rectificative_flow_ids
            else:
                # flow is initial, get itself & rectificative flows
                all_flows = flow + flow.rectificative_flow_ids
            self.move_ids = self.env['account.move'].search([('l10n_fr_pdp_original_flow_id', 'in', all_flows.ids)])
            self.error_moves_count = self.env['account.move'].search_count([
                ('l10n_fr_pdp_original_flow_id', 'in', all_flows.ids),
                ('l10n_fr_pdp_status', '=', 'error'),
            ])

    def _compute_payload_attachment(self):
        """Compute the payload attachment record linked to this flow."""
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', self._name),
            ('res_id', 'in', self.ids),
            ('mimetype', '=', 'application/xml'),
        ], order='id desc')
        attachments_map = {attachment.res_id: attachment for attachment in attachments}
        for flow in self:
            flow.payload_id = attachments_map.get(flow.id)

    @api.depends('period_end', 'due_date')
    def _compute_period_status(self):
        """Compute the current status of the reporting period."""
        today = fields.Date.context_today(self)
        for flow in self:
            if today <= flow.period_end:
                flow.period_status = 'open'
            elif today < flow.due_date:
                flow.period_status = 'grace'
            else:
                flow.period_status = 'closed'

    @api.depends('initial_flow_id')
    def _compute_transmission_type(self):
        for flow in self:
            flow.transmission_type = 'rectificative' if flow.initial_flow_id else 'initial'

    # -------------------------------------------------------------------------
    # CRUD Methods
    # -------------------------------------------------------------------------

    # def unlink(self):
    #     if any(flow.state in FLOW_SENT_STATES for flow in self):
    #         raise UserError(_("You cannot delete flows that have been sent."))
    #     return super().unlink()

    # -------------------------------------------------------------------------
    # Business Methods - Validation
    # -------------------------------------------------------------------------

    @api.model
    def _get_open_flow_and_create_if_needed(self, move, report_type):
        """ This returns a flow that meets the move scope and that is open.
        It creates a new initial flow or a rectificative flow if needed.
        """
        if not report_type:
            return
        period_data = self._get_period_flow_properties(move.company_id, move.date, report_type)


        scope = {
            'company_id': move.company_id.id,
            'period_start': period_data['period_start'],
            'period_end': period_data['period_end'],
            'operation_type': 'sale' if move.is_sale_document(include_receipts=True) else 'purchase',
            'report_type': report_type,
        }

        existing_flows = self.search(
            domain=[(key, '=', value) for key, value in scope.items()],
            order='id',
        )
        # If last flow is sent, create a new rectificative one.
        is_rectificative = existing_flows and existing_flows[-1].state in FLOW_SENT_STATES

        if not existing_flows or is_rectificative:
            name = f'{period_data['period_start']} - {period_data['period_end']} - {report_type} - {'rect.' if is_rectificative else 'init.'}'
            existing_flows += self.create([{
                **scope,
                'name': '',
                'due_date': period_data['due_date'],
                'initial_flow_id': existing_flows[0].id if is_rectificative else None,
            }])

        return existing_flows[-1]

    def _get_move_validation_errors(self, move):
        """Return list of validation errors for a move, empty if valid."""
        errors = []
        company_partner = move.company_id.partner_id.commercial_partner_id
        company_vat = company_partner.vat
        company_country = company_partner.country_id.code
        if (
            move.state == 'posted'
            and move.is_sale_document(include_receipts=True)
            and not move.is_move_sent
            # and move.partner_id.commercial_partner_id.vat  # TBC, B2C: may not have enough info to send invoice
        ):
            errors.append(_("Invoice/credit note has not been sent to the customer."))
        if move._get_l10n_fr_pdp_transaction_type() == 'b2bi':
            partner = move.commercial_partner_id
            vat = partner.vat
            country_code = partner.country_id.code
            if not vat:
                errors.append(_("Missing buyer VAT."))
            elif not is_valid_vat(vat, country_code):
                errors.append(_("Invalid buyer VAT (%(vat)s).", vat=vat))
            if not company_vat:
                requires_tt122 = self._requires_fiscal_representative_vat(move)
                representative_vat = (move.company_id.l10n_fr_pdp_fiscal_representative_vat or '').strip()
                if requires_tt122:
                    if not representative_vat:
                        errors.append(_("Missing seller fiscal representative VAT (TT-122)."))
                    elif not is_valid_vat(representative_vat, company_country):
                        errors.append(_("Invalid seller fiscal representative VAT (%(vat)s).", vat=representative_vat))
                else:
                    errors.append(_("Missing seller VAT."))
            # elif not is_valid_vat(company_vat, company_country):
            #     errors.append(_("Invalid seller VAT (%(vat)s).", vat=company_vat))
        if move.is_purchase_document() and move._is_b2bi_partner_for_purchase():
            supplier = move.commercial_partner_id
            supplier_vat = supplier.vat
            supplier_country = supplier.country_id.code
            if not supplier_vat:
                errors.append(_("Missing supplier VAT."))
            elif not is_valid_vat(supplier_vat, supplier_country):
                errors.append(_("Invalid supplier VAT (%(vat)s).", vat=supplier_vat))
            if not company_vat:
                errors.append(_("Missing buyer VAT."))
            elif not is_valid_vat(company_vat, company_country):
                errors.append(_("Invalid buyer VAT (%(vat)s).", vat=company_vat))
        return errors

    def _requires_fiscal_representative_vat(self, move):
        """Return True when TT-122 fallback can apply for the seller on this move."""
        self.ensure_one()
        if move._get_l10n_fr_pdp_transaction_type() != 'b2bi':
            return False
        taxes = move.invoice_line_ids.filtered(lambda line: line.display_type == 'product').mapped('tax_ids')
        return any((tax.l10n_fr_pdp_vatex_code or '').strip() for tax in taxes)


    # -------------------------------------------------------------------------
    # Business Methods - Payload Building
    # -------------------------------------------------------------------------

    def _build_payload(self, valid_moves=None):
        # TODO: untangle this, 'buil_payload' should only build payload ...
        """Build single XML payload for the entire flow period."""
        for flow in self:
            if flow.state not in FLOW_OPEN_STATES:
                raise UserError(_("Flow %(name)s has already been sent.", name=flow.name))
            flow._ensure_tracking_id()

            if not valid_moves:
                valid_moves = flow.move_ids.filtered(lambda move: move.l10n_fr_pdp_status not in {'out_of_scope', 'error'})

            if not valid_moves:
                flow._message_post_once(_("Payload build failed: no valid invoices."))
                continue

            payload = self.env['pdp.flow.10.xml.builder']._build_payload(flow, valid_moves)
            filename = flow._build_filename()

            if flow.payload_id:
                flow.payload_id.unlink()
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'datas': payload,
                'res_model': flow._name,
                'res_id': flow.id,
                'type': 'binary',
                'mimetype': 'application/xml',
            })
            flow.payload_id = attachment

            # Log build completion
            error_moves_len = len(valid_moves) < len(flow.move_ids)
            if error_moves_len:
                flow._message_post_once(_(
                    "Payload built with %(valid)s valid invoice(s) and %(invalid)s error(s).",
                    valid=len(valid_moves),
                    invalid=lerror_moves_len,
                ))
            else:
                flow._message_post_once(_(
                    "Payload built successfully with %(count)s invoice(s).",
                    count=len(valid_moves),
                ))


    # -------------------------------------------------------------------------
    # Business Methods - Sending
    # -------------------------------------------------------------------------

    def action_send(self):
        """Send flow payload to transport gateway."""
        # TODO if a flow is rectificative, only send if previous flow is complete
        for flow in self:
            flow._ensure_tracking_id()
            ignore_errors = self.env.context.get('ignore_error_invoices')

            if flow.state != 'ready':
                continue
            valid_moves = flow.move_ids.filtered(lambda move: move.l10n_fr_pdp_status not in {'out_of_scope', 'error'})
            
            if not valid_moves:
                continue

            flow._build_payload(valid_moves)

            # Send single payload to proxy.
            response = flow._send_to_proxy()
            transport_state = flow._map_transport_status(response)
            ack_status, flow_state, ack_details, transport_status, rejected_move_ids = flow._process_acknowledgement(response, transport_state)
            send_datetime = fields.Datetime.now()
            write_vals = {
                'transport_identifier': response.get('id'),
                'transport_status': transport_status or response.get('status'),
                'transport_message': response.get('message'),
                'state': flow_state,
                'last_send_datetime': send_datetime,
                'send_datetime': send_datetime if flow_state in FLOW_SENT_STATES else flow.send_datetime,
                'acknowledgement_status': ack_status,
                'acknowledgement_details': ack_details,
            }


            # Update flow with transport response
            flow.write(write_vals)


            flow._upsert_transport_response_attachment({
                'transport': response,
                'acknowledgement_status': ack_status,
                'acknowledgement_details': ack_details or [],
                'state': flow_state,
                'sent_at': fields.Datetime.to_string(send_datetime),
            })

            # Post audit messages on sent moves
            if flow_state in FLOW_SENT_STATES:
                flow._post_sent_message_on_moves(valid_moves)

            # Log send result
            flow._message_post_once(_(
                "Flow sent: status %(status)s, transport %(transport)s. %(details)s",
                status=flow_state,
                transport=response.get('id') or _("n/a"),
                details=response.get('message') or '',
            ))
        return True

    def _post_sent_message_on_moves(self, moves):
        """Post audit message on successfully sent moves."""
        self.ensure_one()
        flow_link = Markup('<a href="/web#id=%s&amp;model=l10n.fr.pdp.reports.flow&amp;view_type=form">%s</a>') % (self.id, self.name)
        body = _("E-reports %s sent", flow_link)
        for move in moves:
            move.message_post(body=body, subtype_xmlid='mail.mt_note')

    def _get_pdp_proxy_user(self):
        self.ensure_one()
        proxy_user = self.company_id.account_peppol_edi_user
        if not proxy_user:
            raise UserError(_(
                "No active PDP proxy user is configured for company %(company)s.",
                company=self.company_id.display_name,
            ))
        return proxy_user

    def _send_to_proxy(self):
        self.ensure_one()
        if not self.payload_id:
            raise UserError(_("The flow payload is missing. Build the payload before sending."))
        proxy_user = self._get_pdp_proxy_user()
        payload_doc = {
            'flow_number': 10,
            'filename': self.payload_id.name,
            'ubl': self.payload_id.raw.decode(),
            'external_ref': self.tracking_id,
        }
        # if not proxy_user:
        #     # Keep local test runs deterministic without requiring a remote proxy setup.
        #     return {
        #         'id': str(uuid.uuid4()),
        #         'flow_id': self.tracking_id,
        #         'status': 'DRAFT',
        #         'message': _("PDP proxy mocked in test mode."),
        #         'acknowledgement': [],
        #     }
        result = proxy_user._call_peppol_proxy(
            proxy_user._get_peppol_proxy_endpoint('send_document'),
            {'documents': [payload_doc]},
        )
        ppf_messages = result.get('ppf_messages') or []
        if not ppf_messages:
            raise UserError(_("The PDP proxy did not return a flow tracking identifier."))
        proxy_message = ppf_messages[0]
        return {
            'id': proxy_message.get('uuid') or proxy_message.get('flow_id'),
            'flow_id': proxy_message.get('flow_id'),
            'status': (proxy_message.get('state') or '').upper() or 'DRAFT',
            'message': result.get('message') or '',
            'acknowledgement': proxy_message.get('acknowledgement') or [],
        }

    def _map_transport_status(self, response):
        """Map API status to internal state."""
        raw_status = (response or {}).get('status', '').upper()
        mapping = {
            'ACCEPTED': 'completed',
            'DELIVERED': 'completed',
            'DONE': 'completed',
            'ERROR': 'error',
            'REFUSED': 'error',
            'DRAFT': 'sent',
            'PROCESSING': 'sent',
        }
        return mapping.get(raw_status, 'sent')

    def _normalize_invoice_reference(self, value):
        """Normalize references for resilient matching against acknowledgement payloads."""
        return re.sub(r'\s+', '', (value or '').strip().upper())

    def _extract_ack_invoice_reference(self, ack):
        """Extract one invoice reference from an acknowledgement entry when available."""
        keys = (
            'invoice_id',
            'invoice_reference',
            'invoice_number',
            'document_id',
            'document_reference',
            'reference',
            'id',
            'tt19',
        )
        for key in keys:
            value = ack.get(key)
            if isinstance(value, str) and value.strip():
                return value
        invoice_block = ack.get('invoice')
        if isinstance(invoice_block, dict):
            for key in keys:
                value = invoice_block.get(key)
                if isinstance(value, str) and value.strip():
                    return value
        return False

    def _extract_rejected_invoice_refs(self, acknowledgement_entries):
        """Return normalized invoice references explicitly rejected by acknowledgement entries."""
        rejected_refs = set()
        for ack in acknowledgement_entries:
            ref = self._extract_ack_invoice_reference(ack)
            if ref:
                rejected_refs.add(self._normalize_invoice_reference(ref))
        return rejected_refs

    def _match_moves_by_invoice_refs(self, moves, rejected_refs):
        """Match rejected references to move identifiers used in Flux 10 payloads."""
        # TODO: refactor status mechanism
        if not moves or not rejected_refs:
            return self.env['account.move']
        matched_moves = self.env['account.move']
        for move in moves:
            candidates = {
                # self._normalize_invoice_reference(move.l10n_fr_pdp_invoice_reference or ''),
                self._normalize_invoice_reference(move.name or ''),
                self._normalize_invoice_reference(move.ref or ''),  # TODO ref ????
            }
            if candidates.intersection(rejected_refs):
                matched_moves |= move
        return matched_moves

    def _process_acknowledgement(self, response, transport_state):
        """Derive acknowledgement status/state from gateway response."""

        # TODO update this to real flow
        return 'ok', 'sent', {}, {}, None

        # ack_list = (response or {}).get('acknowledgement') or []
        # # Default: stick to transport state and pending ack.
        # ack_status = 'pending'
        # state = transport_state
        # transport_status = False
        # rejected_move_ids = []
        # if not ack_list:
        #     return ack_status, state, False, transport_status, rejected_move_ids

        # # Detect rejection/duplicate acknowledgement codes per spec (Tableau 14)
        # rejection_entries = []
        # has_duplicate = False
        # for ack in ack_list:
        #     code = (ack.get('code') or ack.get('reason_code') or '').upper()
        #     if code in REJECTION_CODES:
        #         rejection_entries.append(ack)
        #     if code in DUPLICATE_ACK_CODES:
        #         has_duplicate = True

        # if rejection_entries:
        #     rejected_refs = self._extract_rejected_invoice_refs(rejection_entries)
        #     sent_moves = self.move_ids - self.error_move_ids
        #     rejected_moves = self._match_moves_by_invoice_refs(sent_moves, rejected_refs)
        #     if rejected_moves and len(rejected_moves) < len(sent_moves):
        #         # Rejet partiel: only impacted documents are marked as errors.
        #         ack_status = 'error'
        #         state = 'completed'
        #         transport_status = 'PARTIAL_REJECTED'
        #         rejected_move_ids = rejected_moves.ids
        #     else:
        #         # Rejet global (or unknown granularity): keep strict global error behavior.
        #         ack_status = 'error'
        #         state = 'error'
        # elif has_duplicate:
        #     # Duplicate transmission (G8.05): no business error, keep flow as completed.
        #     ack_status = 'ok'
        #     state = 'completed'
        #     transport_status = 'DUPLICATE'
        # else:
        #     ack_status = 'ok'
        #     # If transport returned only 'sent', upgrade to completed on positive ack.
        #     if state == 'sent':
        #         state = 'completed'

        # return ack_status, state, ack_list, transport_status, rejected_move_ids

    def _extract_proxy_poll_error_message(self, payload):
        """Extract a readable error message from proxy polling payload."""
        if not payload:
            return False
        if isinstance(payload, dict):
            return payload.get('message') or json.dumps(payload)
        if isinstance(payload, str):
            try:
                decoded = json.loads(payload)
            except ValueError:
                return payload
            if isinstance(decoded, dict):
                return decoded.get('message') or payload
            return payload
        return str(payload)

    def _map_proxy_polled_message(self, message):
        """Map generic proxy message polling payload to flow updates."""
        raw_state = (message.get('state') or '').strip().lower()
        transport_status = raw_state.upper() if raw_state else False
        if raw_state == 'done':
            return {
                'state': 'completed',
                'acknowledgement_status': 'ok',
                'transport_status': transport_status,
                'transport_message': False,
            }
        if raw_state == 'error':
            return {
                'state': 'error',
                'acknowledgement_status': 'error',
                'transport_status': transport_status,
                'transport_message': self._extract_proxy_poll_error_message(message.get('error')),
            }
        if raw_state in {'processing', 'draft'}:
            return {
                'state': 'sent',
                'acknowledgement_status': 'pending',
                'transport_status': transport_status,
            }
        return {
            'state': False,
            'acknowledgement_status': False,
            'transport_status': transport_status,
        }

    @api.model
    def _cron_sync_transport_statuses(self):
        """Poll proxy message states and synchronize flow transport statuses."""
        companies = self.env['res.company'].search([('l10n_fr_f10_enable_reporting', '=', True)])
        if not companies:
            return True

        for company in companies:
            flows = self.search([
                ('company_id', '=', company.id),
                ('transport_identifier', '!=', False),
                ('state', 'in', ('sent', 'completed', 'error')),
                '|',
                ('acknowledgement_status', '=', 'pending'),
                ('transport_status', 'in', ('DRAFT', 'PROCESSING', 'PARTIAL_REJECTED')),
            ])
            if not flows:
                continue
            try:
                proxy_user = flows[:1]._get_pdp_proxy_user()
                if not proxy_user:
                    continue
                response = proxy_user._call_peppol_proxy(
                    proxy_user._get_peppol_proxy_endpoint('get_all_documents'),
                    {'domain': {'direction': 'outgoing'}},
                )
                messages = response.get('messages') or []
                messages_by_uuid = {msg.get('uuid'): msg for msg in messages if msg.get('uuid')}
                ack_uuids = []

                for flow in flows:
                    message = messages_by_uuid.get(flow.transport_identifier)
                    if not message:
                        continue
                    mapped = flow._map_proxy_polled_message(message)
                    write_vals = {}
                    if mapped.get('transport_status'):
                        write_vals['transport_status'] = mapped['transport_status']
                    if mapped.get('transport_message') is not None:
                        write_vals['transport_message'] = mapped.get('transport_message')
                    target_state = mapped.get('state')
                    if target_state and not (flow.state in FLOW_SENT_STATES and target_state == 'sent'):
                        write_vals['state'] = target_state
                    ack_status = mapped.get('acknowledgement_status')
                    if ack_status and not (flow.acknowledgement_status in {'ok', 'error'} and ack_status == 'pending'):
                        write_vals['acknowledgement_status'] = ack_status

                    if not write_vals:
                        continue
                    flow.write(write_vals)
                    flow._log_cron_event(
                        _("Proxy status synchronized by cron (status: %(status)s).",
                          status=flow.transport_status or flow.state)
                    )
                    ack_uuids.append(flow.transport_identifier)

                if ack_uuids:
                    proxy_user._call_peppol_proxy(
                        proxy_user._get_peppol_proxy_endpoint('ack'),
                        {'message_uuids': sorted(set(ack_uuids))},
                    )
            except Exception:
                _logger.exception('Failed to synchronize PDP transport statuses for company %s', company.id)
        return True

    # -------------------------------------------------------------------------
    # Business Methods - Cron
    # -------------------------------------------------------------------------

    @api.model
    def _cron_send_ready_flows(self):
        """Cron job to send ready flows within their send window."""
        today = fields.Date.context_today(self)
        companies = self.env['res.company'].search([
            ('l10n_fr_f10_enable_reporting', '=', True),
            ('l10n_fr_pdp_send_mode', '=', 'auto'),
        ])
        if not companies:
            return True
        flows = self.search([('state', 'in', ('ready', 'error')), ('company_id', 'in', companies.ids)])
        for flow in flows:
            try:
                # IN sends within its window:
                # - no errors: send as soon as the window opens
                # - errors: send only on the last day (excluding invalid invoices)
                # RE sends immediately when ready.
                if flow.transmission_type == 'initial':
                    if today < flow.period_end:
                        continue
                    if flow.error_moves_count:
                        if today < flow.due_date:
                            continue
                        ctx = {'ignore_error_invoices': True}
                    else:
                        ctx = {}
                else:
                    # RE flows: send immediately when ready (no deadline constraint)
                    if flow.state != 'ready' or flow.error_moves_count:
                        continue
                    ctx = {}
                flow.with_context(**ctx).with_company(flow.company_id).sudo().action_send()
                flow._log_cron_event(
                    _("Flow automatically sent by cron (status: %(status)s). %(extra)s",
                      status=flow.transport_status or flow.state,
                      extra=_("Invalid invoices were excluded.") if flow.error_moves_count else ""),
                )
            except Exception:
                _logger.exception('Failed to send PDP flow %s during cron', flow.id)
        return True

    # -------------------------------------------------------------------------
    # Business Methods - Deadline Window
    # -------------------------------------------------------------------------

    @api.model
    def _get_period_flow_properties(self, company_id, date, report_type):
        """Return period start/end and due date for a given move date and report type."""

        def get_monthly_period(date):
            return date.replace(day=1), date.replace(day=last_month_day)

        def get_next_10th_due(date):
            return date.replace(day=10, month=(date.month + 1) % 12, year=date.year + (date.month // 12))

        def get_end_of_month_after(date):
            month = (date.month + 1) % 12,
            year = date.year + (date.month // 12)
            return date.replace(
                day=calendar.monthrange(year, month)[1],
                month=month,
                year=year
            )

        last_month_day = calendar.monthrange(date.year, date.month)[1]

        if company_id.l10n_fr_pdp_periodicity == 'normal_monthly':
            if report_type == 'transaction':
                if date.day <= 10:
                    period_start, period_end = date.replace(day=1), date.replace(day=10)
                    due_date = date.replace(day=20)
                elif date.day <= 20:
                    period_start, period_end = date.replace(day=11), date.replace(day=20)
                    due_date = date.replace(day=last_month_day)
                else:
                    period_start, period_end = date.replace(day=21), date.replace(day=last_month_day)
                    due_date = date.replace(day=10, month=(date.month + 1) % 12, year=date.year + (date.month // 12))
            else:
                period_start, period_end = get_monthly_period(date)
                due_date = get_next_10th_due(date)
        elif company_id.l10n_fr_pdp_periodicity == 'normal_quarterly':
            period_start, period_end = get_monthly_period(date)
            due_date = get_next_10th_due(date)
        elif company_id.l10n_fr_pdp_periodicity == 'simplified_monthly':
            period_start, period_end = get_monthly_period(date)
            due_date = get_end_of_month_after(period_end)
        else:  # simplified_bimonthly
            period_start = date.replace(month=date.month - (date.month - 1) % 2, day=1)
            period_end = date.replace(
                month=period_start.month+1,
                day=calendar.monthrange(date.year, period_start.month+1)[1]
            )
            due_date = get_end_of_month_after(period_end)

        return {'period_start': period_start, 'period_end': period_end, 'due_date': due_date}

    def _is_last_send_day(self):
        """Check if today is the last day of the send window."""
        self.ensure_one()
        today = fields.Date.context_today(self)
        return (self.due_date - relativedelta(days=1)) < today <= self.due_date


    # -------------------------------------------------------------------------
    # Business Methods - Tracking & Naming
    # -------------------------------------------------------------------------

    def _ensure_tracking_id(self):
        """Generate or normalize tracking ID."""
        reserved_ids = set()
        for flow in self.sorted('id'):
            flow.tracking_id = flow.tracking_id or flow._generate_tracking_id()

    def _generate_tracking_id(self):
        """Generate unique tracking ID from company and flow attributes."""
        self.ensure_one()
        return str(uuid.uuid4())  # TODO -> header will be gen in PA
        # company = self.company_id
        # siren = (company.siret or '')[:9]
        # reporting_token = self._format_date(self.period_end or self.reporting_date) if (self.period_end or self.reporting_date) else fields.Date.context_today(self)
        # currency = self.currency_id or company.currency_id
        # parts = [
        #     siren or str(company.id),
        #     (self.report_type or '')[:3],
        #     (self.operation_type or '')[:1],
        #     (self.transaction_type or '')[:3],
        #     (currency.name if currency else '')[:3],
        #     ('RE' if self.transmission_type == 'rectificative' else 'IN'),
        #     str(reporting_token),
        # ]
        # return self._sanitize_token('_'.join(p for p in parts if p), default='TRACKING').upper()

    def _get_application_code(self):
        """Return PDP application code for EDI naming rules."""
        is_qual = self.env['ir.config_parameter'].sudo().get_param('l10n_fr_pdp.edi.mode', '') == 'test'
        code = PDP_APP_CODE_QUAL if is_qual else PDP_APP_CODE_PROD
        if not code:
            code = PDP_APP_CODE_FALLBACK_QUAL if is_qual else PDP_APP_CODE_FALLBACK_PROD
        return self._sanitize_token(code, default='APP').upper()

    def _build_filename_identifier(self):
        """Build 19-character alphanumeric identifier for EDI filenames."""
        self.ensure_one()
        self._ensure_tracking_id()
        base = self.tracking_id or uuid.uuid4().hex
        token = re.sub(r'[^A-Za-z0-9]+', '', base).upper()
        if len(token) < PDP_FILENAME_ID_LENGTH:
            # Generate additional alphanumeric characters from UUID to reach required length
            additional = uuid.uuid4().hex.upper()
            token = (token + additional)[:PDP_FILENAME_ID_LENGTH]
        return token[:PDP_FILENAME_ID_LENGTH]

    def _sanitize_token(self, value, default='FLOW'):
        """Clean token for use in filenames and identifiers."""
        value = (value or '').strip()
        if not value:
            return default
        # remove non-alphanumeric characters
        return re.sub(r'[^A-Za-z0-9_]+', '_', value)[:50] or default

    def _update_reference_name(self):
        """Set human-readable flow name based on period."""
        for flow in self:
            date_ref = flow.period_start or flow.reporting_date
            if not date_ref:
                continue
            date_ref = fields.Date.to_date(date_ref)

            # Type (Transaction/Acquisition/Payment)
            if flow.report_type == 'payment':
                flow_type = _("Payment")
            elif flow.operation_type == 'purchase':
                flow_type = _("Acquisition")
            else:
                flow_type = _("Transaction")

            # Date format: MM/YYYY with optional Decade
            date_str = f"{date_ref.strftime('%m')}/{date_ref.strftime('%Y')}"
            if flow.periodicity_code == 'D':
                day = date_ref.day
                decade = 1 if day <= 10 else (2 if day <= 20 else 3)
                date_str = f"{date_str} Décade {decade}"

            # Transmission type (v1.2: IN or RE only)
            trans_type = _("Rectificative") if flow.transmission_type == 'rectificative' else _("Initial")

            # Format: Type - Date - Transmission Type
            flow.name = f"{flow_type} - {date_str} - {trans_type}"

    def _build_filename(self, extension='xml'):
        """Generate EDI-compliant filename for payload."""
        self.ensure_one()
        self._ensure_tracking_id()
        app_code = self._get_application_code()
        flow_id = self._build_filename_identifier()
        return f'{PDP_INTERFACE_CODE}_{app_code}_{app_code}{flow_id}.{extension}'

    # -------------------------------------------------------------------------
    # Business Methods - Utilities
    # -------------------------------------------------------------------------

    def _message_post_once(self, body, subtype='mail.mt_note'):
        """Post message if it differs from the last one to avoid chatter spam."""
        self.ensure_one()
        last_body = self.message_ids[:1].body if self.message_ids else None
        if last_body == body:
            return
        self.message_post(body=body, subtype_xmlid=subtype)

    def _upsert_transport_response_attachment(self, response_payload):
        """Create or replace the JSON attachment containing latest transport response."""
        self.ensure_one()
        Attachment = self.env['ir.attachment']
        base_name = self.payload_id.name or self.name or f"flow_{self.id}.xml"
        filename = (
            f"{base_name[:-4]}_transport_response.json"
            if base_name.lower().endswith('.xml')
            else f"{base_name}_transport_response.json"
        )
        datas = base64.b64encode(
            json.dumps(response_payload or {}, ensure_ascii=False, indent=2).encode('utf-8')
        )
        existing = Attachment.search([
            ('res_model', '=', 'l10n.fr.pdp.reports.flow'),
            ('res_id', '=', self.id),
            ('name', '=', filename),
            ('mimetype', '=', 'application/json'),
        ], limit=1, order='id desc')
        vals = {
            'name': filename,
            'datas': datas,
            'res_model': 'l10n.fr.pdp.reports.flow',
            'res_id': self.id,
            'type': 'binary',
            'mimetype': 'application/json',
        }
        if existing:
            existing.write(vals)
        else:
            Attachment.create(vals)

    def _is_valid_due_date_code(self, code):
        """Validate TT-64 due date type code."""
        return bool(code and code.isdigit() and len(code) <= 3)

    def _get_transaction_category_code(self, transaction_type):
        """Return category code for transaction type."""
        return 'TPS1' if transaction_type == 'b2bi' else 'TLB1'  # Flux 10 category codes: TPS1=B2BI, TLB1=B2C

    def _log_cron_event(self, message):
        """Post message to flow chatter."""
        for flow in self:
            flow._message_post_once(message)

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------

    def action_build_payload_manual(self):
        """Manual trigger for payload building."""
        self._ensure_tracking_id()
        self._build_payload()
        _logger.info('Manual payload build triggered for flows: %s', self.ids)
        return True

    def action_send_from_ui(self):
        """Send flow from UI with error checking."""
        self._ensure_tracking_id()
        ctx = dict(self.env.context)
        for flow in self:
            if flow.error_moves_count and not (ctx.get('ignore_error_invoices') or flow._is_last_send_day()):
                raise UserError(_(
                    "This flow still contains invoices with validation errors. "
                    "Fix them or use the 'Send without invalid invoices' button.",
                ))
        _logger.info('Manual transport submission triggered for flows: %s', self.ids)
        return self.with_context(ctx).action_send()

    def action_send_ignore_errors(self):
        """Send flow ignoring error invoices."""
        return self.with_context(ignore_error_invoices=True).action_send_from_ui()


    def _action_open_moves(self, domain, name, context=None):
        """Helper to open list view of account moves.

        Args:
            moves: Recordset of account.move to display
            name: Window title
            context: Optional context dict

        Returns:
            dict: Action to open moves list view
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'list,form',
            'domain': domain,
            'name': name,
            'context': context or {},
        }

    def action_view_error_moves(self):
        """Open list view of invalid invoices."""
        return self._action_open_moves(
            [
                ('id', 'in', self.move_ids.ids),
                ('l10n_fr_pdp_status', '=', 'error')
            ],
            _("Invalid Invoices"),
        )

    def action_open_send_wizard(self):
        """Open send wizard if errors exist, otherwise send directly."""
        self.ensure_one()
        if not self.error_moves_ids:
            return self.action_send_from_ui()
        view = self.env.ref('l10n_fr_pdp_reports.l10n_fr_pdp_reports_view_send_wizard_form', raise_if_not_found=False)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'l10n.fr.pdp.reports.send.wizard',
            'view_mode': 'form',
            'view_id': view.id if view else False,
            'target': 'new',
            'context': {'default_flow_id': self.id},
        }

    def action_view_moves(self):
        """Open list view of related invoices."""
        return self._action_open_moves(
            [('id', 'in', self.move_ids.ids)],
            _("Related Invoices"),
            {'create': False, 'group_by': ['move_type']},
        )
