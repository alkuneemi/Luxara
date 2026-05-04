from datetime import datetime

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import html2plaintext

from odoo.addons.l10n_fr_pdp.models.account_edi_proxy_user import STATUS_TO_PROCESS_CONDITION_CODE
from odoo.addons.l10n_fr_pdp.models.account_edi_xml_ubl_21_fr import PDP_CUSTOMIZATION_ID


class AccountMove(models.Model):
    _inherit = 'account.move'

    peppol_move_state = fields.Selection(
        selection_add=[
            ('submitted', 'Submitted'),
            ('received', 'Received'),
            ('made_available', 'Made Available'),
            ('approved', 'Approved'),
            ('refused', 'Refused'),
            ('partially_paid', 'Partially Paid'),
            ('paid', 'Paid'),
            ('rejected', 'Rejected'),
            ('cancelled', 'Cancelled'),
        ],
    )
    pdp_ppf_move_state = fields.Selection(
        selection=[
            ('in_progress', 'In Progress'),
            ('sent', 'Sent'),
            ('done', 'Done'),
            ('error', 'Error'),
        ],
        compute='_compute_ppf_state',
        store=True,
        string='PPF Invoice Status',
        copy=False,
    )
    pdp_ppf_lifecycle_state = fields.Selection(
        selection=[
            ('in_progress', 'In Progress'),
            ('sent', 'Sent'),
            ('done', 'Done'),
            ('error', 'Error'),
        ],
        compute='_compute_ppf_state',
        store=True,
        string='PPF Lifeycle Status',
        copy=False,
    )
    pdp_can_send_response = fields.Boolean(compute='_compute_pdp_can_send_response')

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        # Extend to rename the `peppol_move_state` field for French companies (to not say "Peppol")
        fields = super().fields_get(allfields, attributes)
        company = self.env.company
        if not self._context.get("studio") and (company.country_code == 'FR' or company.pdp_identifier) and 'peppol_move_state' in fields:
            fields['peppol_move_state']['string'] = self.env._("E-Invoicing Status")
        return fields

    def _get_view(self, view_id=None, view_type='form', **options):
        # Extend to rename the `peppol_ready` and `peppol_move_state` filters for French companies (to not say "Peppol")
        arch, view = super()._get_view(view_id, view_type, **options)
        company = self.env.company
        if (
            self._context.get("studio")
            or view_type != 'search'
            or not self.env['account.move'].has_access('read')
            or (company.country_code != 'FR' and not company.pdp_identifier)
        ):
            return arch, view

        peppol_move_state_filter_node = arch.find('.//filter[@name="peppol_move_state"]')
        if peppol_move_state_filter_node is not None:
            peppol_move_state_filter_node.set('string', "E-Invoicing Status")

        peppol_ready_filter_node = arch.find('.//filter[@name="peppol_ready"]')
        if peppol_ready_filter_node is not None:
            peppol_ready_filter_node.set('string', "E-Invoicing Ready")
        return arch, view

    @api.depends('peppol_is_sent')
    def _compute_show_reset_to_draft_button(self):
        # EXTEND 'account' to hide the reset to draft button for sent PDP moves
        super()._compute_show_reset_to_draft_button()
        self.filtered(lambda m: m.peppol_is_sent and m.company_id._get_peppol_proxy_type() == 'pdp').show_reset_to_draft_button = False

    @api.depends('peppol_response_ids', 'peppol_response_ids.peppol_state')
    def _compute_peppol_move_state(self):
        super()._compute_peppol_move_state()
        for move in self:
            # Handle sale and purchase documents in case we sent / received the document.
            if move.peppol_move_state != 'error' and (response_status := move._pdp_get_response_status()):
                move.peppol_move_state = response_status

    @api.depends('peppol_response_ids', 'peppol_response_ids.peppol_state', 'peppol_response_ids.response_code')
    def _compute_ppf_state(self):
        for move in self:
            processed = move.peppol_move_state not in ('ready', 'to_send', 'processing', 'error')
            move.pdp_ppf_move_state = move._pdp_get_tax_extract_state() if processed and move.is_sale_document(include_receipts=False) else False
            move.pdp_ppf_lifecycle_state = move._pdp_get_lifecycle_state() if processed else False

    @api.depends('peppol_move_state', 'peppol_message_uuid')
    def _compute_pdp_can_send_response(self):
        for move in self:
            move.pdp_can_send_response = bool(move.peppol_message_uuid) and move.peppol_is_sent

    def _pdp_get_response_status(self):
        """Return the PDP response status of the message"""
        self.ensure_one()
        # Non-PDP messages do not have a response status
        if not self.peppol_message_uuid:
            return None

        # Take the latest response status if we have any
        response_message = self.peppol_response_ids.filtered(lambda l: l.pdp_flow_number == '2' and l.peppol_state == 'done')
        latest_response = response_message.sorted(
            lambda l: (STATUS_TO_PROCESS_CONDITION_CODE.get(l.response_code, '0'), l.pdp_issue_date or datetime.min, l.id), reverse=True
        )[:1]
        if latest_response:
            return latest_response.response_code if latest_response.response_code != 'paid' or latest_response.pdp_fully_paid else 'partially_paid'

        return None

    def _pdp_get_tax_extract_state(self):
        self.ensure_one()
        if not self.peppol_message_uuid or not self.peppol_is_sent:
            return False
        tax_extract_responses = self.peppol_response_ids.filtered(lambda l: l.pdp_flow_number == '1' and l.peppol_state == 'done')
        if not tax_extract_responses:
            return 'in_progress'
        states = tax_extract_responses.mapped('response_code')
        if ('refused', 'rejected') in states:
            state = 'error'
        elif 'approved' not in states:
            state = 'sent'
        else:
            state = 'done'
        return state

    def _pdp_get_lifecycle_state(self):
        self.ensure_one()
        if not self.peppol_message_uuid or not self.peppol_is_sent:
            return False
        current_status_responses = self.peppol_response_ids.filtered(lambda l: l.pdp_flow_number == '6')
        if not current_status_responses:
            return 'in_progress' if self.is_sale_document(include_receipts=False) else False
        states = current_status_responses.mapped('response_code')
        if ('refused', 'rejected') in states:
            return 'error'
        return 'sent'

    def _l10n_fr_pdp_get_default_notes(self):
        self.ensure_one()
        # Mandatory / default notes for French e-invoicing [BR-FR-05]
        payment_term = self.invoice_payment_term_id
        return {
            'PMT': self.env._("In the event of late payment, a flat-rate fee of €40 for collection costs will be charged (Articles L.441-10 and D.441-5 of the Code de commerce)."),
            'PMD': self.env._("Late payment penalties at an annual rate of 10% are applied if the payment is made after the due date."),
            'AAB': html2plaintext(payment_term.note) if payment_term.early_discount else self.env._("No discount for early payment."),
        }

    @api.model
    def _get_ubl_cii_builder_from_xml_tree(self, tree):
        # Extends account_edi_ubl_cii
        customization_id = tree.find('{*}CustomizationID')
        # Note: The CustomizationID alone is not enough because e.g. SuperPDP just sends `urn:cen.eu:en16931:2017`
        #       but still expects the full French validation.
        if customization_id is not None and customization_id.text == PDP_CUSTOMIZATION_ID:
            receiver_endpoint_node = tree.find('./{*}AccountingCustomerParty/{*}Party/{*}EndpointID')
            if receiver_endpoint_node is not None and receiver_endpoint_node.get('schemeID') == '0225':
                return self.env['account.edi.xml.ubl_21_fr']
        return super()._get_ubl_cii_builder_from_xml_tree(tree)

    def action_pdp_open_response_wizard(self):
        if not (pdp_moves := self.filtered('pdp_can_send_response')):
            raise UserError(self.env._("Cannot send response for any of the journal entries."))
        wizard = self.env['pdp.response.wizard'].create({'move_ids': pdp_moves.ids})
        return wizard._get_records_action(name=self.env._("Send Response Message"), target='new')
