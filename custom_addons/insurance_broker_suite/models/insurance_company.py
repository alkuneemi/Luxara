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

    partner_id = fields.Many2one(
        'res.partner',
        string='Related Vendor / Partner',
        readonly=True,
        ondelete='restrict',
        help='The linked vendor record for financial accounting.'
    )

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

    rating = fields.Selection(
        FINANCIAL_RATING_SELECTION,
        string='Financial Rating',
        help='Credit / financial strength rating (e.g. AM Best, S&P)',
    )

    license_number = fields.Char(string='License Number')
    license_expiry = fields.Date(string='License Expiry Date')

    # ── Integration Type ────────────────────────────────────────────────────────
    integration_type = fields.Selection([
        ('manual', 'Manual Entry / يدوي (موظف يدخل يدوياً)'),
        ('portal', 'Direct Portal / بوابة مباشرة (رابط مباشر بدون تسجيل دخول)'),
        ('api', 'API Integration / ربط API تلقائي'),
    ], string='Integration Type / نوع التكامل',
        default='manual',
        required=True,
        tracking=True,
        help='''
        Manual: موظفو البروكر يدخلون الأسعار يدوياً.
        Direct Portal: العميل يضغط رابط مباشر ويدخل بوابة الشركة بدون تسجيل دخول.
        API: الأسعار تُجلب تلقائياً من API الشركة.
        ''',
    )

    # ── Provider Portal (Token-based for RFQ submission) ───────────────────────
    portal_active = fields.Boolean(
        string='RFQ Portal Access Enabled',
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

    # ── Direct Portal Credentials (for integration_type = 'portal') ────────────
    portal_username = fields.Char(
        string='Portal Username / اسم المستخدم',
        copy=False,
        help='Username to login to the insurance company portal system.',
    )
    portal_password = fields.Char(
        string='Portal Password / كلمة المرور',
        copy=False,
        help='Password to login to the insurance company portal system.',
    )
    portal_login_url = fields.Char(
        string='Portal Login URL / رابط تسجيل الدخول',
        help='The login page URL of the insurance company portal.',
    )
    direct_access_token = fields.Char(
        string='Direct Access Token',
        copy=False,
        readonly=True,
        help='Auto-generated token for direct portal access link (bypasses login page).',
    )
    direct_access_url = fields.Char(
        string='Direct Access Link / رابط الدخول المباشر',
        compute='_compute_direct_access_url',
        help='Customer clicks this link and goes directly to the company portal without login.',
    )

    # ── API Integration Settings (for integration_type = 'api') ────────────────
    api_base_url = fields.Char(
        string='API Base URL',
        help='Base URL of the insurance company REST API.',
    )
    api_key = fields.Char(
        string='API Key',
        copy=False,
        help='Primary API key / access token for the insurance company API.',
    )
    api_secret = fields.Char(
        string='API Secret',
        copy=False,
        help='API secret key (if required by the provider).',
    )
    api_quote_endpoint = fields.Char(
        string='Quote Endpoint',
        default='/api/v1/quote',
        help='Endpoint to request a quotation. e.g. /api/v1/quote',
    )
    api_policy_endpoint = fields.Char(
        string='Policy Endpoint',
        default='/api/v1/policy',
        help='Endpoint to issue a policy.',
    )
    api_token_endpoint = fields.Char(
        string='Token / Auth Endpoint',
        help='OAuth2 or token endpoint if required. e.g. /api/auth/token',
    )
    api_documentation_url = fields.Char(
        string='API Documentation URL',
        help='Link to the API documentation provided by the company.',
    )
    api_extra_config = fields.Text(
        string='Extra API Config (JSON)',
        help='Additional configuration in JSON format, e.g. {"version": "2", "timeout": 30}',
    )
    api_test_mode = fields.Boolean(
        string='API Test/Sandbox Mode',
        default=False,
        help='When enabled, API calls are sent to the sandbox/test environment.',
    )

    # ── Pricing configurations ──────────────────────────────────────────────────
    pricing_ids = fields.One2many(
        'insurance.company.pricing',
        'company_id',
        string='Product Pricing / تسعيرة المنتجات',
    )
    pricing_count = fields.Integer(compute='_compute_pricing_count', string='Products Configured')

    # ── Computed ────────────────────────────────────────────────────────────────
    @api.depends('portal_token')
    def _compute_portal_url(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for rec in self:
            if rec.portal_token:
                rec.portal_url = f'{base}/insurance/provider/?token={rec.portal_token}'
            else:
                rec.portal_url = ''

    @api.depends('direct_access_token', 'portal_login_url', 'integration_type')
    def _compute_direct_access_url(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for rec in self:
            if rec.integration_type == 'portal' and rec.direct_access_token:
                rec.direct_access_url = f'{base}/insurance/direct-portal/{rec.direct_access_token}'
            else:
                rec.direct_access_url = ''

    @api.depends('pricing_ids')
    def _compute_pricing_count(self):
        for rec in self:
            rec.pricing_count = len(rec.pricing_ids)

    # ── Create / Write ──────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('portal_token'):
                vals['portal_token'] = secrets.token_urlsafe(32)
            if not vals.get('direct_access_token') and vals.get('integration_type') == 'portal':
                vals['direct_access_token'] = secrets.token_urlsafe(32)

            partner_vals = {
                'name': vals.get('name'),
                'email': vals.get('email'),
                'phone': vals.get('phone'),
                'website': vals.get('website'),
                'country_id': vals.get('country_id'),
                'is_company': True,
                'supplier_rank': 1,
            }
            partner = self.env['res.partner'].sudo().create(partner_vals)
            vals['partner_id'] = partner.id

        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        # Auto-generate direct access token when switching to portal type
        for rec in self:
            if rec.integration_type == 'portal' and not rec.direct_access_token:
                rec.direct_access_token = secrets.token_urlsafe(32)

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

    # ── Actions ─────────────────────────────────────────────────────────────────
    def action_regenerate_token(self):
        for rec in self:
            rec.portal_token = secrets.token_urlsafe(32)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Token Regenerated',
                'message': 'A new portal access token has been generated.',
                'type': 'success',
            }
        }

    def action_regenerate_direct_access_token(self):
        """Regenerate the direct portal access token."""
        for rec in self:
            rec.direct_access_token = secrets.token_urlsafe(32)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Direct Access Token Regenerated',
                'message': 'New direct access link generated. Share it with the customer.',
                'type': 'success',
            }
        }

    def action_test_api_connection(self):
        """Test the API connection for API-integrated companies."""
        self.ensure_one()
        if self.integration_type != 'api':
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Not Applicable',
                    'message': 'API test is only for companies with API Integration type.',
                    'type': 'warning',
                }
            }
        if not self.api_base_url:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Missing API URL',
                    'message': 'Please set the API Base URL first.',
                    'type': 'danger',
                }
            }
        try:
            import urllib.request
            import urllib.error
            import json
            url = self.api_base_url.rstrip('/') + '/ping'
            headers = {}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
                headers['X-Api-Key'] = self.api_key
            req = urllib.request.Request(url, headers=headers, method='GET')
            with urllib.request.urlopen(req, timeout=10) as resp:
                status = resp.status
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': 'API Connected',
                        'message': f'API connection successful. HTTP Status: {status}',
                        'type': 'success',
                    }
                }
        except Exception as e:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'API Connection Failed',
                    'message': f'Could not connect: {str(e)}',
                    'type': 'danger',
                }
            }

    def action_view_pricing(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': f'Pricing — {self.name}',
            'res_model': 'insurance.company.pricing',
            'view_mode': 'list,form',
            'domain': [('company_id', '=', self.id)],
            'context': {'default_company_id': self.id},
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
