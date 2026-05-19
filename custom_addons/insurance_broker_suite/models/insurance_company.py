from odoo import models, fields, api
import secrets

FINANCIAL_RATING_SELECTION = [
    ('AAA', 'AAA — Exceptional'),
    ('AA+', 'AA+ — Excellent'),
    ('AA',  'AA — Excellent'),
    ('AA-', 'AA- — Excellent'),
    ('A+',  'A+ — Good'),
    ('A',   'A — Good'),
    ('A-',  'A- — Good'),
    ('BBB', 'BBB — Adequate'),
    ('BB',  'BB — Speculative'),
    ('B',   'B — Speculative'),
    ('NR',  'NR — Not Rated'),
]


class InsuranceCompanyProvider(models.Model):
    _name = 'insurance.company.provider'
    _description = 'Insurance Company / Provider'
    _order = 'name'

    name = fields.Char(string='Company Name', required=True)
    name_ar = fields.Char(string='Arabic Name')
    code = fields.Char(string='Company Code')
    logo = fields.Image(string='Logo', max_width=256, max_height=256)
    website = fields.Char(string='Website')
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    country_id = fields.Many2one('res.country', string='Country')
    address = fields.Text(string='Address')
    active = fields.Boolean(default=True)
    notes = fields.Text(string='Notes')

    # الربط مع الموردين (Vendors) للحسابات المالية
    partner_id = fields.Many2one(
        'res.partner', 
        string='Related Vendor / Partner', 
        readonly=True, 
        ondelete='restrict',
        help='The linked vendor record for financial accounting.'
    )

    # Insurance types this company covers
    category_ids = fields.Many2many(
        'insurance.category',
        string='Coverage Categories',
        help='Types of insurance this company provides',
    )
    type_ids = fields.Many2many(
        'insurance.type',
        'insurance_company_type_rel',
        'company_id', 'type_id',
        string='Insurance Types Offered',
        help='Specific insurance types this company underwrites (used for RFQ routing)',
    )

    # Financial Rating — Standard & Poor / AM Best style
    rating = fields.Selection(
        FINANCIAL_RATING_SELECTION,
        string='Financial Rating',
        help='Credit / financial strength rating (e.g. AM Best, S&P)',
    )

    license_number = fields.Char(string='License Number')
    license_expiry = fields.Date(string='License Expiry Date')

    # ── Provider Portal ────────────────────────────────────────────────────────
    portal_active = fields.Boolean(
        string='Portal Access Enabled',
        default=True,
        help='Allow this provider to access the RFQ portal and submit quotes online.',
    )
    portal_token = fields.Char(
        string='Portal Access Token',
        copy=False,
        readonly=True,
        help='Unique secret token for portal/API access. Share securely with the provider.',
    )
    portal_url = fields.Char(
        string='Portal URL',
        compute='_compute_portal_url',
        help='Direct URL for the provider to access their RFQ portal.',
    )

    @api.depends('portal_token')
    def _compute_portal_url(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for rec in self:
            if rec.portal_token:
                rec.portal_url = f'{base}/insurance/provider/?token={rec.portal_token}'
            else:
                rec.portal_url = ''

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # 1. توليد التوكن الخاص بالبوابة
            if not vals.get('portal_token'):
                vals['portal_token'] = secrets.token_urlsafe(32)
            
            # 2. إنشاء المورد (Vendor) في جهات الاتصال والحسابات
            partner_vals = {
                'name': vals.get('name'),
                'email': vals.get('email'),
                'phone': vals.get('phone'),
                'website': vals.get('website'),
                'country_id': vals.get('country_id'),
                'is_company': True,
                'supplier_rank': 1, # هذا الحقل يجعله يظهر في قائمة الموردين
            }
            # إنشاء الـ Partner وربطه بالحقل
            partner = self.env['res.partner'].sudo().create(partner_vals)
            vals['partner_id'] = partner.id

        return super().create(vals_list)

    def write(self, vals):
        """ تحديث بيانات المورد المرتبط عند تعديل بيانات شركة التأمين """
        res = super().write(vals)
        
        # تجهيز الحقول التي سيتم تحديثها في المورد
        partner_vals = {}
        if 'name' in vals: partner_vals['name'] = vals['name']
        if 'email' in vals: partner_vals['email'] = vals['email']
        if 'phone' in vals: partner_vals['phone'] = vals['phone']
        if 'website' in vals: partner_vals['website'] = vals['website']
        if 'country_id' in vals: partner_vals['country_id'] = vals['country_id']
        
        if partner_vals:
            for rec in self:
                if rec.partner_id:
                    rec.partner_id.sudo().write(partner_vals)
                    
        return res

    def action_regenerate_token(self):
        for rec in self:
            rec.portal_token = secrets.token_urlsafe(32)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Token Regenerated',
                'message': 'A new portal access token has been generated. Update the provider with the new Portal URL.',
                'type': 'success',
            }
        }

    def action_send_portal_invite(self):
        """Send portal invitation email to provider."""
        self.ensure_one()
        if not self.email:
            raise ValueError('Provider has no email address configured.')
        if not self.portal_token:
            self.portal_token = secrets.token_urlsafe(32)
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        url = f'{base}/insurance/provider/?token={self.portal_token}'
        self.env['mail.mail'].sudo().create({
            'subject': 'Invitation: Ameen Hub Insurance Broker — Provider Portal Access',
            'email_to': self.email,
            'body_html': f'''
                <p>Dear <strong>{self.name}</strong>,</p>
                <p>You have been invited to join the <strong>Ameen Hub Insurance Brokerage</strong> provider portal.</p>
                <p>Through this portal you can:</p>
                <ul>
                    <li>Receive Request for Quotation (RFQ) from our brokers</li>
                    <li>Submit competitive quotes online</li>
                    <li>Track the status of your submitted quotes</li>
                    <li>Integrate via REST API for automated quote submission</li>
                </ul>
                <p><a href="{url}" style="background:#059669;color:#fff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:bold;">
                    Access Provider Portal
                </a></p>
                <p>Or copy this link:<br><code>{url}</code></p>
                <p>Best regards,<br>Ameen Hub Insurance Brokerage Team</p>
            '''
        }).send()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Invitation Sent',
                'message': f'Portal invitation sent to {self.email}.',
                'type': 'success',
            }
        }
