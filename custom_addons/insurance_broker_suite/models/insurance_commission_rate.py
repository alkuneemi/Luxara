from odoo import models, fields, api
from odoo.exceptions import ValidationError


class InsuranceCommissionRate(models.Model):
    """
    جدول تعريف نسب العمولات
    لكل منتج (subtype) + شركة مزودة → نسبة العمولة المتفق عليها
    """
    _name = 'insurance.commission.rate'
    _description = 'Commission Rate Configuration'
    _inherit = ['mail.thread']
    _rec_name = 'display_name'
    _order = 'subtype_id, provider_id'

    # ── Product & Provider ─────────────────────────────────────────────────────
    subtype_id = fields.Many2one(
        'insurance.subtype', string='Insurance Product',
        required=True, ondelete='restrict', tracking=True,
        help='نوع المنتج التأميني (Sub-Type)',
    )
    type_id = fields.Many2one(
        'insurance.type', string='Insurance Type',
        related='subtype_id.type_id', store=True, readonly=True,
    )
    provider_id = fields.Many2one(
        'insurance.company.provider', string='Provider Company / شركة المزود',
        required=True, ondelete='restrict', tracking=True,
        help='شركة التأمين المزودة لهذا المنتج',
    )

    display_name = fields.Char(
        string='Rate Reference', compute='_compute_display_name', store=True,
    )

    # ── Rate ───────────────────────────────────────────────────────────────────
    rate_type = fields.Selection([
        ('percent', 'Percentage — نسبة مئوية'),
        ('fixed',   'Fixed Amount — مبلغ ثابت'),
    ], string='Rate Type', default='percent', required=True, tracking=True)

    rate = fields.Float(
        string='Commission Rate (%)', digits=(5, 2), tracking=True,
        help='نسبة العمولة المتفق عليها مع شركة المزود',
    )
    fixed_amount = fields.Float(
        string='Fixed Commission (OMR)', digits=(10, 3), tracking=True,
        help='مبلغ العمولة الثابت إذا كان النوع "مبلغ ثابت"',
    )
    min_rate = fields.Float(string='Min Rate (%)', digits=(5, 2))
    max_rate = fields.Float(string='Max Rate (%)', digits=(5, 2))

    # ── Validity ───────────────────────────────────────────────────────────────
    effective_date = fields.Date(string='Effective From / اعتباراً من')
    expiry_date    = fields.Date(string='Effective Until / حتى تاريخ')
    active         = fields.Boolean(default=True)

    # ── Accounting ─────────────────────────────────────────────────────────────
    commission_account_id = fields.Many2one(
        'account.account', string='Commission Income Account / حساب دخل العمولة',
        help='الحساب المحاسبي الذي تُقيّد فيه إيرادات العمولة',
        domain="[('account_type', 'in', ['income', 'income_other'])]",
    )
    payable_account_id = fields.Many2one(
        'account.account', string='Insurer Payable Account / حساب الشركة المزودة',
        help='الحساب المحاسبي لمستحقات شركة التأمين',
        domain="[('account_type', '=', 'liability_payable')]",
    )
    journal_id = fields.Many2one(
        'account.journal', string='Accounting Journal',
        domain="[('type', 'in', ['general','sale'])]",
    )

    notes = fields.Text(string='Notes / ملاحظات')

    # ── Computed ───────────────────────────────────────────────────────────────
    @api.depends('subtype_id', 'provider_id', 'rate', 'rate_type')
    def _compute_display_name(self):
        for rec in self:
            sub  = rec.subtype_id.name or ''
            prov = rec.provider_id.name or ''
            rate = f'{rec.rate}%' if rec.rate_type == 'percent' else f'{rec.fixed_amount} OMR'
            rec.display_name = f'{sub} / {prov} — {rate}'

    # ── Validation ─────────────────────────────────────────────────────────────
    @api.constrains('rate', 'rate_type')
    def _check_rate(self):
        for rec in self:
            if rec.rate_type == 'percent' and not (0 <= rec.rate <= 100):
                raise ValidationError('Commission rate must be between 0% and 100%.')

    @api.constrains('effective_date', 'expiry_date')
    def _check_dates(self):
        for rec in self:
            if rec.effective_date and rec.expiry_date and rec.effective_date > rec.expiry_date:
                raise ValidationError('Effective date must be before expiry date.')

    # ── Helper ─────────────────────────────────────────────────────────────────
    def compute_commission(self, invoice_amount):
        """حساب مبلغ العمولة بناءً على نوع الحساب والمبلغ الإجمالي"""
        self.ensure_one()
        if self.rate_type == 'percent':
            return invoice_amount * (self.rate / 100.0)
        return self.fixed_amount

    @api.model
    def get_rate_for(self, subtype_id, provider_id):
        """استرجاع معدل العمولة المعمول به للمنتج والمزود"""
        from datetime import date
        today = date.today()
        domain = [
            ('subtype_id', '=', subtype_id),
            ('provider_id', '=', provider_id),
            ('active', '=', True),
            '|', ('effective_date', '=', False), ('effective_date', '<=', today),
            '|', ('expiry_date', '=', False),    ('expiry_date', '>=', today),
        ]
        return self.search(domain, limit=1)
