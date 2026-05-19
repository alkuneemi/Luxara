# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
import json
import requests
import logging
from odoo.fields import Datetime, Date

_logger = logging.getLogger(__name__)

class OmanAgentController(http.Controller):

    @http.route('/oman_agent/analyze_visit', type='json', auth='public', website=True, csrf=False)
    def analyze_client_visit(self, page_url=b'', action_name=b''):
        """
        دالة برمجية تعمل عند تصفح العميل لصفحة /insurance والصفحات التابعة لها،
        تجمع الإعدادات المتغيرة لرسالة النظام وترسلها إلى n8n للتحليل الفوري الفائق.
        """
        # جلب سجل الإعدادات النشط للـ AI ورسالة النظام
        ai_config = request.env['sahab.ai.config'].sudo().get_config()

        # 1. تحديد هوية العميل الحالي (مسجل الدخول أو الزائر)
        user = request.env.user
        partner = user.partner_id if not user._is_public() else False
        
        client_domain = []
        if partner:
            client_domain = [('partner_id', '=', partner.id)]
        else:
            # محاولة التعرف على الزائر عبر الجلسة
            client_domain = [('id', '=', request.session.get('oman_agent_client_id', 0))]

        client = request.env['insurance.client'].sudo().search(client_domain, limit=1) if client_domain else False

        # تسجيل التحرك الحالي في سجلات رحلة العميل بالموقع
        if client and page_url:
            request.env['insurance.client.journey.log'].sudo().create({
                'client_id': client.id,
                'action_name': action_name or 'زيارة صفحة التأمين',
                'page_url': page_url,
            })

        # 2. بناء ملف البيانات الشامل للعميل مع حقن رسالة النظام المتغيرة من الإعدادات
        client_profile = {
            # تزويد n8n بالتعليمات ورسالة النظام المحددة من الخلفية
            'system_message': ai_config.system_message or '',
            'agent_name': ai_config.agent_name or 'Oman Agent',
            'company_name': ai_config.company_name or 'Ameen Hub',
            'welcome_message': ai_config.welcome_message or '',
            
            # بيانات تتبع العميل والـ CRM الحالي
            'is_logged_in': not user._is_public(),
            'client_id': client.id if client else False,
            'name': client.name if client else 'زائر جديد',
            'email': client.email if client else '',
            'phone': client.phone if client else '',
            'category': client.category if client else 'public',
            'crm_stage': client.crm_stage if client else 'new_lead',
            'current_funnel_step': client.current_funnel_step if client else '1_categories',
            'current_page_url': page_url,
            
            # المؤشرات الرقمية للعمليات المكتملة أو السابقة
            'policy_count': client.policy_count if client else 0,
            'rfq_count': client.rfq_count if client else 0,
            'claim_count': client.claim_count if client else 0,
            'total_premium': client.total_premium if client else 0.0,
            
            # السجلات والوثائق السابقة والطلبات المعلقة والمنتهية
            'pending_rfqs': [],
            'expiring_policies': [],
            'active_claims': [],
            'recent_journey_logs': []
        }

        if client:
            # جلب الطلبات المعلقة (RFQs)
            pending_rfqs = request.env['insurance.rfq'].sudo().search([
                ('client_id', '=', client.id),
                ('status', 'in', ['draft', 'sent', 'responses_received'])
            ], limit=3)
            client_profile['pending_rfqs'] = [{
                'id': r.id, 'ref': r.reference_no, 'type': r.insurance_type, 'status': r.status
            } for r in pending_rfqs]

            # جلب الوثائق التي شارف تاريخ صلاحيتها على الانتهاء
            today = Date.today()
            thirty_days_later = Date.add(today, days=30)
            expiring_policies = request.env['insurance.policy'].sudo().search([
                ('client_id', '=', client.id),
                ('status', '=', 'active'),
                ('date_to', '>=', today),
                ('date_to', '<=', thirty_days_later)
            ], limit=3)
            client_profile['expiring_policies'] = [{
                'id': p.id, 'policy_no': p.name, 'expiry_date': str(p.date_to), 'premium': p.net_premium
            } for p in expiring_policies]

            # جلب مطالبات جارية ولم تسوى بعد
            active_claims = request.env['insurance.claim'].sudo().search([
                ('client_id', '=', client.id),
                ('status', 'not in', ['settled', 'rejected'])
            ], limit=3)
            client_profile['active_claims'] = [{
                'id': c.id, 'claim_no': c.name, 'status': c.status
            } for c in active_claims]

            # آخر 5 تحركات تصفح للعميل لاستنباط اهتماماته الفورية
            recent_logs = request.env['insurance.client.journey.log'].sudo().search([
                ('client_id', '=', client.id)
            ], limit=5, order='id desc')
            client_profile['recent_journey_logs'] = [{
                'action': l.action_name, 'url': l.page_url, 'time': str(l.create_date)
            } for l in recent_logs]

        # الرد البديل الفوري والسريع لحماية انسيابية تصفح الصفحة (Fallback)
        fallback_reply = {
            'welcome': ai_config.welcome_message or "مرحباً بك! تصفح باقاتنا التأمينية وسأقدم لك النصيحة المخلصة.",
            'recommendation': "نحن هنا لمساعدتك في اختيار التغطية الأنسب وتوضيح جميع التفاصيل.",
            'alert': "",
            'promo_ad': {
                'title': "عرض تأمين السيارات الشامل",
                'text': "احصل على خصومات حصرية وتغطية كاملة للمركبات الآن أونلاين.",
                'link': "/insurance"
            }
        }

        # 3. إعداد الروابط الثابتة لاختبار n8n واللايف المباشر
        test_url = "https://n8n-production-f5c9.up.railway.app/webhook-test/oman_agent_webhook"
        live_url = "https://n8n-production-f5c9.up.railway.app/webhook/oman_agent_webhook"

        response = None
        try:
            # المحاولة الأولى: إرسال الطلب إلى رابط الـ Test
            # المهلة الزمنية قصيرة جداً (1 ثانية) للرد الفوري
            response = requests.post(
                test_url,
                json=client_profile,
                headers={'Content-Type': 'application/json'},
                timeout=1.0
            )
            
            # إذا كان الـ Test غير مفعّل، n8n يرجع 404 فوراً، فنثير خطأ للانتقال للمحاولة الثانية
            if response.status_code != 200:
                raise ValueError("Test Webhook is not active.")
                
        except Exception as e:
            # المحاولة الثانية: التحويل الفوري إلى رابط الـ Live
            _logger.info("Switching to n8n Live Webhook... Test url failed/inactive.")
            try:
                response = requests.post(
                    live_url,
                    json=client_profile,
                    headers={'Content-Type': 'application/json'},
                    timeout=1.8
                )
            except Exception as live_e:
                _logger.error("Both n8n Test and Live Webhooks failed. Using fallback.")
                return fallback_reply

        # معالجة النتيجة المرجعة من n8n (سواء كانت من الـ Test أو Live)
        if response and response.status_code == 200:
            try:
                res_data = response.json()
                return {
                    'welcome': res_data.get('welcome', fallback_reply['welcome']),
                    'recommendation': res_data.get('recommendation', fallback_reply['recommendation']),
                    'alert': res_data.get('alert', fallback_reply['alert']),
                    'promo_ad': res_data.get('promo_ad', fallback_reply['promo_ad'])
                }
            except Exception:
                return fallback_reply
        else:
            return fallback_reply
