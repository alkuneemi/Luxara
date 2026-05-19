from odoo import models, fields, api, _


class InsuranceSource(models.Model):
    """الموديل الخاص بمصادر التأمين"""
    _name = 'insurance.source'
    _description = 'Insurance Source Master'
    _rec_name = 'name'

    name = fields.Char(string='Source Name', required=True, translate=True)
    code = fields.Char(string='Code', required=True)


class InsuranceOpportunity(models.Model):
    """
    نموذج فرص التأمين — موروث من crm.lead عبر _inherits (delegation inheritance)
    """
    _name = 'insurance.opportunity'
    _description = 'Insurance Opportunity'
    _inherits = {'crm.lead': 'lead_id'}
    _rec_name = 'name'
    _order = 'create_date desc'

    # ── Delegation link ────────────────────────────────────────────────────────
    lead_id = fields.Many2one(
        'crm.lead',
        string='CRM Lead',
        required=True,
        ondelete='cascade',
        auto_join=True,
        index=True,
    )
    stage = fields.Many2one(
        related='lead_id.stage_id',
        string='المرحلة / Stage',
        readonly=False,
        store=True,
        domain="['|', ('team_id', '=', False), ('team_id', '=', team_id)]",
        tracking=True,
    )

    # ── Insurance selection ───────────────────────────────────────────────────
    ins_category_id = fields.Many2one(
        'insurance.category',
        string='فئة التأمين / Insurance Category',
        tracking=True,
    )
    ins_type_id = fields.Many2one(
        'insurance.type',
        string='نوع التأمين / Insurance Type',
        tracking=True,
        domain="[('category_id', '=', ins_category_id)]",
    )
    ins_subtype_id = fields.Many2one(
        'insurance.subtype',
        string='النوع الفرعي / Insurance Sub-Type',
        tracking=True,
        domain="[('type_id', '=', ins_type_id)]",
    )

    # ── Insurance source ──────────────────────────────────────────────────────
    ins_source_id = fields.Many2one(
        'insurance.source',
        string='Insurance Source',
        tracking=True,
    )

    # ── Linked insurance records ───────────────────────────────────────────────
    application_id = fields.Many2one(
        'insurance.application', string='Insurance Application', readonly=True)
    sales_application_id = fields.Many2one(
        'insurance.application',
        string='Sales Order / طلب المبيعات',
        readonly=True,
        domain="[('channel', '=', 'sales')]",
    )

    # ── AI session tracking ───────────────────────────────────────────────────
    ai_session_id = fields.Char(string='AI Session ID', index=True)
    ai_conversation = fields.Text(string='AI Conversation Log')

    # ── Computed portal URL ───────────────────────────────────────────────────
    portal_url = fields.Char(string='Portal URL', compute='_compute_portal_url')

    # ── Website Funnel Tracking ───────────────────────────────────────────────
    current_funnel_step = fields.Selection(
        related='lead_id.current_funnel_step',
        string='Funnel Step',
        readonly=False,
        store=True,
    )
    last_category_id = fields.Many2one(
        related='lead_id.last_category_id',
        string='Last Category',
        readonly=False,
        store=True,
    )
    last_type_id = fields.Many2one(
        related='lead_id.last_type_id',
        string='Last Type',
        readonly=False,
        store=True,
    )
    last_subtype_id = fields.Many2one(
        related='lead_id.last_subtype_id',
        string='Last Subtype',
        readonly=False,
        store=True,
    )
    journey_log_ids = fields.One2many(
        related='lead_id.journey_log_ids',
        string='Journey Log',
        readonly=True,
    )
    journey_log_count = fields.Integer(
        related='lead_id.journey_log_count',
        string='Log Entries',
        readonly=True,
    )

    # ── Related fields from application_id (for Requirement Details tab) ──────
    # Odoo does NOT allow "application_id.field_name" syntax in view <field> tags.
    # These related fields proxy the application fields so the view can use them directly.

    app_form_type = fields.Selection(
        related='application_id.form_type', readonly=True, store=False)

    # Personal / Contact
    app_customer_name  = fields.Char(related='application_id.customer_name',  readonly=True, store=False)
    app_id_number      = fields.Char(related='application_id.id_number',      readonly=True, store=False)
    app_customer_phone = fields.Char(related='application_id.customer_phone', readonly=True, store=False)
    app_customer_email = fields.Char(related='application_id.customer_email', readonly=True, store=False)
    app_nationality    = fields.Char(related='application_id.nationality',    readonly=True, store=False)
    app_date_of_birth  = fields.Date(related='application_id.date_of_birth',  readonly=True, store=False)
    app_gender         = fields.Selection(related='application_id.gender',    readonly=True, store=False)

    # Motor / Vehicle
    app_motor_full_name        = fields.Char(related='application_id.motor_full_name',        readonly=True, store=False)
    app_motor_license_number   = fields.Char(related='application_id.motor_license_number',   readonly=True, store=False)
    app_motor_plate_number     = fields.Char(related='application_id.motor_plate_number',     readonly=True, store=False)
    app_motor_plate_character  = fields.Char(related='application_id.motor_plate_character',  readonly=True, store=False)
    app_motor_year             = fields.Char(related='application_id.motor_year',             readonly=True, store=False)
    app_motor_make             = fields.Char(related='application_id.motor_make',             readonly=True, store=False)
    app_motor_model            = fields.Char(related='application_id.motor_model',            readonly=True, store=False)
    app_motor_chassis_number   = fields.Char(related='application_id.motor_chassis_number',   readonly=True, store=False)
    app_motor_engine_cc        = fields.Char(related='application_id.motor_engine_cc',        readonly=True, store=False)
    app_motor_seating_capacity = fields.Integer(related='application_id.motor_seating_capacity', readonly=True, store=False)
    app_motor_is_financed      = fields.Boolean(related='application_id.motor_is_financed',   readonly=True, store=False)
    app_motor_finance_company  = fields.Char(related='application_id.motor_finance_company',  readonly=True, store=False)
    app_motor_color            = fields.Char(related='application_id.motor_color',            readonly=True, store=False)

    # Medical
    app_med_coverage_type      = fields.Char(related='application_id.med_coverage_type',      readonly=True, store=False)
    app_med_employee_count     = fields.Integer(related='application_id.med_employee_count',  readonly=True, store=False)
    app_med_dependents_count   = fields.Integer(related='application_id.med_dependents_count', readonly=True, store=False)
    app_med_network_preference = fields.Selection(related='application_id.med_network_preference', readonly=True, store=False)
    app_med_dental_required    = fields.Boolean(related='application_id.med_dental_required', readonly=True, store=False)
    app_med_optical_required   = fields.Boolean(related='application_id.med_optical_required', readonly=True, store=False)
    app_med_pre_existing       = fields.Boolean(related='application_id.med_pre_existing',    readonly=True, store=False)
    app_med_company_name       = fields.Char(related='application_id.med_company_name',       readonly=True, store=False)

    # Property / Fire
    app_prop_proposer_name     = fields.Char(related='application_id.prop_proposer_name',     readonly=True, store=False)
    app_prop_address           = fields.Char(related='application_id.prop_address',           readonly=True, store=False)
    app_prop_cover_type        = fields.Char(related='application_id.prop_cover_type',        readonly=True, store=False)
    app_prop_usage             = fields.Char(related='application_id.prop_usage',             readonly=True, store=False)
    app_prop_building_value    = fields.Float(related='application_id.prop_building_value',   readonly=True, store=False)
    app_prop_contents_value    = fields.Float(related='application_id.prop_contents_value',   readonly=True, store=False)
    app_prop_construction_type = fields.Char(related='application_id.prop_construction_type', readonly=True, store=False)
    app_prop_any_previous_loss = fields.Boolean(related='application_id.prop_any_previous_loss', readonly=True, store=False)

    # Marine
    app_marine_voyage_from   = fields.Char(related='application_id.marine_voyage_from',    readonly=True, store=False)
    app_marine_voyage_to     = fields.Char(related='application_id.marine_voyage_to',      readonly=True, store=False)
    app_marine_departure_date = fields.Date(related='application_id.marine_departure_date', readonly=True, store=False)
    app_marine_arrival_date  = fields.Date(related='application_id.marine_arrival_date',   readonly=True, store=False)
    app_marine_cargo_type    = fields.Char(related='application_id.marine_cargo_type',     readonly=True, store=False)
    app_marine_cargo_value   = fields.Float(related='application_id.marine_cargo_value',   readonly=True, store=False)
    app_marine_vessel_name   = fields.Char(related='application_id.marine_vessel_name',    readonly=True, store=False)

    # Life
    app_life_sum_assured       = fields.Float(related='application_id.life_sum_assured',        readonly=True, store=False)
    app_life_policy_term       = fields.Integer(related='application_id.life_policy_term',      readonly=True, store=False)
    app_life_payment_frequency = fields.Selection(related='application_id.life_payment_frequency', readonly=True, store=False)
    app_life_beneficiary_name  = fields.Char(related='application_id.life_beneficiary_name',    readonly=True, store=False)
    app_life_occupation        = fields.Char(related='application_id.life_occupation',          readonly=True, store=False)
    app_life_smoker            = fields.Boolean(related='application_id.life_smoker',           readonly=True, store=False)
    app_life_hazardous_activity = fields.Boolean(related='application_id.life_hazardous_activity', readonly=True, store=False)

    # Workmen Compensation
    app_wc_company_name      = fields.Char(related='application_id.wc_company_name',         readonly=True, store=False)
    app_wc_employee_count    = fields.Integer(related='application_id.wc_employee_count',    readonly=True, store=False)
    app_wc_total_annual_wages = fields.Float(related='application_id.wc_total_annual_wages', readonly=True, store=False)
    app_wc_business_nature   = fields.Char(related='application_id.wc_business_nature',     readonly=True, store=False)
    app_wc_any_previous_claims = fields.Boolean(related='application_id.wc_any_previous_claims', readonly=True, store=False)

    # Documents
    app_document_ids = fields.Many2many(
        related='application_id.document_ids', readonly=True, string='Uploaded Documents')

    # ── Computed portal URL ───────────────────────────────────────────────────
    @api.depends('application_id')
    def _compute_portal_url(self):
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for rec in self:
            if rec.application_id:
                rec.portal_url = f'{base}/my/insurance/{rec.application_id.id}'
            else:
                rec.portal_url = f'{base}/my/insurance'

    # ── Cascading onchange ────────────────────────────────────────────────────
    @api.onchange('ins_category_id')
    def _onchange_ins_category_id(self):
        self.ins_type_id = False
        self.ins_subtype_id = False

    @api.onchange('ins_type_id')
    def _onchange_ins_type_id(self):
        self.ins_subtype_id = False

    # ── Funnel advance wrapper ────────────────────────────────────────────────
    def _funnel_advance(self, step, action_name, page_url=None, **extra_vals):
        self.ensure_one()
        return self.lead_id._funnel_advance(
            step, action_name=action_name, page_url=page_url, **extra_vals)

    # ── Anti-duplication website opportunity creation ─────────────────────────
    @api.model
    def _get_or_create_for_partner(self, partner):
        existing = self.search([
            ('partner_id', '=', partner.id),
            ('type', '=', 'opportunity'),
            ('active', '=', True),
            ('stage_id.is_won', '=', False),
        ], limit=1)
        if existing:
            return existing

        stage = self.env['crm.stage'].sudo().search([], limit=1, order='sequence asc')
        website_source = self.env['insurance.source'].sudo().search([('code', '=', 'website')], limit=1)

        opp = self.sudo().create({
            'type': 'opportunity',
            'name': f'Website Insurance — {partner.name}',
            'partner_id': partner.id,
            'contact_name': partner.name,
            'email_from': partner.email or '',
            'phone': partner.phone or '',
            'stage_id': stage.id if stage else False,
            'ins_source_id': website_source.id if website_source else False,
            'description': (
                f'تم الإنشاء تلقائياً: العميل "{partner.name}" زار '
                f'صفحة التأمين على الموقع.'
            ),
        })
        return opp

    # ── Auto-create Sales Application on Lead stage ───────────────────────────
    def write(self, vals):
        result = super().write(vals)
        if vals.get('stage_id'):
            stage = self.env['crm.stage'].browse(vals['stage_id'])
            if stage.sequence >= 2:
                for rec in self:
                    if not rec.sales_application_id and rec.ins_subtype_id:
                        app_vals = {
                            'channel': 'sales',
                            'customer_name': rec.contact_name or (rec.partner_id.name if rec.partner_id else 'Unknown'),
                            'customer_phone': rec.phone or '00000000',
                            'customer_email': rec.email_from or 'sales@company.com',
                            'partner_id': rec.partner_id.id if rec.partner_id else False,
                            'category_id': rec.ins_category_id.id if rec.ins_category_id else False,
                            'type_id': rec.ins_type_id.id if rec.ins_type_id else False,
                            'subtype_id': rec.ins_subtype_id.id if rec.ins_subtype_id else False,
                            'opportunity_id': rec.id,
                            'sales_agent_id': self.env.user.id,
                            'expected_revenue': rec.expected_revenue or 0.0,
                            'notes': rec.description or '',
                        }
                        sales_app = self.env['insurance.application'].sudo().create(app_vals)
                        rec.sales_application_id = sales_app.id
                        rec.lead_id.message_post(
                            body=_(
                                '✅ تم إنشاء طلب تأمين تلقائياً في سجل المبيعات.\n'
                                'رقم الطلب: %s'
                            ) % sales_app.reference,
                            message_type='notification',
                            subtype_xmlid='mail.mt_note',
                        )
        return result

    # ── Actions ───────────────────────────────────────────────────────────────
    def action_view_crm_lead(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'CRM Lead',
            'res_model': 'crm.lead',
            'res_id': self.lead_id.id,
            'view_mode': 'form',
        }

    def action_view_application(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Insurance Application',
            'res_model': 'insurance.application',
            'res_id': self.application_id.id,
            'view_mode': 'form',
        }

    def action_view_sales_order(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('طلب المبيعات / Sales Order'),
            'res_model': 'insurance.application',
            'res_id': self.sales_application_id.id,
            'view_mode': 'form',
        }
