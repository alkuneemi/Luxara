import logging

from odoo import _, api, fields, models
from odoo.addons.l10n_fr_pdp_reports.utils import drom_com_territories
from odoo.addons.l10n_fr_pdp_reports.models.pdp_flow import FLOW_OPEN_STATES, FLOW_SENT_STATES, FLOW_OPEN_STATES_SELECTION, FLOW_SENT_STATES_SELECTION
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_fr_pdp_original_flow_id = fields.Many2one(  # first flow for this move (can be a rectificative flow)
        comodel_name='l10n.fr.pdp.reports.flow',
        readonly=True,
        store=True,
        compute='_compute_l10n_fr_pdp_original_flow_id',
        string="Initial PDP Flow",
    )
    l10n_fr_pdp_flow_ids = fields.Many2many(
        comodel_name='l10n.fr.pdp.reports.flow',
        string="PDP Flows",
        compute='_compute_l10n_fr_pdp_flow_10_fields'
    )
    l10n_fr_pdp_status = fields.Selection(
        selection=[
            ('out_of_scope', "Out of scope"),
            ('error', "Error"),
        ] + FLOW_OPEN_STATES_SELECTION + FLOW_SENT_STATES_SELECTION,
        string="E-Reporting Status",
        compute='_compute_l10n_fr_pdp_status',
        store=True,
        copy=False,
        help="Lifecycle of the invoice within the French PDP reporting process.",
    )
    l10n_fr_pdp_display_info = fields.Boolean(related='company_id.l10n_fr_f10_enable_reporting')
    l10n_fr_pdp_is_flow_10_scope = fields.Selection(
        selection=[('transaction', 'Transaction'), ('payment', 'Payment')],
        compute='_compute_l10n_fr_pdp_flow_10_fields',
    )
    # l10n_fr_pdp_is_flow_10_scope = fields.Boolean(
    #     string="Is in Flow 10 scope",
    #     compute='_compute_l10n_fr_pdp_flow_10_fields',
    # )
    l10n_fr_pdp_error_message = fields.Text(
        string="Flow 10 blocking errors",
        compute='_compute_l10n_fr_pdp_flow_10_fields',
    )
    l10n_fr_pdp_has_error = fields.Boolean(
        compute='_compute_l10n_fr_pdp_has_error',
        store=True,
        readonly=True,
    )

    # -------------------------------------------------------------------------
    # Compute Methods
    # -------------------------------------------------------------------------

    @api.depends(
        'date',
        'move_type',
        'company_id.account_fiscal_country_id',
        'commercial_partner_id.country_id',
        'commercial_partner_id.vat',
        'l10n_fr_pdp_has_error',
        'line_ids.matched_debit_ids.debit_move_id',
        'line_ids.matched_credit_ids.credit_move_id',
        'l10n_fr_pdp_original_flow_id',
    )
    def _compute_l10n_fr_pdp_status(self):
        for move in self:
            if not move.l10n_fr_pdp_is_flow_10_scope:
                move.l10n_fr_pdp_status = 'out_of_scope'
            elif move.l10n_fr_pdp_has_error:
                move.l10n_fr_pdp_status = 'error'
            elif not move.l10n_fr_pdp_flow_ids:
                move.l10n_fr_pdp_status = None
            else:
                move.l10n_fr_pdp_status = move.l10n_fr_pdp_flow_ids[-1].state

    @api.depends(
        'date',
        'move_type',
        'company_id.account_fiscal_country_id',
        'commercial_partner_id.country_id',
        'commercial_partner_id.vat',
        'move_type',
        'line_ids.matched_debit_ids.debit_move_id',
        'line_ids.matched_credit_ids.credit_move_id',
    )
    def _compute_l10n_fr_pdp_original_flow_id(self):
        for move in self:
            if move.l10n_fr_pdp_original_flow_id.state not in FLOW_SENT_STATES: # once a move has been sent in a flow, do not change it's original flow !
                if not move.l10n_fr_pdp_is_flow_10_scope:
                    move.l10n_fr_pdp_original_flow_id = None
                else:
                    report_type = move.l10n_fr_pdp_is_flow_10_scope
                    move.l10n_fr_pdp_original_flow_id = self.env['l10n.fr.pdp.reports.flow'].\
                        _get_open_flow_and_create_if_needed(move, report_type)
            elif move.type == 'entry' and not move.l10n_fr_pdp_is_flow_10_scope:
                # if move is entry and has sent l10n_fr_pdp_original_flow_id and scope is now None
                # it means it's a payment that has been unreconciled after been send
                # -> we ensure there is an open payment flow to rectify the period
                self.env['l10n.fr.pdp.reports.flow']._get_open_flow_and_create_if_needed(move, 'payment')

    @api.depends(
        'state',
        'is_move_sent',
        'move_type',
        'company_id.account_fiscal_country_id',
        'commercial_partner_id.country_id',
        'commercial_partner_id.vat',
        'line_ids.matched_debit_ids.debit_move_id',
        'line_ids.matched_credit_ids.credit_move_id',
    )
    def _compute_l10n_fr_pdp_has_error(self):
        for move in self:
            move.l10n_fr_pdp_has_error = bool(move._get_l10n_fr_pdp_errors(lazy=True))

    @api.depends(
        'date',
        'move_type',
        'company_id.account_fiscal_country_id',
        'commercial_partner_id.country_id',
        'commercial_partner_id.vat',
        'move_type',
        'line_ids.matched_debit_ids.debit_move_id',
        'line_ids.matched_credit_ids.credit_move_id',
    )
    def _compute_l10n_fr_pdp_flow_10_fields(self):
        for move in self:
            ### SCOPE ###
            if (
                (move.is_sale_document(include_receipts=True) and move._get_l10n_fr_pdp_transaction_type())
                or (move.is_purchase_document(include_receipts=False) and move._is_b2bi_partner_for_purchase())
            ):
                move.l10n_fr_pdp_is_flow_10_scope = 'transaction'
            elif (
                move.move_type == 'entry' and move._l10n_fr_pdp_get_matched_transaction()
            ):
                move.l10n_fr_pdp_is_flow_10_scope = 'payment'
            else:
                move.l10n_fr_pdp_is_flow_10_scope = None

            ### FLOW IDS ###
            # original flow is rectificative : get it and later rectificative flows
            if move.l10n_fr_pdp_original_flow_id.initial_flow_id:
                rectificative_flows = move.l10n_fr_pdp_original_flow_id.initial_flow_id.rectificative_flow_ids
                move.l10n_fr_pdp_flow_ids = rectificative_flows.filtered(
                    lambda flow: flow.id >= move.l10n_fr_pdp_original_flow_id.id
                )
            # original flow is initial
            elif move.l10n_fr_pdp_original_flow_id:
                move.l10n_fr_pdp_flow_ids = move.l10n_fr_pdp_original_flow_id + move.l10n_fr_pdp_original_flow_id.rectificative_flow_ids
            else:
                move.l10n_fr_pdp_flow_ids = None

            ### ERROR MESSAGE ###
            move.l10n_fr_pdp_error_message = '\n-'.join([''] + move._get_l10n_fr_pdp_errors()) or None


    def _l10n_fr_pdp_get_matched_transaction(self):
        self.ensure_one()
        for move in self._get_reconciled_amls():
            if move.l10n_fr_pdp_is_flow_10_scope == 'transaction' and (
                move._is_downpayment()
                or any(tax.tax_exigibility == 'on_payment' for tax in move.invoice_line_ids.tax_ids)
            ):
                return move

    # -------------------------------------------------------------------------
    # Business Methods
    # -------------------------------------------------------------------------

    def _get_l10n_fr_pdp_errors(self, lazy=False):
        """Return the list of validation errors for this move in the context of PDP reporting."""
        self.ensure_one()
        if self.state != 'posted' or self.l10n_fr_pdp_is_flow_10_scope != 'transaction':
            return []
        transaction_type = self._get_l10n_fr_pdp_transaction_type()
        def check():
            if transaction_type == 'b2bi':
                if self.is_sale_document(include_receipts=True) and not self.is_move_sent:
                    yield _("Invoice/credit note has not been sent to the customer.")

                try:
                    self.commercial_partner_id.check_vat()
                except ValidationError:
                    yield _("Invalid partner VAT (%(vat)s).", vat=self.commercial_partner_id.vat)

                # TODO add check move names and adresses of move & linked moves and add baje checks

        if lazy:
            error = next(check(), False)
            return [error] if error else []
        return list(check())


    def _get_l10n_fr_pdp_transaction_type(self):
        """Classify invoice for PDP reporting: b2c, b2bi, or False (domestic B2B)."""
        self.ensure_one()
        # Use the centralized DROM-COM logic
        move = self._l10n_fr_pdp_get_matched_transaction() if self.move_type == 'entry' else self
        return drom_com_territories.get_transaction_flow_type(
            company_country=move.company_id.account_fiscal_country_id.code,
            partner_country=move.commercial_partner_id.country_id.code,
            partner_vat=move.commercial_partner_id.vat,
        )

    def _is_b2bi_partner_for_purchase(self):
        """Return True when a vendor bill partner is treated as b2bi for Flux 10."""
        self.ensure_one()
        company_country_code = self.company_id.account_fiscal_country_id.code
        partner_country_code = self.commercial_partner_id.country_id.code

        # Purchases are classified on geography/territory rules, not on supplier VAT presence.
        # Missing VAT must stay in-scope and be handled by validation errors.
        if company_country_code and partner_country_code:
            if drom_com_territories.should_use_einvoicing(company_country_code, partner_country_code):
                return False
            company_is_fr = drom_com_territories.is_france_territory(company_country_code)
            partner_is_fr = drom_com_territories.is_france_territory(partner_country_code)
            return not (company_is_fr and partner_is_fr and company_country_code == partner_country_code)

        vat = (self.commercial_partner_id.vat or '').strip()
        if company_country_code and len(vat) >= 2:
            return vat[:2].upper() != (company_country_code or '')
        return False

    # -------------------------------------------------------------------------
    # CRUD Override
    # -------------------------------------------------------------------------

    def button_draft(self):
        """Prevent resetting to draft when invoice already sent to PDP."""
        for move in self:
            if not move.is_sale_document(include_receipts=True):
                continue
            if move.l10n_fr_pdp_original_flow_id.state in FLOW_SENT_STATES:
                raise UserError(_("You cannot reset to draft an invoice already sent to PDP. Create a credit note and issue a new invoice instead or cancel this invoice."))
        return super().button_draft()

    def button_cancel(self):
        pass
