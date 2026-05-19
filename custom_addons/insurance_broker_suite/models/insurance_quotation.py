from odoo import models, fields, api
import secrets


class InsuranceQuotation(models.Model):
    """
    نموذج التسعيرة العامة — يجمع عروض الأسعار من جميع الشركات لطلب تأمين واحد.
    يدعم ثلاثة مصادر: يدوي (موظف)، بوابة مباشرة، API.
    """
    _name = 'insurance.quotation'
    _description = 'Insurance Quotation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'reference'
    _order = 'create_date desc'

    reference = fields.Char(
        string='Reference', readonly=True, copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('insurance.quotation') or 'QT-NEW',
    )

    application_id = fields.Many2one(
        'insurance.application',
        string='Insurance Application / الطلب',
        ondelete='cascade',
        index=True,
    )
    opportunity_id = fields.Many2one(
        'insurance.opportunity',
        string='Opportunity / الفرصة',
        ondelete='set null',
        index=True,
    )

    # Insurance selection (denormalized for performance)
    subtype_id = fields.Many2one(
        'insurance.subtype',
        string='Insurance Sub-Type',
        related='application_id.subtype_id',
        store=True,
        readonly=True,
    )
    type_id = fields.Many2one(
        'insurance.type',
        related='application_id.type_id',
        store=True,
        readonly=True,
    )
    category_id = fields.Many2one(
        'insurance.category',
        related='application_id.category_id',
        store=True,
        readonly=True,
    )

    # Customer info (denormalized)
    customer_name = fields.Char(related='application_id.customer_name', store=True, readonly=True)
    customer_email = fields.Char(related='application_id.customer_email', store=True, readonly=True)
    customer_phone = fields.Char(related='application_id.customer_phone', store=True, readonly=True)

    status = fields.Selection([
        ('open', 'Open — Collecting Quotes'),
        ('pending_manual', 'Pending Manual Entry'),
        ('quotes_received', 'Quotes Received'),
        ('presented', 'Presented to Customer'),
        ('accepted', 'Accepted'),
        ('closed', 'Closed'),
    ], string='Status', default='open', tracking=True)

    notes = fields.Text(string='Internal Notes')
    presented_at = fields.Datetime(string='Presented to Customer At')
    accepted_at = fields.Datetime(string='Accepted At')

    # Public token for customer to view quotation online
    public_token = fields.Char(
        string='Public Token', copy=False, readonly=True,
        default=lambda self: secrets.token_urlsafe(20),
    )
    public_url = fields.Char(string='Customer Quote URL', compute='_compute_public_url')

    line_ids = fields.One2many('insurance.quotation.line', 'quotation_id', string='Quote Lines')
    line_count = fields.Integer(compute='_compute_line_count', string='Quotes Count')

    recommended_line_id = fields.Many2one(
        'insurance.quotation.line',
        string='Recommended Quote',
        domain="[('quotation_id', '=', id)]",
    )

    # ── Computed ──────────────────────────────────────────────────────────────────
    @api.depends('public_token')
    def _compute_public_url(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for rec in self:
            if rec.public_token:
                rec.public_url = f'{base}/insurance/quotation/view/{rec.public_token}'
            else:
                rec.public_url = ''

    @api.depends('line_ids')
    def _compute_line_count(self):
        for rec in self:
            rec.line_count = len(rec.line_ids)

    # ── Actions ───────────────────────────────────────────────────────────────────
    def action_mark_presented(self):
        from datetime import datetime
        self.write({'status': 'presented', 'presented_at': datetime.now()})

    def action_close(self):
        self.write({'status': 'closed'})

    def action_auto_populate_companies(self):
        """
        تلقائياً يضيف شركات التأمين التي لديها تسعيرة للنوع الفرعي هذا.
        """
        self.ensure_one()
        if not self.subtype_id:
            return
        pricings = self.env['insurance.company.pricing'].search([
            ('subtype_id', '=', self.subtype_id.id),
            ('active', '=', True),
            ('company_id.active', '=', True),
        ])
        existing_companies = self.line_ids.mapped('company_id.id')
        new_lines = []
        for pricing in pricings:
            if pricing.company_id.id not in existing_companies:
                eff_type = pricing.get_effective_integration_type()
                new_lines.append({
                    'quotation_id': self.id,
                    'company_id': pricing.company_id.id,
                    'pricing_id': pricing.id,
                    'source_type': eff_type,
                    'status': 'pending' if eff_type == 'manual' else 'awaiting_api',
                    'base_premium': pricing.base_premium,
                })
        if new_lines:
            self.env['insurance.quotation.line'].create(new_lines)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Companies Added',
                'message': f'{len(new_lines)} companies added to quotation.',
                'type': 'success',
            }
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('reference') or vals['reference'] == 'QT-NEW':
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'insurance.quotation') or 'QT-NEW'
            if not vals.get('public_token'):
                vals['public_token'] = secrets.token_urlsafe(20)
        return super().create(vals_list)


class InsuranceQuotationLine(models.Model):
    """
    سطر في التسعيرة — عرض سعر من شركة واحدة.
    يمكن أن يكون مصدره: يدوي / بوابة مباشرة / API.
    """
    _name = 'insurance.quotation.line'
    _description = 'Quotation Line (per Company)'
    _order = 'premium asc, status'
    _rec_name = 'company_id'

    quotation_id = fields.Many2one(
        'insurance.quotation', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(
        'insurance.company.provider', string='Insurance Company', required=True, ondelete='restrict')
    pricing_id = fields.Many2one(
        'insurance.company.pricing', string='Pricing Config', ondelete='set null')

    # Source type — how was this quote obtained
    source_type = fields.Selection([
        ('manual', 'Manual Entry / يدوي'),
        ('portal', 'Direct Portal / بوابة مباشرة'),
        ('api', 'API Integration / API'),
    ], string='Quote Source', default='manual', required=True)

    status = fields.Selection([
        ('pending', 'Pending Entry'),
        ('awaiting_api', 'Awaiting API Response'),
        ('quoted', 'Quote Received'),
        ('rejected', 'Rejected / No Quote'),
    ], string='Status', default='pending', tracking=True)

    # Pricing
    base_premium = fields.Float(string='Base Premium (OMR)', digits=(10, 3))
    premium = fields.Float(string='Final Premium (OMR)', digits=(10, 3))
    deductible = fields.Float(string='Deductible (OMR)', digits=(10, 3))
    discount_pct = fields.Float(string='Discount %')
    tax_amount = fields.Float(string='Tax / VAT (OMR)', digits=(10, 3))
    total_amount = fields.Float(
        string='Total Amount (OMR)', compute='_compute_total', store=True, digits=(10, 3))

    # Coverage details
    coverage_summary = fields.Html(string='Coverage Summary')
    exclusions = fields.Text(string='Exclusions')
    add_ons = fields.Text(string='Add-ons / Benefits')
    network = fields.Char(string='Network / TPA')
    validity_date = fields.Date(string='Quote Valid Until')

    # Portal direct access
    portal_direct_url = fields.Char(
        string='Direct Portal Link',
        compute='_compute_portal_direct_url',
        help='Click to open the insurance company portal directly (pre-authenticated).',
    )
    portal_session_token = fields.Char(
        string='Session Token', copy=False,
        help='Auto-generated token for direct portal access without re-login.',
    )

    # Entry tracking
    entered_by = fields.Many2one('res.users', string='Entered By', readonly=True)
    entered_at = fields.Datetime(string='Entered At', readonly=True)
    api_response_raw = fields.Text(string='API Raw Response', readonly=True)
    is_recommended = fields.Boolean(string='Recommended', default=False)

    notes = fields.Text(string='Notes')

    # ── Computed ──────────────────────────────────────────────────────────────────
    @api.depends('premium', 'tax_amount', 'discount_pct')
    def _compute_total(self):
        for rec in self:
            discounted = rec.premium * (1 - rec.discount_pct / 100)
            rec.total_amount = discounted + rec.tax_amount

    @api.depends('company_id', 'quotation_id', 'portal_session_token')
    def _compute_portal_direct_url(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for rec in self:
            if rec.source_type == 'portal' and rec.company_id.integration_type == 'portal':
                if rec.portal_session_token:
                    rec.portal_direct_url = (
                        f'{base}/insurance/direct-portal/{rec.portal_session_token}'
                    )
                elif rec.company_id.direct_access_url:
                    rec.portal_direct_url = rec.company_id.direct_access_url
                else:
                    rec.portal_direct_url = rec.company_id.portal_login_url or ''
            elif rec.pricing_id and rec.pricing_id.portal_product_url:
                rec.portal_direct_url = rec.pricing_id.portal_product_url
            else:
                rec.portal_direct_url = ''

    def action_generate_session_token(self):
        """Generate a direct-access session token for this quotation line."""
        for rec in self:
            rec.portal_session_token = secrets.token_urlsafe(32)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Token Generated',
                'message': 'Direct portal access link generated.',
                'type': 'success',
            }
        }

    def action_open_portal(self):
        """Open the company portal directly (for employees)."""
        self.ensure_one()
        url = self.portal_direct_url or self.company_id.portal_login_url or self.company_id.website
        if url:
            return {'type': 'ir.actions.act_url', 'url': url, 'target': 'new'}

    def action_mark_quoted(self):
        from datetime import datetime
        self.write({
            'status': 'quoted',
            'entered_by': self.env.user.id,
            'entered_at': datetime.now(),
        })

    def action_mark_recommended(self):
        # Remove recommendation from siblings
        self.quotation_id.line_ids.write({'is_recommended': False})
        self.write({'is_recommended': True})
        self.quotation_id.recommended_line_id = self.id
