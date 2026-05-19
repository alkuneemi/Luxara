# -*- coding: utf-8 -*-
  from odoo import api, fields, models, _
  from odoo.exceptions import UserError
  import requests
  import json
  import logging

  _logger = logging.getLogger(__name__)


  class SaasServer(models.Model):
      """إعدادات الخادم المركزي وإعدادات التكامل مع n8n وGitHub."""
      _name = 'saas.server'
      _description = 'Luxara SaaS Server Configuration'
      _rec_name = 'name'

      name = fields.Char(
          string='اسم الإعداد',
          required=True,
          default='إعداد Luxara الرئيسي',
      )
      active = fields.Boolean(default=True)

      # ── n8n Integration ─────────────────────────────────────────────────────
      n8n_webhook_url = fields.Char(
          string='رابط n8n Webhook',
          required=True,
          help='الرابط الرئيسي الذي يستقبل أوامر إنشاء وإدارة الحاويات.',
      )
      n8n_secret_key = fields.Char(
          string='مفتاح الأمان (API Secret)',
          required=True,
          help='مفتاح التشفير لضمان أمان الاتصال بين Odoo وn8n.',
      )

      # ── GitHub Integration ───────────────────────────────────────────────────
      github_repo_url = fields.Char(
          string='رابط مستودع Luxara الأم',
          required=True,
          default='https://github.com/alkuneemi/Luxara',
          help='المستودع الذي تُشتق منه فروع العملاء.',
      )
      github_token = fields.Char(
          string='GitHub Access Token',
          required=True,
          help='توكن الوصول لـ GitHub لإنشاء فروع العملاء.',
      )
      github_base_branch = fields.Char(
          string='الفرع الأساسي',
          default='19.0',
          required=True,
          help='الفرع الذي تُشتق منه فروع الإنتاج.',
      )

      # ── Railway Integration ──────────────────────────────────────────────────
      railway_api_token = fields.Char(
          string='Railway API Token',
          help='توكن الوصول لـ Railway لإدارة الخدمات والحاويات.',
      )
      railway_project_id = fields.Char(
          string='معرف مشروع Railway',
          help='معرف المشروع الرئيسي على Railway.',
      )
      railway_base_domain = fields.Char(
          string='النطاق الأساسي',
          default='luxara.app',
          help='النطاق الذي تُضاف إليه النطاقات الفرعية للعملاء.',
      )

      # ── Callback ─────────────────────────────────────────────────────────────
      callback_base_url = fields.Char(
          string='رابط الاستقبال (Callback URL)',
          compute='_compute_callback_url',
          store=False,
          help='الرابط الذي يرسل إليه n8n إشارة الاكتمال.',
      )

      @api.depends('name')
      def _compute_callback_url(self):
          base = self.env['ir.config_parameter'].sudo().get_param(
              'web.base.url', 'https://luxara.app'
          )
          for rec in self:
              rec.callback_base_url = f"{base}/saas/callback"

      def action_test_connection(self):
          """اختبار الاتصال بـ n8n."""
          self.ensure_one()
          try:
              resp = requests.post(
                  self.n8n_webhook_url,
                  json={'action': 'ping', 'source': 'odoo_test'},
                  headers={'X-Secret-Key': self.n8n_secret_key},
                  timeout=10,
              )
              if resp.status_code in (200, 201):
                  return {
                      'type': 'ir.actions.client',
                      'tag': 'display_notification',
                      'params': {
                          'title': _('نجاح'),
                          'message': _('الاتصال بـ n8n يعمل بشكل صحيح.'),
                          'type': 'success',
                      },
                  }
          except Exception as e:
              _logger.error("SaaS Server connection test failed: %s", e)
          raise UserError(_('فشل الاتصال بـ n8n. تحقق من الرابط ومفتاح الأمان.'))
  