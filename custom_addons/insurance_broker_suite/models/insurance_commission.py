from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date


class InsuranceCommission(models.Model):
    _name = 'insurance.commission'
    _description = 'Commission Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'due_date asc'

    # ── Identity ───────────────────────────────────────────────────────────────
    name = fields.Char(string='Reference', compute='_compute_name', store=True)

    # ── Links ──────────────────────────────────────────────────────────────────
    policy_id = fields.Many2one(
        'insurance.policy', string='Policy / الوثيقة',
        required=True, ondelete='restrict', tracking=True,
    )
    client_id = fields.Many2one(
        'insurance.client', related='policy_id.client_id',
        store=True, readonly=True, string='Client',
    )
    insurer_id = fields.Many2one(
        'insurance.company.provider',
        related='policy_id.insurer_id',
        store=True, readonly=True, string='Insurer Company',
    )
    insurer = fields.Char(
        related='policy_id.insurer', store=True, readonly=True, string='Insurer (text)',
    )
    insurance_type = fields.Selection(
        related='policy_id.insurance_type', store=True, readonly=True,
    )
    subtype_id = fields.Many2one(
        'insurance.subtype', related='policy_id.subtype_id',
        store=True, readonly=True,
    )

    # ── Rate Config Link ───────────────────────────────────────────────────────
    commission_rate_id = fields.Many2one(
        'insurance.commission.rate',
        string='Commission Rate Config',
        ondelete='set null',
        tracking=True,
        help='معدل العمولة المعتمد من جدول الإعدادات',
    )

    # ── Financial ─────────────────────────────────────────────────────────────
    invoice_amount = fields.Float(
        string='Total Premium (OMR) / إجمالي القسط',
        required=True, tracking=True,
        help='القسط الإجمالي المدفوع من العميل',
    )
    commission_rate_pct = fields.Float(
        string='Commission Rate (%) / نسبة العمولة',
        required=True, tracking=True,
        digits=(5, 2),
    )
    commission_amount = fields.Float(
        string='Commission Amount (OMR) / مبلغ العمولة',
        compute='_compute_amounts', store=True,
        help='حصة البروكر = إجمالي القسط × نسبة العمولة',
    )
    insurer_amount = fields.Float(
        string='Net to Insurer (OMR) / صافي للشركة',
        compute='_compute_amounts', store=True,
        help='المبلغ المستحق لشركة التأمين = إجمالي القسط − مبلغ العمولة',
    )

    # Legacy fields (keep for backward compat)
    expected_amount = fields.Float(
        string='Expected Commission', compute='_compute_expected', store=True,
    )
    received_amount  = fields.Float(string='Received Amount', tracking=True)
    outstanding_amount = fields.Float(
        string='Outstanding', compute='_compute_outstanding', store=True,
    )

    # ── Status ─────────────────────────────────────────────────────────────────
    status = fields.Selection([
        ('draft',    'Draft / مسودة'),
        ('confirmed','Confirmed / معتمدة'),
        ('partial',  'Partial / جزئية'),
        ('received', 'Received / مستلمة'),
        ('paid_out', 'Paid to Insurer / مدفوعة للشركة'),
        ('overdue',  'Overdue / متأخرة'),
    ], string='Status', default='draft', tracking=True)

    due_date      = fields.Date(string='Due Date / تاريخ الاستحقاق', tracking=True)
    received_date = fields.Date(string='Received Date', tracking=True)
    paid_out_date = fields.Date(string='Paid to Insurer Date', tracking=True)

    # ── Accounting ─────────────────────────────────────────────────────────────
    journal_id = fields.Many2one(
        'account.journal', string='Journal',
        domain="[('type', 'in', ['general','sale'])]",
    )
    commission_account_id = fields.Many2one(
        'account.account', string='Commission Income Account / حساب دخل العمولة',
        domain="[('account_type', 'in', ['income','income_other'])]",
    )
    payable_account_id = fields.Many2one(
        'account.account', string='Insurer Payable Account / حساب الشركة',
        domain="[('account_type', '=', 'liability_payable')]",
    )
    receivable_account_id = fields.Many2one(
        'account.account', string='Customer Receivable Account',
        domain="[('account_type', '=', 'asset_receivable')]",
    )

    # Journal Entry links
    move_id = fields.Many2one(
        'account.move', string='Journal Entry / القيد المحاسبي',
        readonly=True, copy=False,
    )
    payment_move_id = fields.Many2one(
        'account.move', string='Payment Entry',
        readonly=True, copy=False,
    )
    move_state = fields.Selection(
        related='move_id.state', string='Entry State', readonly=True,
    )

    # Payment reference
    payment_reference = fields.Char(string='Payment Reference / مرجع الدفع')
    payment_method    = fields.Selection([
        ('bank',   'Bank Transfer'),
        ('cash',   'Cash'),
        ('card',   'Credit / Debit Card'),
        ('online', 'Online Payment'),
        ('cheque', 'Cheque'),
    ], string='Payment Method', tracking=True)

    notes = fields.Text(string='Notes / ملاحظات')

    # ── Computed ───────────────────────────────────────────────────────────────
    @api.depends('policy_id')
    def _compute_name(self):
        for rec in self:
            rec.name = f"COM / {rec.policy_id.policy_number or 'New'}"

    @api.depends('invoice_amount', 'commission_rate_pct')
    def _compute_amounts(self):
        for rec in self:
            rec.commission_amount = rec.invoice_amount * (rec.commission_rate_pct / 100.0)
            rec.insurer_amount    = rec.invoice_amount - rec.commission_amount

    @api.depends('commission_amount')
    def _compute_expected(self):
        for rec in self:
            rec.expected_amount = rec.commission_amount

    @api.depends('commission_amount', 'received_amount')
    def _compute_outstanding(self):
        for rec in self:
            rec.outstanding_amount = rec.commission_amount - (rec.received_amount or 0.0)

    # ── Onchange: auto-fill from rate config ───────────────────────────────────
    @api.onchange('commission_rate_id')
    def _onchange_rate_id(self):
        if self.commission_rate_id:
            r = self.commission_rate_id
            self.commission_rate_pct      = r.rate if r.rate_type == 'percent' else 0.0
            self.commission_account_id    = r.commission_account_id
            self.payable_account_id       = r.payable_account_id
            self.journal_id               = r.journal_id

    @api.onchange('policy_id')
    def _onchange_policy_id(self):
        """Auto-fill invoice_amount and commission_rate from policy"""
        if self.policy_id:
            self.invoice_amount       = self.policy_id.net_premium
            self.commission_rate_pct  = self.policy_id.commission_rate
            # Try to auto-find rate config
            if self.policy_id.subtype_id and self.policy_id.insurer_id:
                rate = self.env['insurance.commission.rate'].get_rate_for(
                    self.policy_id.subtype_id.id,
                    self.policy_id.insurer_id.id,
                )
                if rate:
                    self.commission_rate_id  = rate
                    self.commission_rate_pct = rate.rate if rate.rate_type == 'percent' else 0.0
                    self.commission_account_id = rate.commission_account_id
                    self.payable_account_id    = rate.payable_account_id
                    self.journal_id            = rate.journal_id

    # ── Actions ────────────────────────────────────────────────────────────────
    def action_confirm(self):
        """تأكيد العمولة وإنشاء القيد المحاسبي"""
        self.ensure_one()
        if self.status != 'draft':
            raise UserError('Only draft commissions can be confirmed.')
        if not self.invoice_amount or not self.commission_rate_pct:
            raise UserError('Please set the invoice amount and commission rate first.')
        self.write({'status': 'confirmed'})
        self._create_journal_entry()
        return True

    def action_mark_received(self):
        self.write({
            'status': 'received',
            'received_amount': self.commission_amount,
            'received_date': date.today(),
        })

    def action_mark_paid_out(self):
        """تسجيل دفع المبلغ المستحق لشركة التأمين"""
        self.write({
            'status': 'paid_out',
            'paid_out_date': date.today(),
        })

    def action_mark_partial(self):
        self.write({'status': 'partial'})

    def action_mark_overdue(self):
        self.write({'status': 'overdue'})

    def action_reset_draft(self):
        self.write({'status': 'draft'})

    def action_view_journal_entry(self):
        self.ensure_one()
        if not self.move_id:
            raise UserError('No journal entry created yet.')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Journal Entry',
            'res_model': 'account.move',
            'res_id': self.move_id.id,
            'view_mode': 'form',
        }

    # ── Journal Entry Creation ─────────────────────────────────────────────────
    def _create_journal_entry(self):
        """
        القيد المحاسبي عند تأكيد العمولة:

          Dr  Customer Receivable     ← invoice_amount    (إجمالي القسط)
              Cr  Commission Income   ← commission_amount  (حصة البروكر)
              Cr  Insurer Payable     ← insurer_amount     (مستحق للشركة)
        """
        self.ensure_one()
        if self.move_id:
            return  # already created

        # ── Determine accounts ─────────────────────────────────────────────────
        journal = (
            self.journal_id
            or self.env['account.journal'].search([('type', '=', 'general')], limit=1)
        )
        if not journal:
            raise UserError('No accounting journal configured. Please set a journal on the commission or commission rate.')

        commission_acc = (
            self.commission_account_id
            or (self.commission_rate_id and self.commission_rate_id.commission_account_id)
        )
        payable_acc = (
            self.payable_account_id
            or (self.commission_rate_id and self.commission_rate_id.payable_account_id)
        )
        receivable_acc = self.receivable_account_id

        if not commission_acc:
            raise UserError(
                'Please set a Commission Income Account on this commission or on the commission rate config.'
            )
        if not payable_acc:
            raise UserError(
                'Please set an Insurer Payable Account on this commission or on the commission rate config.'
            )

        # ── Build journal entry lines ──────────────────────────────────────────
        policy_num  = self.policy_id.policy_number or self.name
        client_name = self.client_id.name or 'Customer'
        insurer_name = (
            self.insurer_id.name if self.insurer_id
            else (self.insurer or 'Insurer')
        )

        line_vals = []

        # Debit: Customer Receivable (if configured)
        if receivable_acc:
            line_vals.append((0, 0, {
                'account_id': receivable_acc.id,
                'debit':      self.invoice_amount,
                'credit':     0.0,
                'name':       f'Premium Receivable — {client_name} / {policy_num}',
                'partner_id': (
                    self.client_id.partner_id.id
                    if hasattr(self.client_id, 'partner_id') and self.client_id.partner_id
                    else False
                ),
            }))

        # Credit: Commission Income
        line_vals.append((0, 0, {
            'account_id': commission_acc.id,
            'debit':      0.0,
            'credit':     self.commission_amount,
            'name':       f'Commission Income {self.commission_rate_pct:.2f}% — {policy_num}',
        }))

        # Credit: Insurer Payable
        line_vals.append((0, 0, {
            'account_id': payable_acc.id,
            'debit':      0.0,
            'credit':     self.insurer_amount,
            'name':       f'Net Payable to {insurer_name} — {policy_num}',
        }))

        # If no receivable account — balance the entry with a debit on payable + commission
        if not receivable_acc:
            line_vals.insert(0, (0, 0, {
                'account_id': commission_acc.id,
                'debit':      self.invoice_amount,
                'credit':     0.0,
                'name':       f'Premium Collected — {client_name} / {policy_num}',
            }))
            # Override credit lines to use invoice_amount as balancing
            line_vals = [
                (0, 0, {
                    'account_id': commission_acc.id,
                    'debit':  self.commission_amount,
                    'credit': 0.0,
                    'name':   f'Commission Income {self.commission_rate_pct:.2f}% — {policy_num}',
                }),
                (0, 0, {
                    'account_id': payable_acc.id,
                    'debit':  self.insurer_amount,
                    'credit': 0.0,
                    'name':   f'Insurer Receivable — {insurer_name} / {policy_num}',
                }),
                (0, 0, {
                    'account_id': commission_acc.id,
                    'debit':  0.0,
                    'credit': self.invoice_amount,
                    'name':   f'Premium Collected — {policy_num}',
                }),
            ]

        move = self.env['account.move'].create({
            'move_type':  'entry',
            'journal_id': journal.id,
            'date':       fields.Date.today(),
            'ref':        self.name,
            'narration':  (
                f'Commission entry for policy {policy_num}\n'
                f'Total Premium: {self.invoice_amount:.3f} OMR | '
                f'Commission ({self.commission_rate_pct:.2f}%): {self.commission_amount:.3f} OMR | '
                f'Net to {insurer_name}: {self.insurer_amount:.3f} OMR'
            ),
            'line_ids': line_vals,
        })

        self.move_id = move
        self.message_post(
            body=(
                f'✅ Journal entry created: <b>{move.name}</b><br/>'
                f'Premium: <b>{self.invoice_amount:.3f} OMR</b> | '
                f'Commission: <b>{self.commission_amount:.3f} OMR ({self.commission_rate_pct:.2f}%)</b> | '
                f'Net to Insurer: <b>{self.insurer_amount:.3f} OMR</b>'
            ),
            message_type='notification',
        )

    # ── Cron ───────────────────────────────────────────────────────────────────
    @api.model
    def _cron_check_overdue(self):
        today = date.today()
        overdue = self.search([
            ('status', 'in', ['confirmed', 'partial']),
            ('due_date', '<', today),
        ])
        overdue.write({'status': 'overdue'})
