# -*- coding: utf-8 -*-
  from odoo import api, fields, models, _
  from odoo.exceptions import UserError, ValidationError
  import requests
  import json
  import re
  import logging

  _logger = logging.getLogger(__name__)


  class SaasClient(models.Model):
      """السجل الديناميكي لكل عميل — يعكس الحالة الحية لحاويته على Railway."""
      _name = 'saas.client'
      _description = 'Luxara SaaS Client'
      _inherit = ['mail.thread', 'mail.activity.mixin']
      _rec_name = 'display_name_computed'
      _order = 'create_date desc'

      # ── Identity ─────────────────────────────────────────────────────────────
      partner_id = fields.Many2one(
          'res.partner', string='العميل', required=True, tracking=True
      )
      display_name_computed = fields.Char(
          compute='_compute_display_name_computed', store=True
      )
      email = fields.Char(
          string='البريد الإلكتروني',
          related='partner_id.email', store=True
      )

      # ── Package ───────────────────────────────────────────────────────────────
      package_id = fields.Many2one(
          'saas.package', string='الحزمة', required=True, tracking=True
      )
      server_id = fields.Many2one(
          'saas.server', string='إعداد السيرفر',
          required=True, tracking=True,
      )

      # ── Domain ───────────────────────────────────────────────────────────────
      subdomain = fields.Char(
          string='النطاق الفرعي',
          required=True,
          tracking=True,
          help='مثال: alameen  →  يصبح alameen.luxara.app',
      )
      full_domain = fields.Char(
          string='الرابط الكامل',
          compute='_compute_full_domain',
          store=True,
      )

      # ── Git Branches ──────────────────────────────────────────────────────────
      prod_branch = fields.Char(
          string='فرع الإنتاج',
          compute='_compute_branches',
          store=True,
      )
      stage_branch = fields.Char(
          string='فرع الاختبار',
          compute='_compute_branches',
          store=True,
      )

      # ── Railway IDs ───────────────────────────────────────────────────────────
      railway_service_id = fields.Char(
          string='معرف الخدمة (Railway Service ID)',
          tracking=True,
          help='المعرف الذي ترجعه Railway بعد إنشاء الخدمة.',
      )
      railway_db_id = fields.Char(
          string='معرف قاعدة البيانات (Railway DB ID)',
          tracking=True,
      )
      railway_domain = fields.Char(
          string='نطاق Railway الكامل',
          tracking=True,
      )

      # ── State ─────────────────────────────────────────────────────────────────
      state = fields.Selection([
          ('draft',      'مسودة'),
          ('deploying',  'جاري البناء'),
          ('active',     'نشط'),
          ('suspended',  'موقوف مؤقتاً'),
          ('cancelled',  'ملغي'),
      ], default='draft', string='الحالة', tracking=True)

      # ── Staging ───────────────────────────────────────────────────────────────
      is_staging = fields.Boolean(
          string='بيئة اختبار؟', default=False, tracking=True
      )
      parent_client_id = fields.Many2one(
          'saas.client', string='العميل الأصلي',
          help='مرجع عميل الإنتاج لهذه البيئة الاختبارية.',
      )
      staging_client_ids = fields.One2many(
          'saas.client', 'parent_client_id', string='بيئات الاختبار'
      )

      # ── Dates ─────────────────────────────────────────────────────────────────
      subscription_start = fields.Date(string='بداية الاشتراك')
      subscription_end = fields.Date(string='نهاية الاشتراك')
      last_deployed = fields.Datetime(string='آخر نشر', tracking=True)

      # ── Notes ─────────────────────────────────────────────────────────────────
      notes = fields.Html(string='ملاحظات')

      # ── Computed fields ───────────────────────────────────────────────────────
      @api.depends('partner_id', 'subdomain')
      def _compute_display_name_computed(self):
          for rec in self:
              partner = rec.partner_id.name or ''
              sub = rec.subdomain or ''
              rec.display_name_computed = f"{partner} ({sub})" if sub else partner

      @api.depends('subdomain', 'server_id.railway_base_domain')
      def _compute_full_domain(self):
          for rec in self:
              domain = rec.server_id.railway_base_domain or 'luxara.app'
              rec.full_domain = f"https://{rec.subdomain}.{domain}" if rec.subdomain else ''

      @api.depends('subdomain', 'is_staging')
      def _compute_branches(self):
          for rec in self:
              sub = (rec.subdomain or '').replace('.', '-').lower()
              rec.prod_branch = f"prod-{sub}" if sub else ''
              rec.stage_branch = f"stage-{sub}" if sub else ''

      # ── Validation ────────────────────────────────────────────────────────────
      @api.constrains('subdomain')
      def _check_subdomain(self):
          pattern = re.compile(r'^[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?$')
          for rec in self:
              if rec.subdomain and not pattern.match(rec.subdomain):
                  raise ValidationError(
                      _('النطاق الفرعي يجب أن يحتوي على أحرف صغيرة وأرقام وشرطات فقط.')
                  )

      # ── Actions ───────────────────────────────────────────────────────────────
      def _get_n8n_headers(self):
          return {
              'Content-Type': 'application/json',
              'X-Secret-Key': self.server_id.n8n_secret_key or '',
          }

      def _send_n8n_webhook(self, payload):
          """إرسال حزمة JSON إلى n8n Webhook."""
          self.ensure_one()
          url = self.server_id.n8n_webhook_url
          if not url:
              raise UserError(_('رابط n8n Webhook غير محدد في إعدادات السيرفر.'))
          try:
              resp = requests.post(
                  url,
                  json=payload,
                  headers=self._get_n8n_headers(),
                  timeout=30,
              )
              resp.raise_for_status()
              return resp.json() if resp.content else {}
          except requests.exceptions.RequestException as e:
              _logger.error("n8n webhook error for client %s: %s", self.id, e)
              raise UserError(
                  _('فشل الاتصال بـ n8n: %s') % str(e)
              )

      def action_provision(self):
          """تفعيل الحاوية — إرسال إشارة الإنشاء إلى n8n."""
          self.ensure_one()
          if self.state not in ('draft',):
              raise UserError(_('يمكن تفعيل الحاوية فقط من حالة المسودة.'))
          payload = {
              'action': 'provision',
              'client_id': self.id,
              'partner_name': self.partner_id.name,
              'email': self.email,
              'subdomain': self.subdomain,
              'prod_branch': self.prod_branch,
              'package': self.package_id.name,
              'modules': self.package_id.module_list or '',
              'github_repo': self.server_id.github_repo_url,
              'github_branch': self.prod_branch,
              'base_branch': self.server_id.github_base_branch,
              'railway_project_id': self.server_id.railway_project_id or '',
              'callback_url': self.server_id.callback_base_url + f"/{self.id}",
          }
          self._send_n8n_webhook(payload)
          self.write({'state': 'deploying', 'last_deployed': fields.Datetime.now()})
          self.message_post(body=_('تم إرسال أمر إنشاء الحاوية إلى n8n. جاري البناء...'))

      def action_suspend(self):
          """إيقاف مؤقت — إيقاف الحاوية على Railway عند التخلف عن السداد."""
          self.ensure_one()
          payload = {
              'action': 'suspend',
              'client_id': self.id,
              'railway_service_id': self.railway_service_id,
              'subdomain': self.subdomain,
          }
          self._send_n8n_webhook(payload)
          self.write({'state': 'suspended'})
          self.message_post(body=_('تم إرسال أمر الإيقاف المؤقت إلى Railway عبر n8n.'))

      def action_resume(self):
          """استئناف — إعادة تشغيل الحاوية بعد السداد."""
          self.ensure_one()
          if self.state != 'suspended':
              raise UserError(_('يمكن استئناف الخدمة فقط من حالة الإيقاف المؤقت.'))
          payload = {
              'action': 'resume',
              'client_id': self.id,
              'railway_service_id': self.railway_service_id,
              'subdomain': self.subdomain,
          }
          self._send_n8n_webhook(payload)
          self.write({'state': 'active'})
          self.message_post(body=_('تم إرسال أمر استئناف الخدمة إلى Railway عبر n8n.'))

      def action_upgrade(self):
          """إعادة بناء الحاوية (Redeploy) لتطبيق التحديثات الجديدة."""
          self.ensure_one()
          if self.state != 'active':
              raise UserError(_('يمكن تحديث الحاوية فقط في الحالة النشطة.'))
          payload = {
              'action': 'redeploy',
              'client_id': self.id,
              'railway_service_id': self.railway_service_id,
              'github_branch': self.prod_branch,
          }
          self._send_n8n_webhook(payload)
          self.write({'state': 'deploying', 'last_deployed': fields.Datetime.now()})
          self.message_post(body=_('تم إرسال أمر إعادة البناء إلى Railway عبر n8n.'))

      def action_create_staging(self):
          """إنشاء بيئة اختبار معزولة لهذا العميل."""
          self.ensure_one()
          if self.is_staging:
              raise UserError(_('لا يمكن إنشاء بيئة اختبار من بيئة اختبار.'))
          if self.state != 'active':
              raise UserError(_('يجب أن يكون العميل في الحالة النشطة لإنشاء بيئة اختبار.'))

          # إنشاء سجل العميل الاختباري
          staging = self.copy({
              'subdomain': f"{self.subdomain}-staging",
              'is_staging': True,
              'parent_client_id': self.id,
              'state': 'draft',
              'railway_service_id': False,
              'railway_db_id': False,
          })
          payload = {
              'action': 'provision_staging',
              'client_id': staging.id,
              'parent_client_id': self.id,
              'railway_service_id': self.railway_service_id,
              'railway_db_id': self.railway_db_id,
              'subdomain': staging.subdomain,
              'stage_branch': staging.stage_branch,
              'base_branch': self.prod_branch,
              'callback_url': self.server_id.callback_base_url + f"/{staging.id}",
          }
          self._send_n8n_webhook(payload)
          staging.write({'state': 'deploying'})
          self.message_post(body=_(f'تم إنشاء بيئة الاختبار: {staging.subdomain}'))
          return {
              'type': 'ir.actions.act_window',
              'res_model': 'saas.client',
              'res_id': staging.id,
              'view_mode': 'form',
          }

      def action_merge_staging(self):
          """دمج وتطبيق بيئة الاختبار على الإنتاج."""
          self.ensure_one()
          if not self.is_staging:
              raise UserError(_('هذه الإجراء للبيئات الاختبارية فقط.'))
          payload = {
              'action': 'merge_staging',
              'staging_client_id': self.id,
              'prod_client_id': self.parent_client_id.id,
              'stage_branch': self.stage_branch,
              'prod_branch': self.prod_branch,
              'railway_service_id': self.parent_client_id.railway_service_id,
          }
          self._send_n8n_webhook(payload)
          self.message_post(body=_('تم إرسال أمر الدمج والتطبيق على بيئة الإنتاج.'))
  