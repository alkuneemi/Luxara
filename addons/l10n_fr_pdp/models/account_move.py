from datetime import datetime

from odoo import api, fields, models
from odoo.exceptions import UserError

from odoo.addons.account_peppol.models.account_move import UNSENT_PEPPOL_MOVE_STATES
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
            ('paid', 'Paid'),
            ('rejected', 'Rejected'),
            ('cancelled', 'Cancelled'),
        ],
    )
    ppf_move_state = fields.Selection(
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
    ppf_lifecycle_state = fields.Selection(
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
    pdp_response_ids = fields.One2many('pdp.response', 'move_id')
    pdp_can_send_response = fields.Boolean(compute='_compute_pdp_can_send_response')

    @api.depends('pdp_response_ids', 'pdp_response_ids.pdp_state')
    def _compute_peppol_move_state(self):
        for move in self:
            # Handle sale and purchase documents in case we sent / received the document.
            if move.peppol_move_state != 'error' and (response_status := move._pdp_get_response_status()):
                move.peppol_move_state = response_status
                continue

            if not move.is_sale_document(include_receipts=True):
                continue
            # Handle the cases that we have not sent the move yet.
            # Roughly speaking we set the `peppol_move_state` to `ready` after posting
            # (in case the company and partner are on the PDP network and we have not sent it already)
            # and reset it to `False` when resetting to draft
            # (except if we have sent it already).
            if all([
                move.company_id.account_peppol_proxy_state == 'receiver',
                move.commercial_partner_id.peppol_verification_state == 'valid',
                move.state == 'posted',
                not move.peppol_move_state,
            ]):
                move.peppol_move_state = 'ready'
            elif (
                move.state == 'draft'
                and move.peppol_move_state in UNSENT_PEPPOL_MOVE_STATES
            ):
                move.peppol_move_state = False

    @api.depends('pdp_response_ids', 'pdp_response_ids.pdp_state', 'pdp_response_ids.ppf_state')
    def _compute_ppf_state(self):
        for move in self:
            move.ppf_move_state = move._pdp_get_tax_extract_state()
            move.ppf_lifecycle_state = move._pdp_get_lifecycle_state()

    @api.depends('peppol_move_state', 'peppol_message_uuid')
    def _compute_pdp_can_send_response(self):
        for move in self:
            move.pdp_can_send_response = bool(move.peppol_message_uuid) and move.peppol_move_state not in UNSENT_PEPPOL_MOVE_STATES

    def _pdp_get_response_status(self):
        """Return the PDP response status of the message"""
        self.ensure_one()
        # Non-PDP messages do not have a response status
        if not self.peppol_message_uuid:
            return None

        # Take the latest response status if we have any
        # TODO: I suppose "partially paid" is possible? Since 'paid' lifecyle does not have to be the full amount
        response_message = self.pdp_response_ids.filtered(lambda l: l.flow_number == '2' and l.pdp_state == 'done')
        latest_response = response_message.sorted(
            lambda l: (l.issue_date or datetime.min, STATUS_TO_PROCESS_CONDITION_CODE.get(l.response_code, '0'), l.id), reverse=True
        )[:1]
        if latest_response:
            return latest_response.response_code

        return None

    def _pdp_get_tax_extract_state(self):
        self.ensure_one()
        if not self.peppol_message_uuid or self.peppol_move_state in UNSENT_PEPPOL_MOVE_STATES:
            return False
        tax_extract_responses = self.pdp_response_ids.filtered(lambda l: l.flow_number == '1' and l.pdp_state == 'done')
        if not tax_extract_responses:
            return 'in_progress'
        states = tax_extract_responses.mapped('ppf_state')
        if ('inadmissible', 'rejected') in states:
            state = 'error'
        elif 'accepted' not in states:
            state = 'sent'
        else:
            state = 'done'
        return state

    def _pdp_get_lifecycle_state(self):
        self.ensure_one()
        if not self.peppol_message_uuid or self.peppol_move_state in UNSENT_PEPPOL_MOVE_STATES:
            return False
        current_status_responses = self.pdp_response_ids.filtered(lambda l: l.flow_number == '6')
        if not current_status_responses:
            return 'in_progress'
        states = current_status_responses.mapped('ppf_state')
        if ('inadmissible', 'rejected') in states:
            return 'error'
        return 'sent'

    def _l10n_fr_pdp_get_default_notes(self):
        self.ensure_one()
        # Mandatory / default notes for French e-invoicing [BR-FR-05]
        return {
            'PMT': self.env._("In the event of late payment, a flat-rate fee of €40 for collection costs will be charged (Articles L.441-10 and D.441-5 of the Code de commerce)."),
            'PMD': self.env._("Late payment penalties at an annual rate of 10% are applied if the payment is made after the due date."),
            'AAB': self.env._("No discount for early payment."),  # TODO: Early payment discount information
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
        # TODO: what about peppol (via PDP) moves? And business response?
        pdp_moves = self.filtered('pdp_can_send_response')
        if not pdp_moves:
            raise UserError(self.env._("Cannot send response for any of the journal entries."))
        wizard = self.env['pdp.response.wizard'].create({'move_ids': pdp_moves.ids})
        return wizard._get_records_action(name="Send Response Message", target='new')
