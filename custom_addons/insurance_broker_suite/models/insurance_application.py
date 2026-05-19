from odoo import models, fields, api
from odoo.exceptions import ValidationError


class InsuranceApplication(models.Model):
    _name = 'insurance.application'
    _description = 'Online Insurance Application'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'reference'
    _order = 'create_date desc'

    reference = fields.Char(
        string='Reference', readonly=True, copy=False,
        default=lambda self: self.env['ir.sequence'].next_by_code('insurance.application'),
    )

    # ─── CHANNEL: قناة الطلب ────────────────────────────────────────────────────
    # online = طلبات البوابة الإلكترونية (الوضع الأصلي)
    # sales  = طلبات فريق المبيعات (مع نظام العمولة)
    # general = طلبات عامة
    channel = fields.Selection([
        ('online',  'Online Portal / أونلاين'),
        ('sales',   'Sales Team / فريق المبيعات'),
        ('general', 'General / عام'),
    ], string='Channel / القناة', default='online', tracking=True, index=True,
        help='قناة الطلب: أونلاين أو فريق مبيعات أو عام')

    # ─── Insurance selection ─────────────────────────────────────────────────────
    # IMPORTANT: category_id و type_id أصبحا حقلان مستقلان بدلاً من related
    # يتم تعبئتهما تلقائياً عند اختيار subtype_id، وكذلك عبر onchange للتسلسل
    category_id = fields.Many2one(
        'insurance.category', string='Category / الفئة',
        store=True, tracking=True,
        help='يتم تعبئته تلقائياً عند اختيار النوع الفرعي'
    )
    type_id = fields.Many2one(
        'insurance.type', string='Insurance Type / نوع التأمين',
        store=True, tracking=True,
        domain="[('category_id', '=', category_id)]",
        help='يتم تعبئته تلقائياً عند اختيار النوع الفرعي'
    )
    subtype_id = fields.Many2one(
        'insurance.subtype', string='Insurance Sub-Type', required=True,
        tracking=True, ondelete='restrict',
        domain="[('type_id', '=', type_id)]",
    )
    form_type = fields.Selection(related='subtype_id.form_type', string='Form Type', store=True)

    # Customer
    partner_id = fields.Many2one('res.partner', string='Customer', tracking=True)
    customer_name = fields.Char(string='Full Name', required=True, tracking=True)
    customer_email = fields.Char(string='Email', required=True, tracking=True)
    customer_phone = fields.Char(string='Phone', required=True, tracking=True)
    id_number = fields.Char(string='ID / Civil Number', tracking=True)
    nationality = fields.Char(string='Nationality')
    date_of_birth = fields.Date(string='Date of Birth')
    gender = fields.Selection([('male', 'Male'), ('female', 'Female')], string='Gender')

    # Status
    status = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('under_review', 'Under Review'),
        ('info_required', 'Information Required'),
        ('approved', 'Approved / Quoted'),
        ('rejected', 'Rejected'),
        ('policy_issued', 'Policy Issued'),
    ], string='Status', default='draft', tracking=True)

    # Admin fields
    admin_notes = fields.Html(string='Internal Notes')
    requirement_message = fields.Html(
        string='Requirements Message',
        help='Message shown to customer when additional info is required',
        tracking=True,
    )
    quoted_premium = fields.Float(string='Quoted Premium (OMR)', tracking=True)
    assigned_to = fields.Many2one('res.users', string='Assigned To', tracking=True)

    # Linked policy (after issue)
    policy_id = fields.Many2one('insurance.policy', string='Resulting Policy', readonly=True)

    # Documents
    document_ids = fields.Many2many(
        'ir.attachment', 'insurance_application_attachment_rel',
        'application_id', 'attachment_id',
        string='Uploaded Documents',
    )

    # ─── SALES TEAM FIELDS — حقول فريق المبيعات ─────────────────────────────────
    # تظهر فقط عندما channel = 'sales'
    sales_agent_id = fields.Many2one(
        'res.users', string='Sales Agent / مندوب المبيعات',
        tracking=True, domain="[('share', '=', False)]",
    )
    sales_team_id = fields.Many2one(
        'crm.team', string='Sales Team / فريق المبيعات', tracking=True
    )
    commission_rate = fields.Float(
        string='Commission Rate % / نسبة العمولة', default=10.0
    )
    commission_amount = fields.Float(
        string='Commission Amount (OMR) / مبلغ العمولة',
        compute='_compute_commission_amount',
        store=True,
    )
    commission_paid = fields.Boolean(
        string='Commission Paid / العمولة مدفوعة', tracking=True
    )
    commission_paid_date = fields.Date(
        string='Commission Payment Date / تاريخ دفع العمولة'
    )

    # Link to source opportunity (for sales channel)
    opportunity_id = fields.Many2one(
        'insurance.opportunity', string='Source Opportunity / الفرصة المصدر',
        readonly=True, ondelete='set null',
    )

    # ─── MOTOR FIELDS ───────────────────────────────────────────────────────────
    motor_full_name = fields.Char(string='Full Name (as on licence)')
    motor_id_number = fields.Char(string='ID / Civil Number')
    motor_plate_number = fields.Char(string='Plate Number')
    motor_plate_character = fields.Char(string='Plate Characters (English)')
    motor_license_number = fields.Char(string='Driving Licence Number')
    motor_vehicle_registration_date = fields.Date(string='Vehicle First Registration Date')
    motor_chassis_number = fields.Char(string='Chassis Number')
    motor_make = fields.Char(string='Vehicle Make')
    motor_model = fields.Char(string='Vehicle Model')
    motor_year = fields.Integer(string='Vehicle Year')
    motor_color = fields.Char(string='Vehicle Color')
    motor_engine_cc = fields.Integer(string='Engine CC')
    motor_seating_capacity = fields.Integer(string='Seating Capacity')
    motor_is_financed = fields.Boolean(string='Under Finance / Leasing?')
    motor_finance_company = fields.Char(string='Finance Company')

    # ─── MEDICAL FIELDS ─────────────────────────────────────────────────────────
    med_coverage_type = fields.Selection([
        ('individual', 'Individual'),
        ('family', 'Family'),
        ('group', 'Group / Corporate'),
    ], string='Coverage Type')
    med_employee_count = fields.Integer(string='Number of Employees / Members')
    med_dependents_count = fields.Integer(string='Number of Dependents')
    med_network_preference = fields.Selection([
        ('a', 'Network A (Premium)'),
        ('b', 'Network B (Standard)'),
        ('any', 'Any Network'),
    ], string='Network Preference')
    med_dental_required = fields.Boolean(string='Dental Coverage Required?')
    med_optical_required = fields.Boolean(string='Optical Coverage Required?')
    med_pre_existing = fields.Boolean(string='Any Pre-existing Conditions?')
    med_pre_existing_details = fields.Text(string='Pre-existing Condition Details')
    med_company_name = fields.Char(string='Company / Organization Name')

    # ─── PROPERTY / FIRE FIELDS ─────────────────────────────────────────────────
    prop_address = fields.Text(string='Property Address')
    prop_cover_type = fields.Selection([
        ('fire_only', 'Fire Only'),
        ('fire_theft', 'Fire & Theft'),
        ('fire_allied', 'Fire & Allied Perils'),
        ('comprehensive', 'Comprehensive'),
    ], string='Cover Type')
    prop_usage = fields.Selection([
        ('residential', 'Residential'),
        ('commercial', 'Commercial'),
        ('industrial', 'Industrial'),
        ('warehouse', 'Warehouse'),
        ('office', 'Office'),
        ('other', 'Other'),
    ], string='Property Usage')
    prop_building_value = fields.Float(string='Building Value (OMR)')
    prop_contents_value = fields.Float(string='Contents Value (OMR)')
    prop_any_previous_loss = fields.Boolean(string='Any Previous Loss / Claim?')
    prop_previous_loss_details = fields.Text(string='Previous Loss Details')
    prop_proposer_name = fields.Char(string='Proposer Full Name')
    prop_profession_business = fields.Char(string='Profession / Business')
    prop_any_rejection = fields.Boolean(string='Any Previous Insurance Rejection?')
    prop_rejection_details = fields.Text(string='Rejection Details')
    prop_construction_type = fields.Char(string='Construction Type')
    prop_year_built = fields.Integer(string='Year Built')

    # ─── MARINE FIELDS ──────────────────────────────────────────────────────────
    marine_voyage_from = fields.Char(string='Voyage From')
    marine_voyage_to = fields.Char(string='Voyage To')
    marine_departure_date = fields.Date(string='Departure Date')
    marine_arrival_date = fields.Date(string='Expected Arrival Date')
    marine_cargo_type = fields.Char(string='Cargo / Goods Type')
    marine_cargo_value = fields.Float(string='Cargo Value (OMR)')
    marine_vessel_name = fields.Char(string='Vessel / Ship Name')
    marine_packing = fields.Char(string='Packing / Container Type')

    # ─── LIFE FIELDS ────────────────────────────────────────────────────────────
    life_sum_assured = fields.Float(string='Sum Assured (OMR)')
    life_policy_term = fields.Integer(string='Policy Term (Years)')
    life_payment_frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('semi_annual', 'Semi-Annual'),
        ('annual', 'Annual'),
    ], string='Payment Frequency')
    life_beneficiary_name = fields.Char(string='Beneficiary Name')
    life_beneficiary_relation = fields.Char(string='Beneficiary Relationship')
    life_smoker = fields.Boolean(string='Smoker?')
    life_occupation = fields.Char(string='Occupation')
    life_hazardous_activity = fields.Boolean(string='Any Hazardous Activities?')

    # ─── WORKMEN COMPENSATION ───────────────────────────────────────────────────
    wc_company_name = fields.Char(string='Company Name')
    wc_employee_count = fields.Integer(string='Number of Employees')
    wc_total_annual_wages = fields.Float(string='Total Annual Wages (OMR)')
    wc_business_nature = fields.Char(string='Nature of Business')
    wc_any_previous_claims = fields.Boolean(string='Any Previous Claims?')

    # ─── Computed ───────────────────────────────────────────────────────────────
    @api.depends('quoted_premium', 'commission_rate')
    def _compute_commission_amount(self):
        for rec in self:
            rec.commission_amount = (rec.quoted_premium * rec.commission_rate) / 100.0

    # ─── Onchange — cascading fields ────────────────────────────────────────────
    @api.onchange('subtype_id')
    def _onchange_subtype_id(self):
        """Auto-fill category and type from the selected subtype."""
        if self.subtype_id:
            self.type_id = self.subtype_id.type_id
            self.category_id = self.subtype_id.category_id

    @api.onchange('category_id')
    def _onchange_category_id(self):
        """Reset type and subtype when category changes."""
        self.type_id = False
        self.subtype_id = False

    @api.onchange('type_id')
    def _onchange_type_id(self):
        """Reset subtype when type changes."""
        self.subtype_id = False

    # ─── Actions ─────────────────────────────────────────────────────────────────
    def action_submit(self):
        self.write({'status': 'submitted'})
        self.message_post(
            body='Application submitted by customer.',
            message_type='notification',
            subtype_xmlid='mail.mt_note',
        )

    def action_under_review(self):
        self.write({'status': 'under_review'})

    def action_request_info(self):
        self.write({'status': 'info_required'})

    def action_approve(self):
        self.write({'status': 'approved'})

    def action_reject(self):
        self.write({'status': 'rejected'})

    def action_issue_policy(self):
        self.write({'status': 'policy_issued'})

    def action_view_on_portal(self):
        return {
            'type': 'ir.actions.act_url',
            'url': f'/my/insurance/{self.id}',
            'target': 'new',
        }

    # ✅ كود Odoo 19 الصحيح
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('reference') or vals.get('reference') == '/':
                vals['reference'] = self.env['ir.sequence'].next_by_code(
                    'insurance.application'
                ) or 'APP-NEW'
        return super().create(vals_list)
