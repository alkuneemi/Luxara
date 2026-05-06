import logging

from odoo import _, api, fields, models
from odoo.addons.l10n_fr_pdp_reports.utils import drom_com_territories
from odoo.addons.l10n_fr_pdp_reports.models.pdp_flow import FLOW_OPEN_STATES, FLOW_SENT_STATES
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_fr_pdp_flow_ids = fields.Many2many(
        comodel_name='l10n.fr.pdp.reports.flow',
        string="PDP Flows",
        compute='_compute_l10n_fr_pdp_flow_ids'
    )
    l10n_fr_pdp_original_flow_id = fields.Many2one(  # first flow for this move (can be a rectificative flow)
        comodel_name='l10n.fr.pdp.reports.flow',
        readonly=True,
        stored=True,
        compute='_l10n_fr_pdp_original_flow_id',
        string="Initial PDP Flow",
    )
    # l10n_fr_pdp_current_flow_id = fields.Many2one(  # last flow relevant for this move
    #     comodel_name='l10n.fr.pdp.reports.flow',
    #     compute='_l10n_fr_pdp_initial_flow_id',
    # )
    l10n_fr_pdp_status = fields.Selection(
        selection=[
            ('out_of_scope', "Out of scope"),
            ('pending', "Pending"),
            ('ready', "Ready to send"),
            ('error', "Error"),
            ('sent', "Sent"),
        ],
        string="E-Reporting Status",
        compute='_compute_l10n_fr_pdp_status',
        store=True,
        copy=False,
        help="Lifecycle of the invoice within the French PDP reporting process.",
    )
    l10n_fr_pdp_display_info = fields.Boolean(related='company_id.l10n_fr_f10_enable_reporting')
    l10n_fr_pdp_is_flow_10_scope = fields.Boolean(
        string="Is in Flow 10 scope",
        compute='_compute_l10n_fr_pdp_flow_10_status',
    )
    l10n_fr_pdp_error_message = fields.Text(
        string="Flow 10 blocking errors",
        compute='_compute_l10n_fr_pdp_flow_10_status',
    )
    l10n_fr_pdp_has_error = fields.Boolean(
        compute='_compute_l10n_fr_pdp_flow_10_status',
        store=True,
        readonly=True,
    )

    # -------------------------------------------------------------------------
    # Compute Methods
    # -------------------------------------------------------------------------

    @api.depends(
        'move_type',
        'company_id.account_fiscal_country_id',
        'commercial_partner_id.country_id',
        'commercial_partner_id.vat'
    )
    def _compute_l10n_fr_pdp_flow_10_status(self):
        for move in self:
            if move.is_sale_document(include_receipts=True):
                move.l10n_fr_pdp_is_flow_10_scope = bool(move._get_l10n_fr_pdp_transaction_type())
            elif move.is_purchase_document(include_receipts=False):
                move.l10n_fr_pdp_is_flow_10_scope = move._is_b2bi_partner_for_purchase()
            else:
                move.l10n_fr_pdp_is_flow_10_scope = False

            if move.state != 'posted' or not move.l10n_fr_pdp_is_flow_10_scope:
                move.l10n_fr_pdp_error_message = None
                move.l10n_fr_pdp_has_error = False
                continue

            error_messages = move._get_l10n_fr_pdp_errors()
            if error_messages:
                move.l10n_fr_pdp_error_message = '\n-'.join([''] + error_messages)
                move.l10n_fr_pdp_has_error = True
            else:
                move.l10n_fr_pdp_error_message = None
                move.l10n_fr_pdp_has_error = False


    # @api.depends('l10n_fr_pdp_original_flow_id')
    # def _compute_l10n_fr_pdp_flow_ids(self):
    #     flows_map = {
    #         initial: rectificative for initial, rectificative
    #         in self.env['l10n.fr.pdp.reports.flow']._read_group(
    #             domain=['initial_flow_id', 'in', self.l10n_fr_pdp_initial_flow_id],
    #             aggregates=['id:recordset'],
    #             groupby=['initial_flow_id'],
    #             order='id',
    #         )
    #     }
    #     for move in self:
    #         # original flow is initial
    #         if move.l10n_fr_pdp_original_flow_id in flows_map:
    #             move.l10n_fr_pdp_flow_ids = (
    #                 move.l10n_fr_pdp_original_flow_id +
    #                 flows_map[move.l10n_fr_pdp_original_flow_id]
    #             )
    #         # original flow is rectificative (get itself and later rectificative flows)
    #         elif move.l10n_fr_pdp_original_flow_id:
    #             move.l10n_fr_pdp_flow_ids = flows_map[
    #                 move.l10n_fr_pdp_original_flow_id.l10n_fr_pdp_initial_flow_id
    #             ].filtered(lambda flow: flow.id >= move.l10n_fr_pdp_original_flow_id.id)

    @api.depends('l10n_fr_pdp_original_flow_id')
    def _compute_l10n_fr_pdp_flow_ids(self):
        for move in self:
            # original flow is rectificative : get itf and later rectificative flows
            if move.l10n_fr_pdp_original_flow_id.initial_flow_id:
                rectificative_flows = move.l10n_fr_pdp_original_flow_id.initial_flow_id.rectificative_flow_ids
                move.l10n_fr_pdp_flow_ids = rectificative_flows.filtered(
                    lambda flow: flow.id >= move.l10n_fr_pdp_original_flow_id.id
                )
            # original flow is initial
            elif move.l10n_fr_pdp_original_flow_id:
                move.l10n_fr_pdp_flow_ids = move.l10n_fr_pdp_original_flow_id + move.l10n_fr_pdp_original_flow_id.rectificative_flow_ids

    @api.depends(
        'date',
        'move_type',
        'company_id.account_fiscal_country_id',
        'commercial_partner_id.country_id',
        'commercial_partner_id.vat',
    )
    def _l10n_fr_pdp_original_flow_id(self):
        for move in self:
            if move.l10n_fr_pdp_original_flow_id.state in FLOW_SENT_STATES:
                # once a move has been sent in a flow, do not change it's original flow !
                continue
            if not move.l10n_fr_pdp_is_flow_10_scope:
                move.l10n_fr_pdp_original_flow_id = False
            else:
                move.l10n_fr_pdp_original_flow_id = self.env['l10n.fr.pdp.reports.flow']._get_open_flow_and_create_if_needed(move)

    @api.depends(
        'state',
        'move_type',
        'commercial_partner_id.vat',
        'commercial_partner_id.country_id',
        'commercial_partner_id',
        'company_id',
        'company_id.account_fiscal_country_id',
        'company_id.partner_id.vat',
        'l10n_fr_pdp_flow_ids.state',
        'l10n_fr_pdp_flow_ids.error_move_ids',
        'l10n_fr_pdp_flow_ids.period_status',
        'is_move_sent',
    )
    def _compute_l10n_fr_pdp_status(self):
        for move in self:
            is_sale = move.is_sale_document(include_receipts=True)
            is_purchase = move.is_purchase_document(include_receipts=False)  # Purchase receipts are out of scope as B2B can't be receipts and there is not VAT to report on B2C purchases.

            # Not posted or not a supported document -> not applicable
            if move.state != 'posted' or not (is_sale or is_purchase):
                move.l10n_fr_pdp_status = False
                continue

            if not move.l10n_fr_pdp_is_flow_10_scope:
                move.l10n_fr_pdp_status = 'out_of_scope'
                continue

            # Check if move is in any flow
            flows = move.l10n_fr_pdp_flow_ids
            if not flows:
                # In-scope posted document not aggregated yet.
                move.l10n_fr_pdp_status = 'pending'
                continue

            # Get the most relevant flow for this move (prioritize non-sent flows),
            # then pick the most recent one to avoid stale status from older flows.
            sorted_flows = flows.sorted('id')
            relevant_flow = next(
                (flow for flow in sorted_flows if flow.state not in FLOW_SENT_STATES),
                False,
            ) or sorted_flows[0]

            # Check if move has validation errors in the relevant flow
            has_errors = move in relevant_flow.error_move_ids

            # v1.2 Status logic based on period_status:
            # - open period -> pending (users have time to fix errors)
            # - grace period -> error (if validation errors) OR ready (if valid)
            # - closed period -> sent (if flow sent) OR error (will be in auto-created RE)

            # Recompute directly to avoid stale cached value when "today" changes
            # (especially in cron/time-window transitions and tests patching today).
            state = relevant_flow.state

            # Priority 1: Flow already sent/completed
            if state in FLOW_SENT_STATES:
                if has_errors and relevant_flow.transport_status == 'PARTIAL_REJECTED':
                    move.l10n_fr_pdp_status = 'error'
                else:
                    move.l10n_fr_pdp_status = 'sent'
            # Open period: users have time to fix errors, stay pending.
            elif relevant_flow.period_status == 'open':
                move.l10n_fr_pdp_status = 'pending'
            # Grace/closed: validation errors are surfaced.
            elif has_errors:
                move.l10n_fr_pdp_status = 'error'
            # Flow built and valid: ready to send (even on due day / after if not sent yet).
            elif state == 'ready':
                move.l10n_fr_pdp_status = 'ready'
            else:
                move.l10n_fr_pdp_status = 'pending'

    # -------------------------------------------------------------------------
    # Business Methods
    # -------------------------------------------------------------------------

    def _get_l10n_fr_pdp_errors(self):
        """Return the list of validation errors for this move in the context of PDP reporting."""
        self.ensure_one()
        errors = []
        company_partner = self.company_id.partner_id.commercial_partner_id
        company_vat = company_partner.vat
        company_country = company_partner.country_id.code
        transaction_type = self._get_l10n_fr_pdp_transaction_type()
        if transaction_type == 'b2bi':
            if self.is_sale_document(include_receipts=True) and not self.is_move_sent:
                errors.append(_("Invoice/credit note has not been sent to the customer."))

            try:
                self.commercial_partner_id.check_vat()
            except ValidationError:
                errors.append(_("Invalid partner VAT (%(vat)s).", vat=self.commercial_partner_id.vat))
            # if not company_vat:
            #     requires_tt122 = any(tax.amount == 0 for tax in self.invoice_line_ids.tax_ids)
            #     representative_vat = (self.company_id.l10n_fr_pdp_fiscal_representative_vat or '').strip()  # TODO remove this
            #     if requires_tt122:
            #         if not representative_vat:
            #             errors.append(_("Missing seller fiscal representative VAT (TT-122)."))
            #         elif not is_valid_vat(representative_vat, company_country):
            #             errors.append(_("Invalid seller fiscal representative VAT (%(vat)s).", vat=representative_vat))
            #     else:
            #         errors.append(_("Missing seller VAT."))
            # elif not is_valid_vat(company_vat, company_country):
            #     errors.append(_("Invalid seller VAT (%(vat)s).", vat=company_vat))

        return errors


    def _get_l10n_fr_pdp_transaction_type(self):
        """Classify invoice for PDP reporting: b2c, b2bi, or False (domestic B2B)."""
        self.ensure_one()
        # Use the centralized DROM-COM logic
        return drom_com_territories.get_transaction_flow_type(
            company_country=self.company_id.account_fiscal_country_id.code,
            partner_country=self.commercial_partner_id.country_id.code,
            partner_vat=self.commercial_partner_id.vat,
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

    def write(self, vals):
        """Reset open PDP flows when tracked fields change."""
        # TODO: remove this.
        # If a move is not sent -> no need to generate the flow xml yet
        # If a move is set, prevent changing anything, allow to cancel it and in this case a rectificative flow must be created.
        not_previously_posted = {move for move in self if move.state != 'posted'}
        tracked_fields = {
            'invoice_date',
            'date',
            'invoice_line_ids',
            'currency_id',
            'partner_id',
            'partner_shipping_id',
            'move_type',
            'state',
            'name',
            'is_move_sent',
        }
        res = super().write(vals)
        if tracked_fields.intersection(vals):
            flows_to_reset = self.env['l10n.fr.pdp.reports.flow'].browse()
            for move in self:
                if move.state != 'posted':
                    continue
                if move.is_sale_document(include_receipts=True):
                    if not move._get_l10n_fr_pdp_transaction_type():
                        continue
                elif move.is_purchase_document(include_receipts=False):
                    if not move._is_b2bi_partner_for_purchase():
                        continue
                else:
                    continue

                open_flows = move.l10n_fr_pdp_flow_ids.filtered(lambda f: f.state in FLOW_OPEN_STATES)
                if open_flows:
                    flows_to_reset |= open_flows
            flows_to_reset._mark_as_outdated()
            # v1.2: No automatic correction flows. User must create credit note + RE manually.
        if 'is_move_sent' in vals:
            affected = self.filtered(lambda m: m.state == 'posted' and m.is_sale_document(include_receipts=True))
            if affected:
                flows = affected.mapped('l10n_fr_pdp_flow_ids').filtered(lambda f: f.state in FLOW_OPEN_STATES)
                if flows:
                    flows._mark_as_outdated()
                    try:
                        flows._build_payload()
                    except Exception:  # TODO  ? Why try except ? UserError enough ???
                        _logger.exception('Failed to rebuild PDP payload after send flag change')
        # Create rectificative flows for cancellations of previously sent invoices.
        if vals.get('state') == 'cancel':
            sent_flows = self.env['l10n.fr.pdp.reports.flow'].browse()
            for move in self:
                if move.id in not_previously_posted or not move.is_sale_document(include_receipts=True):
                    continue
                sent_flows |= move.l10n_fr_pdp_flow_ids.filtered(lambda f: f.state in {'sent', 'completed'})
            for flow in sent_flows:
                flow.action_create_rectificative_flow()
        return res

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
