from odoo import models, fields, api


class InsuranceCompanyPricing(models.Model):
    """
    تسعيرة شركة التأمين لمنتج معين (فرعي).
    كل شركة يمكن أن يكون لها سعر مختلف لكل نوع فرعي من التأمين.
    """
    _name = 'insurance.company.pricing'
    _description = 'Insurance Company Product Pricing'
    _order = 'company_id, sequence'
    _rec_name = 'display_name'

    company_id = fields.Many2one(
        'insurance.company.provider',
        string='Insurance Company / شركة التأمين',
        required=True,
        ondelete='cascade',
        index=True,
    )
    subtype_id = fields.Many2one(
        'insurance.subtype',
        string='Insurance Sub-Type / النوع الفرعي',
        required=True,
        ondelete='restrict',
        index=True,
    )
    type_id = fields.Many2one(
        'insurance.type',
        related='subtype_id.type_id',
        store=True,
        readonly=True,
        string='Insurance Type',
    )
    category_id = fields.Many2one(
        'insurance.category',
        related='subtype_id.category_id',
        store=True,
        readonly=True,
        string='Category',
    )

    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    # ── Pricing ──────────────────────────────────────────────────────────────────
    base_premium = fields.Float(string='Base Premium (OMR)', digits=(10, 3))
    min_premium = fields.Float(string='Min Premium (OMR)', digits=(10, 3))
    max_premium = fields.Float(string='Max Premium (OMR)', digits=(10, 3))
    currency = fields.Char(string='Currency', default='OMR')
    pricing_notes = fields.Text(string='Pricing Notes / ملاحظات التسعيرة')

    # ── Coverage & Details ────────────────────────────────────────────────────────
    coverage_summary = fields.Html(string='Coverage Summary / ملخص التغطية')
    exclusions = fields.Text(string='Exclusions / الاستثناءات')
    add_ons = fields.Text(string='Add-ons Available / الإضافات المتاحة')

    # ── Integration override per product ─────────────────────────────────────────
    # يمكن لكل منتج أن يتجاوز إعداد الشركة الافتراضي
    override_integration = fields.Boolean(
        string='Override Company Integration',
        default=False,
        help='Enable to set a different integration type for this specific product.',
    )
    integration_type = fields.Selection([
        ('manual', 'Manual Entry'),
        ('portal', 'Direct Portal'),
        ('api', 'API Integration'),
    ], string='Product Integration Type',
        help='Override the company-level integration type for this specific product.',
    )

    # For portal override
    portal_product_url = fields.Char(
        string='Product Portal URL',
        help='Direct URL to this specific product on the company portal.',
    )
    # For API override
    api_endpoint_override = fields.Char(
        string='API Endpoint Override',
        help='Override the company default API endpoint for this product.',
    )

    # ── Computed display name ─────────────────────────────────────────────────────
    display_name = fields.Char(compute='_compute_display_name', store=True)

    @api.depends('company_id', 'subtype_id')
    def _compute_display_name(self):
        for rec in self:
            company = rec.company_id.name or ''
            subtype = rec.subtype_id.name or ''
            rec.display_name = f'{company} — {subtype}' if company and subtype else company or subtype

    def get_effective_integration_type(self):
        """Returns the effective integration type for this pricing record."""
        self.ensure_one()
        if self.override_integration and self.integration_type:
            return self.integration_type
        return self.company_id.integration_type or 'manual'

    def get_effective_portal_url(self):
        """Returns the effective direct access URL for portal-type integration."""
        self.ensure_one()
        if self.override_integration and self.portal_product_url:
            return self.portal_product_url
        return self.company_id.direct_access_url or ''


class InsuranceSubtypePricingWizard(models.TransientModel):
    """Wizard to quickly add pricing for multiple companies at once."""
    _name = 'insurance.subtype.pricing.wizard'
    _description = 'Bulk Pricing Setup Wizard'

    subtype_id = fields.Many2one('insurance.subtype', string='Sub-Type', required=True)
    company_ids = fields.Many2many(
        'insurance.company.provider',
        string='Companies to Configure',
    )
    base_premium = fields.Float(string='Default Base Premium (OMR)', digits=(10, 3))
    notes = fields.Text(string='Notes')

    def action_create_pricing(self):
        self.ensure_one()
        for company in self.company_ids:
            existing = self.env['insurance.company.pricing'].search([
                ('company_id', '=', company.id),
                ('subtype_id', '=', self.subtype_id.id),
            ], limit=1)
            if not existing:
                self.env['insurance.company.pricing'].create({
                    'company_id': company.id,
                    'subtype_id': self.subtype_id.id,
                    'base_premium': self.base_premium,
                    'pricing_notes': self.notes,
                })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Pricing Created',
                'message': f'Pricing configured for {len(self.company_ids)} companies.',
                'type': 'success',
            }
        }
