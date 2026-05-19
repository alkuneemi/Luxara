# -*- coding: utf-8 -*-
  from odoo import http, _
  from odoo.http import request
  import json
  import logging

  _logger = logging.getLogger(__name__)


  class SaasCallbackController(http.Controller):
      """استقبال إشارات الاكتمال من n8n بعد إنشاء حاويات العملاء."""

      @http.route(
          '/saas/callback/<int:client_id>',
          type='json',
          auth='public',
          methods=['POST'],
          csrf=False,
      )
      def saas_callback(self, client_id, **kwargs):
          """
          يستقبل إشارة n8n بعد اكتمال بناء الحاوية.
          الحمولة المتوقعة:
            {
              "success": true,
              "railway_service_id": "...",
              "railway_db_id": "...",
              "domain": "alameen.sahabcloud.app",
              "action": "provision"
            }
          """
          try:
              data = json.loads(request.httprequest.data)
          except Exception:
              data = request.jsonrequest or {}

          _logger.info("SaaS Callback received for client %s: %s", client_id, data)

          client = request.env['saas.client'].sudo().browse(client_id)
          if not client.exists():
              return {'status': 'error', 'message': 'Client not found'}

          if not data.get('success'):
              client.write({'state': 'draft'})
              client.message_post(
                  body=_('فشل بناء الحاوية: %s') % data.get('error', 'خطأ غير معروف')
              )
              return {'status': 'error', 'message': 'Build failed'}

          # تحديث بيانات ريلوي وتفعيل العميل
          vals = {'state': 'active'}
          if data.get('railway_service_id'):
              vals['railway_service_id'] = data['railway_service_id']
          if data.get('railway_db_id'):
              vals['railway_db_id'] = data['railway_db_id']
          if data.get('domain'):
              vals['railway_domain'] = data['domain']

          client.write(vals)
          client.message_post(
              body=_('تم بناء الحاوية بنجاح! الرابط: %s') % client.full_domain
          )

          # إرسال بريد الترحيب للعميل
          template = request.env.ref(
              'sahab_cloud_controller.mail_template_welcome',
              raise_if_not_found=False,
          )
          if template and client.partner_id.email:
              template.sudo().send_mail(client.id, force_send=True)

          return {'status': 'ok', 'client_id': client_id}

      @http.route(
          '/saas/portal',
          type='http',
          auth='user',
          website=True,
      )
      def saas_portal(self, **kwargs):
          """بوابة الويب للخدمة الذاتية — لوحة تحكم العميل."""
          partner = request.env.user.partner_id
          clients = request.env['saas.client'].sudo().search([
              ('partner_id', '=', partner.id),
              ('is_staging', '=', False),
          ])
          return request.render(
              'sahab_cloud_controller.portal_my_instances',
              {'clients': clients},
          )
  