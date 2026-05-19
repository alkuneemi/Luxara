# -*- coding: utf-8 -*-
  from odoo import fields, models


  class SaasPackage(models.Model):
      """حزم الاشتراك — تربط الجانب التجاري بالموديولات التقنية."""
      _name = 'saas.package'
      _description = 'Luxara SaaS Package'
      _order = 'sequence, name'

      name = fields.Char(string='اسم الحزمة', required=True, translate=True)
      sequence = fields.Integer(default=10)
      active = fields.Boolean(default=True)
      description = fields.Text(string='الوصف', translate=True)
      color = fields.Integer(string='اللون', default=0)

      # ── Pricing ──────────────────────────────────────────────────────────────
      monthly_price = fields.Float(string='السعر الشهري', digits=(10, 2))
      annual_price = fields.Float(string='السعر السنوي', digits=(10, 2))
      currency_id = fields.Many2one(
          'res.currency', string='العملة',
          default=lambda self: self.env.company.currency_id,
      )

      # ── Technical modules ────────────────────────────────────────────────────
      module_list = fields.Text(
          string='قائمة الموديولات',
          help='أسماء الموديولات الفنية المفصولة بفاصلة (مثل: account,insurance_broker_suite)',
      )
      odoo_branch = fields.Char(
          string='فرع Odoo',
          default='19.0',
          help='فرع GitHub الأساسي لهذه الحزمة.',
      )

      # ── Resources ────────────────────────────────────────────────────────────
      max_users = fields.Integer(string='أقصى عدد مستخدمين', default=5)
      max_storage_gb = fields.Float(string='مساحة التخزين (GB)', default=5.0)
      railway_service_size = fields.Selection([
          ('hobby', 'Hobby'),
          ('pro', 'Pro'),
      ], string='حجم الخدمة على Railway', default='hobby')

      # ── Clients ──────────────────────────────────────────────────────────────
      client_ids = fields.One2many(
          'saas.client', 'package_id', string='العملاء'
      )
      client_count = fields.Integer(
          string='عدد العملاء', compute='_compute_client_count', store=True
      )

      def _compute_client_count(self):
          for rec in self:
              rec.client_count = len(rec.client_ids)
  