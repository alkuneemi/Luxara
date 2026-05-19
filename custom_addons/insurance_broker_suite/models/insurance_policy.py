from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import date, timedelta


class InsurancePolicy(models.Model):
    _name = 'insurance.policy'
    _description = 'Insurance Policy'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'policy_number'
    _order = 'expiry_date asc'

    policy_number = fields.Char(
        string='Policy Number', required=True, tracking=True, copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('insurance.policy'),
    )
    client_id = fields.Many2one('insurance.client', string='Client', required=True, tracking=True, ondelete='restrict')

    # ── Insurance Type — two options: legacy Selection + new Many2One ──────────
    insurance_type = fields.Selection([
        ('motor', 'Motor'),
        ('medical', 'Medical'),
        ('life', 'Life'),
        ('property', 'Property'),
        ('marine', 'Marine'),
        ('group_life', 'Group Life'),
        ('workmen_compensation', 'Workmen Compensation'),
    ], string='Insurance Type (Category)', required=False, tracking=True,
        help='Legacy category selection. Prefer using the Insurance Type (Linked) field below.')

    type_id = fields.Many2one(
        'insurance.type',
        string='Insurance Type',
        tracking=True,
        ondelete='restrict',
        domain="[('category_id.active', '=', True)]",
        help='Linked insurance type from the configuration hierarchy (Category > Type > Sub-Type).',
    )
    subtype_id = fields.Many2one(
        'insurance.subtype',
        string='Insurance Sub-Type',
        tracking=True,
        ondelete='restrict',
        domain="[('type_id', '=', type_id)]",
    )

    # ── Insurer — legacy Char + new Many2One linked to insurance.company.provider ──
    insurer = fields.Char(
        string='Insurer (Manual)',
        tracking=True,
        help='Legacy text field. Prefer using the Insurer Company field below for a proper link.',
    )
    insurer_id = fields.Many2one(
        'insurance.company.provider',
        string='Insurer Company',
        tracking=True,
        ondelete='restrict',
        help='Insurance company / underwriter linked from the Companies configuration.',
    )

    status = fields.Selection([
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
        ('pending', 'Pending'),
        ('renewed', 'Renewed'),
    ], string='Status', default='active', tracking=True)
    issue_date = fields.Date(string='Issue Date', required=True)
    expiry_date = fields.Date(string='Expiry Date', required=True, tracking=True)
    net_premium = fields.Float(string='Net Premium (OMR)', required=True, tracking=True)
    commission_rate = fields.Float(string='Commission Rate (%)')
    commission = fields.Float(string='Commission Amount (OMR)', compute='_compute_commission', store=True)
    sum_assured = fields.Float(string='Sum Assured (OMR)')
    coverage_details = fields.Text(string='Coverage Details')
    vehicle_chassis_no = fields.Char(string='Vehicle Chassis No.')
    vehicle_plate_no = fields.Char(string='Vehicle Plate No.')
    vehicle_year = fields.Integer(string='Vehicle Year')
    notes = fields.Text(string='Notes')

    # Source RFQ and CRM links
    rfq_id = fields.Many2one('insurance.rfq', string='Source RFQ')
    crm_lead_id = fields.Many2one(
        'crm.lead',
        string='CRM Opportunity',
        ondelete='set null',
        tracking=True,
        help='CRM opportunity linked to this policy.',
    )

    # Computed fields
    days_to_expiry = fields.Integer(compute='_compute_days_to_expiry', string='Days to Expiry', store=False)
    is_expiring_soon = fields.Boolean(compute='_compute_days_to_expiry', string='Expiring Soon', store=True)

    claim_ids = fields.One2many('insurance.claim', 'policy_id', string='Claims')
    commission_ids = fields.One2many('insurance.commission', 'policy_id', string='Commissions')
    claim_count = fields.Integer(compute='_compute_claim_count', string='Claims')

    @api.depends('commission_rate', 'net_premium')
    def _compute_commission(self):
        for rec in self:
            rec.commission = rec.net_premium * (rec.commission_rate / 100.0)

    @api.depends('expiry_date', 'status')
    def _compute_days_to_expiry(self):
        today = date.today()
        for rec in self:
            if rec.expiry_date and rec.status == 'active':
                delta = (rec.expiry_date - today).days
                rec.days_to_expiry = delta
                rec.is_expiring_soon = delta <= 60
            else:
                rec.days_to_expiry = 0
                rec.is_expiring_soon = False

    @api.depends('claim_ids')
    def _compute_claim_count(self):
        for rec in self:
            rec.claim_count = len(rec.claim_ids)

    @api.constrains('issue_date', 'expiry_date')
    def _check_dates(self):
        for rec in self:
            if rec.issue_date and rec.expiry_date and rec.issue_date >= rec.expiry_date:
                raise ValidationError('Expiry date must be after issue date.')

    def action_view_claims(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Claims',
            'res_model': 'insurance.claim',
            'view_mode': 'list,form',
            'domain': [('policy_id', '=', self.id)],
            'context': {'default_policy_id': self.id},
        }

    def action_renew(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Renew Policy',
            'res_model': 'insurance.policy',
            'view_mode': 'form',
            'context': {
                'default_client_id': self.client_id.id,
                'default_insurance_type': self.insurance_type,
                'default_type_id': self.type_id.id if self.type_id else False,
                'default_subtype_id': self.subtype_id.id if self.subtype_id else False,
                'default_insurer': self.insurer,
                'default_insurer_id': self.insurer_id.id if self.insurer_id else False,
                'default_net_premium': self.net_premium,
                'default_commission_rate': self.commission_rate,
                'default_coverage_details': self.coverage_details,
                'default_rfq_id': self.rfq_id.id if self.rfq_id else False,
            },
        }

    def action_cancel(self):
        self.write({'status': 'cancelled'})

    def action_mark_expired(self):
        self.write({'status': 'expired'})

    @api.model
    def _cron_check_expiry(self):
        today = date.today()
        alert_days = [60, 30, 7]
        for days in alert_days:
            target = today + timedelta(days=days)
            policies = self.search([
                ('expiry_date', '=', target),
                ('status', '=', 'active'),
            ])
            for policy in policies:
                policy.message_post(
                    body=f'Renewal Hunter: This policy expires in {days} days on {policy.expiry_date}. Please initiate renewal.',
                    message_type='notification',
                    subtype_xmlid='mail.mt_note',
                )
