from odoo import models, fields, api, _


class InsuranceSource(models.Model):
    """الموديل الجديد الخاص بمصادر التأمين"""
    _name = 'insurance.source'
    _description = 'Insurance Source Master'
    _rec_name = 'name'

    name = fields.Char(string='Source Name', required=True, translate=True)
    code = fields.Char(string='Code', required=True) # الكود البرمجي للمطابقة إذا لزم الأمر


class InsuranceOpportunity(models.Model):
    """
    نموذج فرص التأمين — موروث من crm.lead عبر _inherits (delegation inheritance)
    يحتوي على جميع حقول crm.lead تلقائياً ويضيف حقول خاصة بالتأمين فوقها.
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
        help='مرحلة فرصة التأمين الحالية في نظام CRM',
    )

    # ── Insurance selection — cascading (فئة → نوع → فرعي) ───────────────────
    ins_category_id = fields.Many2one(
        'insurance.category',
        string='فئة التأمين / Insurance Category',
        tracking=True,
        help='اختر فئة التأمين أولاً ليظهر نوع التأمين مفلتراً',
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

    # ── Insurance source (تم تحويله إلى Many2one يعتمد على الاسم) ──────────────────
    ins_source_id = fields.Many2one(
        'insurance.source', 
        string='Insurance Source',
        tracking=True
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

    # ── Website Funnel Tracking (الحقول الناقصة للتتبع) ───────────────────────
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
        """Delegates funnel advancement to the underlying crm.lead."""
        self.ensure_one()
        return self.lead_id._funnel_advance(
            step, action_name=action_name, page_url=page_url, **extra_vals)

    # ── Anti-duplication website opportunity creation ─────────────────────────
    @api.model
    def _get_or_create_for_partner(self, partner):
        """
        Returns the active open insurance opportunity for this partner,
        or creates a new one. Prevents duplicate opportunities per customer.
        """
        existing = self.search([
            ('partner_id', '=', partner.id),
            ('type', '=', 'opportunity'),
            ('active', '=', True),
            ('stage_id.is_won', '=', False),
        ], limit=1)
        if existing:
            return existing

        # Get or create default stage
        stage = self.env['crm.stage'].sudo().search([], limit=1, order='sequence asc')

        # البحث عن سجل الـ Website بناءً على الكود أو الاسم لربطه تلقائياً كـ Default
        website_source = self.env['insurance.source'].sudo().search([('code', '=', 'website')], limit=1)

        opp = self.sudo().create({
            'type': 'opportunity',
            'name': f'Website Insurance — {partner.name}',
            'partner_id': partner.id,
            'contact_name': partner.name,
            'email_from': partner.email or '',
            'phone': partner.phone or '',
            'stage_id': stage.id if stage else False,
            'ins_source_id': website_source.id if website_source else False, # الربط الجديد
            'description': (
                f'تم الإنشاء تلقائياً: العميل "{partner.name}" زار '
                f'صفحة التأمين على الموقع.'
            ),
        })
        return opp

    # ── Auto-create Sales Application on Lead stage ───────────────────────────
    def write(self, vals):
        result = super().write(vals)
        # Check if the underlying crm.lead stage changed to a "lead/won" type
        if vals.get('stage_id'):
            stage = self.env['crm.stage'].browse(vals['stage_id'])
            if stage.sequence >= 2:  # Past initial stage
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
