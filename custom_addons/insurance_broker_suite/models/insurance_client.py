from odoo import models, fields, api, _
from datetime import date


class InsuranceClientAgentMessage(models.Model):
    _name = 'insurance.client.agent.message'
    _description = 'AI Agent Generated Messages for Client'
    _order = 'id desc'

    client_id = fields.Many2one('insurance.client', string='Client', required=True, ondelete='cascade')
    message_type = fields.Selection([
        ('welcome', 'ترحيب وتحفيز'),
        ('reminder', 'تذكير بطلب غير مكتمل'),
        ('tip', 'نصائح وإرشادات'),
        ('cross_sell', 'تسويق وإعلانات'),
    ], string='Message Type', required=True)
    target_page = fields.Char(string='Target Page / Context')
    content = fields.Text(string='Message Content', required=True)
    is_read = fields.Boolean(string='Read by Client', default=False)


class InsuranceClient(models.Model):
    _name = 'insurance.client'
    _description = 'Insurance Client'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'name'
    _order = 'name'

    name = fields.Char(string='Client Name', required=True, tracking=True)
    category = fields.Selection([
        ('personal', 'Personal'),
        ('corporate', 'Corporate'),
    ], string='Category', default='corporate', required=True, tracking=True)
    contact_person = fields.Char(string='Contact Person')
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    address = fields.Text(string='Address')

    # ── Industry / Sector ─────────────────────────────────────────────────────
    industry_ids = fields.Many2many(
        'insurance.industry.tag',
        'insurance_client_industry_rel',
        'client_id',
        'industry_id',
        string='Industry / Sectors',
    )
    industry = fields.Char(string='Industry (Legacy)', help='Deprecated: use Industry / Sectors field above.')

    crm_stage = fields.Selection([
        ('new_lead', 'New Lead'),
        ('contacted', 'Contacted'),
        ('requirement_collection', 'Requirement Collection'),
        ('quotation_requested', 'Quotation Requested'),
        ('negotiation', 'Negotiation'),
        ('won', 'Won'),
        ('lost', 'Lost'),
    ], string='CRM Stage', default='new_lead', tracking=True)
    
    notes = fields.Text(string='Notes')
    active = fields.Boolean(default=True)

    # ── Accounting / Partner Link ─────────────────────────────────────────────
    partner_id = fields.Many2one(
        'res.partner',
        string='Related Customer',
        readonly=True,
        ondelete='restrict',
        help='The linked customer record in the Contacts/Accounting app.'
    )

    # ── Website Journey Tracking ──────────────────────────────────────────────
    current_funnel_step = fields.Selection(
        selection=[
            ('1_categories', 'زار الأقسام الرئيسية'),
            ('2_types',      'زار الأنواع'),
            ('3_subtypes',   'زار الأنواع الفرعية'),
            ('4_form',       'مرحلة ملء الاستمارة'),
            ('5_payment',    'مرحلة الدفع'),
            ('6_completed',  'أكمل العملية بنجاح'),
        ],
        string='Funnel Step',
        tracking=True,
        index=True,
    )
    last_category_id = fields.Many2one('insurance.category', string='Last Category', ondelete='set null')
    last_type_id = fields.Many2one('insurance.type', string='Last Type', ondelete='set null')
    last_subtype_id = fields.Many2one('insurance.subtype', string='Last Subtype', ondelete='set null')

    journey_log_ids = fields.One2many('insurance.client.journey.log', 'client_id', string='Journey Log')
    journey_log_count = fields.Integer(compute='_compute_journey_log_count', string='Log Entries')

    # ── Relational Links (تجميع كل ما يتعلق بالعميل لقراءة الـ AI الشاملة) ───────
    policy_ids = fields.One2many('insurance.policy', 'client_id', string='Policies')
    rfq_ids = fields.One2many('insurance.rfq', 'client_id', string='RFQs')
    claim_ids = fields.One2many('insurance.claim', 'client_id', string='Claims')
    
    # ربط الفرص البيعية (crm.lead المربوطة بالشريك الحالي)
    opportunity_ids = fields.One2many('crm.lead', 'partner_id', string='CRM Opportunities', compute='_compute_opportunity_ids')
    
    # ربط طلبات التأمين عبر بوابات الويب أو المبيعات
    application_ids = fields.One2many('insurance.application', 'partner_id', string='Insurance Applications', compute='_compute_application_ids')

    # ── الإحصائيات المحسوبة المتقدمة للداشبورد للعميل ───────────────────────────
    policy_count = fields.Integer(compute='_compute_policy_count', string='Policies')
    active_policy_count = fields.Integer(compute='_compute_dashboard_stats', string='Active Policies')
    expired_policy_count = fields.Integer(compute='_compute_dashboard_stats', string='Expired Policies')
    
    rfq_count = fields.Integer(compute='_compute_rfq_count', string='RFQs')
    pending_rfq_count = fields.Integer(compute='_compute_dashboard_stats', string='Pending RFQs')
    
    claim_count = fields.Integer(compute='_compute_claim_count', string='Claims')
    open_claim_count = fields.Integer(compute='_compute_dashboard_stats', string='Open Claims')
    
    opportunity_count = fields.Integer(compute='_compute_dashboard_stats', string='Opportunities Count')
    pending_app_count = fields.Integer(compute='_compute_dashboard_stats', string='Pending Applications Count')

    total_premium = fields.Float(compute='_compute_total_premium', string='Total Active Premium', store=True)
    total_claimed_amount = fields.Float(compute='_compute_dashboard_stats', string='Total Claimed Amount')

    # ── AI Agent Integration ──────────────────────────────────────────────────
    agent_message_ids = fields.One2many('insurance.client.agent.message', 'client_id', string='AI Agent Messages')

    @api.depends('partner_id')
    def _compute_opportunity_ids(self):
        for rec in self:
            if rec.partner_id:
                rec.opportunity_ids = self.env['crm.lead'].search([('partner_id', '=', rec.partner_id.id)])
            else:
                rec.opportunity_ids = False

    @api.depends('partner_id')
    def _compute_application_ids(self):
        for rec in self:
            if rec.partner_id:
                rec.application_ids = self.env['insurance.application'].search([('partner_id', '=', rec.partner_id.id)])
            else:
                rec.application_ids = False

    @api.depends('journey_log_ids')
    def _compute_journey_log_count(self):
        for rec in self:
            rec.journey_log_count = len(rec.journey_log_ids)

    @api.depends('policy_ids', 'policy_ids.net_premium', 'policy_ids.status')
    def _compute_total_premium(self):
        for rec in self:
            rec.total_premium = sum(rec.policy_ids.filtered(
                lambda p: p.status == 'active'
            ).mapped('net_premium'))

    @api.depends('policy_ids')
    def _compute_policy_count(self):
        for rec in self:
            rec.policy_count = len(rec.policy_ids)

    @api.depends('rfq_ids')
    def _compute_rfq_count(self):
        for rec in self:
            rec.rfq_count = len(rec.rfq_ids)

    @api.depends('claim_ids')
    def _compute_claim_count(self):
        for rec in self:
            rec.claim_count = len(rec.claim_ids)

    # احتساب إحصائيات لوحة التحكم الشاملة للتسهيل على الـ AI لقراءتها دفعة واحدة
    @api.depends('policy_ids', 'rfq_ids', 'claim_ids', 'opportunity_ids', 'application_ids')
    def _compute_dashboard_stats(self):
        for rec in self:
            rec.active_policy_count = len(rec.policy_ids.filtered(lambda p: p.status == 'active'))
            rec.expired_policy_count = len(rec.policy_ids.filtered(lambda p: p.status in ['expired', 'cancelled']))
            rec.pending_rfq_count = len(rec.rfq_ids.filtered(lambda r: r.status in ['draft', 'sent']))
            rec.open_claim_count = len(rec.claim_ids.filtered(lambda c: c.status not in ['settled', 'rejected']))
            rec.opportunity_count = len(rec.opportunity_ids)
            rec.pending_app_count = len(rec.application_ids.filtered(lambda a: a.status not in ['approved', 'policy_issued', 'rejected']))
            rec.total_claimed_amount = sum(rec.claim_ids.mapped('claim_amount'))

    # ── Create & Write Overrides (Partner Sync) ──────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            partner_vals = {
                'name': vals.get('name'),
                'email': vals.get('email'),
                'phone': vals.get('phone'),
                'company_type': 'company' if vals.get('category') == 'corporate' else 'person',
                'customer_rank': 1,
            }
            partner = self.env['res.partner'].sudo().create(partner_vals)
            vals['partner_id'] = partner.id

        return super().create(vals_list)

    def write(self, vals):
        res = super().write(vals)
        partner_vals = {}
        if 'name' in vals: partner_vals['name'] = vals['name']
        if 'email' in vals: partner_vals['email'] = vals['email']
        if 'phone' in vals: partner_vals['phone'] = vals['phone']
        if 'category' in vals: 
            partner_vals['company_type'] = 'company' if vals['category'] == 'corporate' else 'person'

        if partner_vals:
            for rec in self:
                if rec.partner_id:
                    rec.partner_id.sudo().write(partner_vals)
        return res

    # ── Actions ───────────────────────────────────────────────────────────────
    def action_view_policies(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Policies',
            'res_model': 'insurance.policy',
            'view_mode': 'list,form',
            'domain': [('client_id', '=', self.id)],
            'context': {'default_client_id': self.id},
        }

    def action_view_rfqs(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'RFQs',
            'res_model': 'insurance.rfq',
            'view_mode': 'list,form',
            'domain': [('client_id', '=', self.id)],
            'context': {'default_client_id': self.id},
        }

    def action_generate_agent_messages(self):
        """تحليل حالة العميل وتوليد رسائل مخصصة بناءً على مرحلته الحالية"""
        for client in self:
            client.agent_message_ids.filtered(lambda m: not m.is_read).unlink()
            messages_to_create = []
            step = client.current_funnel_step
            
            if step in ['4_form', '5_payment']:
                messages_to_create.extend([
                    {'type': 'reminder', 'target': 'form', 'text': f'مرحباً {client.name or "بك"}! لقد قطعت شوطاً رائعاً، طلبك السابق في انتظارك لإكماله.'},
                    {'type': 'reminder', 'target': 'form', 'text': 'لا تدع التغطية التأمينية تفوتك، أكمل بيانات الاستمارة الآن واضمن حمايتك.'},
                    {'type': 'tip', 'target': 'payment', 'text': 'هل تعلم أن الدفع الإلكتروني لدينا مشفر ومحمي بأعلى معايير الأمان العالمية؟'},
                    {'type': 'tip', 'target': 'form', 'text': 'بقي خطوة واحدة فقط للحصول على عروض الأسعار من أفضل شركات التأمين.'},
                    {'type': 'cross_sell', 'target': 'form', 'text': 'أثناء إكمالك للطلب، يمكنك إضافة تغطية توسيعية للحوادث الشخصية بخصم خاص اليوم فقط.'},
                    {'type': 'tip', 'target': 'form', 'text': 'إذا واجهت أي صعوبة في إرفاق المستندات، يمكنك تخطيها الآن وإرسالها لاحقاً.'},
                    {'type': 'reminder', 'target': 'form', 'text': 'الوثيقة بانتظارك! فريقنا جاهز لاعتمادها فور إكمال الخطوة الأخيرة.'},
                    {'type': 'welcome', 'target': 'form', 'text': 'عوداً حميداً! يسعدنا رؤيتك تكمل رحلتك معنا لتأمين مستقبلك.'},
                    {'type': 'tip', 'target': 'form', 'text': 'تأكد من إدخال رقم الهوية بشكل صحيح لضمان ربط الوثيقة بالنظام وتفعيلها فوراً.'},
                    {'type': 'cross_sell', 'target': 'form', 'text': 'هل فكرت في تأمين ممتلكاتك الأخرى؟ لدينا باقات شاملة تناسب احتياجاتك بعد إكمال هذا الطلب.'},
                ])
            elif step in ['2_types', '3_subtypes']:
                messages_to_create.extend([
                    {'type': 'tip', 'target': 'types', 'text': 'عند اختيار نوع التأمين، احرص على مراجعة جدول المنافع لضمان تغطية احتياجاتك الأساسية.'},
                    {'type': 'tip', 'target': 'subtypes', 'text': 'التأمين الشامل يوفر لك راحة بال تامة مقارنة بتأمين ضد الغير. قارن بينهما الآن!'},
                    {'type': 'cross_sell', 'target': 'types', 'text': 'باقة "الدرع المتميز" هي الأكثر طلباً هذا الأسبوع للشركات، اكتشف مميزاتها.'},
                    {'type': 'welcome', 'target': 'types', 'text': 'نحن هنا لمساعدتك في اختيار الباقة الأنسب. لا تتردد في استخدام أداة المقارنة الذكية.'},
                    {'type': 'tip', 'target': 'types', 'text': 'هل تبحث عن تغطية دولية؟ تأكد من تفعيل خيار "الامتداد الجغرافي" في البوليصة.'},
                    {'type': 'tip', 'target': 'subtypes', 'text': 'أضفنا مؤخراً تغطية إضافية لبعض وثائق التأمين. تصفح الخيارات المتاحة.'},
                    {'type': 'reminder', 'target': 'types', 'text': 'إذا كنت محتاراً بين نوعين، يمكنك حفظهما في المفضلة والعودة لهما لاحقاً.'},
                    {'type': 'cross_sell', 'target': 'subtypes', 'text': 'احصل على استشارة مجانية مع أحد خبرائنا لاختيار التأمين الأنسب لنشاطك.'},
                    {'type': 'tip', 'target': 'types', 'text': 'معلومة تهمك: بعض الوثائق توفر تغطيات مميزة كإضافة اختيارية.'},
                    {'type': 'welcome', 'target': 'subtypes', 'text': 'استكشف عالم التأمين بثقة، جميع شركات التأمين لدينا معتمدة.'},
                ])
            else:
                messages_to_create.extend([
                    {'type': 'welcome', 'target': 'categories', 'text': 'أهلاً بك في منصتنا! نحن هنا لنجعل تجربة التأمين أسهل، أسرع، وأكثر شفافية.'},
                    {'type': 'cross_sell', 'target': 'categories', 'text': 'اكتشف باقة التأمين العائلية الجديدة، حماية متكاملة لك ولعائلتك بأسعار تنافسية.'},
                    {'type': 'tip', 'target': 'categories', 'text': 'تصفح الأقسام بمرونة، صممنا الموقع ليأخذك خطوة بخطوة نحو التغطية المثالية.'},
                    {'type': 'welcome', 'target': 'categories', 'text': 'سجل دخولك الآن لحفظ تقدمك والحصول على عروض أسعار حصرية ومخصصة لك.'},
                    {'type': 'tip', 'target': 'categories', 'text': 'هل تعلم أنه يمكنك استخراج وثيقتك إلكترونياً بالكامل في دقائق معدودة?'},
                    {'type': 'cross_sell', 'target': 'categories', 'text': 'لعملاء الشركات: لدينا حلول تأمينية مخصصة لحماية أسطول مركباتك وموظفيك.'},
                    {'type': 'tip', 'target': 'categories', 'text': 'تأكد من تجهيز وثائقك الرسمية لتسريع عملية إصدار الوثيقة لاحقاً.'},
                    {'type': 'welcome', 'target': 'categories', 'text': 'نحن نفخر بتقديم خيارات تأمينية تناسب كل ميزانية. ابدأ رحلتك الآن!'},
                    {'type': 'cross_sell', 'target': 'categories', 'text': 'حمل تطبيقنا الآن لتتبع مطالباتك وإدارة وثائقك التأمينية من هاتفك مباشرة.'},
                    {'type': 'tip', 'target': 'categories', 'text': 'تابع مدونتنا التأمينية لمعرفة المزيد عن كيفية اختيار التأمين المناسب.'},
                ])

            for msg in messages_to_create:
                self.env['insurance.client.agent.message'].create({
                    'client_id': client.id,
                    'message_type': msg['type'],
                    'target_page': msg['target'],
                    'content': msg['text'],
                })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'تم التحليل!',
                'message': 'قام الوكيل الذكي بتحليل حالة العميل وتوليد 10 رسائل استراتيجية بنجاح.',
                'type': 'success',
                'sticky': False,
            }
        }


class InsuranceClientJourneyLog(models.Model):
    _name = 'insurance.client.journey.log'
    _description = 'Insurance Client — Website Journey Log'
    _order = 'id desc'
    _log_access = True

    client_id = fields.Many2one(
        'insurance.client', string='Client',
        required=True, ondelete='cascade', index=True)
    action_name = fields.Char(string='Action', required=True)
    page_url = fields.Char(string='Page URL')
    create_date = fields.Datetime(string='Timestamp', readonly=True)
