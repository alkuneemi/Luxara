# -*- coding: utf-8 -*-
import json
import uuid
import requests
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# رسالة النظام الاحتياطية (Fallback)

class SahabAIController(http.Controller):

    # 1️⃣ دالة جلب السياق الأولي والترحيب (الأصلية)
    @http.route('/sahab/ai/context', type='json', auth='public', methods=['POST'], csrf=False)
    def get_context(self, **kwargs):
        cats = request.env['insurance.category'].sudo().search([
            ('website_published', '=', True), ('active', '=', True),
        ], order='sequence, name')
        cfg = request.env['sahab.ai.config'].sudo().get_config()
        return {
            'categories': [{'id': c.id, 'name': c.name, 'icon': c.icon or 'fa-shield'} for c in cats],
            'agent_name': cfg.agent_name or 'SAHAB AI',
            'welcome_message': cfg.welcome_message or 'أهلاً وسهلاً! أنا صحاب، مساعدك التأميني، كيف أقدر أساعدك اليوم؟',
        }

    # 2️⃣ الدالة المضافة حديثاً: جلب محفظة وبيانات العميل الشاملة فور النقر على الأيقونة
    @http.route('/sahab/ai/fetch_client_dashboard_context', type='json', auth='public', methods=['POST'], csrf=False)
    def fetch_client_dashboard_context(self, **kwargs):
        """
        تُستدعى فور النقر على الأيقونة: تجمع كل ما يتعلق بالعميل من مديول التحليلات الموحد 
        لتزويد n8n بملف رقمي كامل عن حالة طلباته وتواريخ بوالصه المنتهية أو القريبة من الانتهاء.
        """
        user = request.env.user
        # إذا كان زائر غير مسجل، نكتفي بإرسال بيانات فارغة
        if user._is_public() or not user.partner_id:
            return {'logged_in': False, 'client_portfolio': {}}

        # البحث عن سجل العميل في مديول التغطية التأمينية الموحد المربوط بالشريك الحالي
        client_rec = request.env['insurance.client'].sudo().search([('partner_id', '=', user.partner_id.id)], limit=1)
        
        if not client_rec:
            return {
                'logged_in': True,
                'customer_name': user.partner_id.name,
                'email': user.partner_id.email or '',
                'phone': user.partner_id.phone or '',
                'client_portfolio': {'has_record': False}
            }

        # بناء ملف البيانات التحليلي الشامل وإرساله في الحقل المخفي للـ Webhook
        portfolio = {
            'has_record': True,
            'client_id': client_rec.id,
            'customer_name': client_rec.name,
            'category': client_rec.category,
            'crm_stage': client_rec.crm_stage,
            'current_funnel_step': client_rec.current_funnel_step or 'None',
            'stats': {
                'total_active_premium': client_rec.total_premium,
                'active_policies_count': client_rec.active_policy_count,
                'expired_policies_count': client_rec.expired_policy_count,
                'open_claims_count': client_rec.open_claim_count,
                'pending_rfqs_count': client_rec.pending_rfq_count,
            },
            # كشف تاريخي بالبوالص وتواريخ انتهائها لتنبيه العميل آلياً بانتهاء بوليصته
            'policies': [{
                'policy_number': p.policy_number,
                'insurer': p.insurer,
                'subtype': p.subtype_id.name if p.subtype_id else 'General',
                'expiry_date': str(p.expiry_date),
                'status': p.status,
                'premium': p.net_premium
            } for p in client_rec.policy_ids],
            # كشف بطلبات البوابة والـ CRM قيد المعالجة لمعرفة حالة الطلب الحالي
            'pending_applications': [{
                'reference': a.reference,
                'subtype': a.subtype_id.name if a.subtype_id else 'General',
                'status': a.status,
                'channel': a.channel,
                'date': str(a.create_date.date())
            } for a in client_rec.application_ids if a.status not in ['approved', 'policy_issued', 'rejected']],
            # تتبع الحوادث والمطالبات الحالية
            'active_claims': [{
                'claim_number': c.claim_number,
                'incident_date': str(c.incident_date),
                'claim_amount': c.claim_amount,
                'status': c.status
            } for c in client_rec.claim_ids]
        }
        return {'logged_in': True, 'client_portfolio': portfolio}

    # 3️⃣ دالة الـ Chat الرئيسية (المحدثة لاستقبال المستندات والسياق الموحد)
    @http.route('/sahab/ai/chat', type='json', auth='public', methods=['POST'], csrf=False)
    def chat(self, message='', session_id=None, context=None, attachment=None, **kwargs):
        """
        واجهة الدردشة الحية: تستقبل رسالة العميل، حزمة السياق التحليلي المحدث، 
        والملف أو الصورة المشفرة Base64 لإرسالها مباشرة لـ n8n.
        """
        if not session_id:
            session_id = str(uuid.uuid4())

        cfg = request.env['sahab.ai.config'].sudo().get_config()
        agent_name = cfg.agent_name or 'SAHAB AI'

        # توجيه الطلب حسب الإعدادات (إلى n8n أو OpenAI المباشر)
        try:
            if cfg.mode == 'n8n_webhook' and cfg.n8n_webhook_url:
                return self._n8n_reply(message, session_id, context or {}, attachment, cfg)
            elif cfg.mode == 'direct_api' and cfg.openai_api_key:
                return self._openai_reply(message, session_id, context or {}, cfg, agent_name)
        except Exception as e:
            _logger.error(f"AI backend error: {str(e)}")
            
        return {
            'reply': 'عذراً، أواجه صعوبة في الاتصال بالخادم الذكي حالياً. يرجى المحاولة بعد قليل.',
            'options': [],
            'session_id': session_id
        }

    # 4️⃣ دالة الإرسال والاستقبال من n8n (المحدثة لتضمين المرفقات)
    def _n8n_reply(self, message, session_id, context, attachment, cfg):
        user = request.env.user
        partner = user.partner_id if not user._is_public() else False

        # بناء حزمة البيانات (Payload) الشاملة للمرفقات وعقل الأيجنت المخفي
        payload = {
            'message': message,
            'session_id': session_id,
            'system_message': cfg.system_message or '',
            'client_info': {
                'is_logged_in': not user._is_public(),
                'name': partner.name if partner else 'زائر',
                'email': partner.email if partner else '',
            },
            'context': context,       # سياق محفظة وبوالص العميل من أودو
            'attachment': attachment   # الملف المشفر (base64, filename, mime_type)
        }

        resp = requests.post(
            cfg.n8n_webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )

        if resp.status_code == 200:
            data = resp.json()
            reply_text = data.get('reply') or data.get('message') or data.get('recommendation') or "تم استلام رسالتك."
            
            response_data = {
                'reply': reply_text,
                'options': data.get('options', []) or data.get('quick_replies', []),
                'session_id': session_id
            }

            if data.get('action') == 'create_lead':
                record_info = self._create_odoo_records(data.get('collected_data', {}), session_id)
                response_data['portal_url'] = record_info.get('portal_url')
                response_data['application_created'] = True

            return response_data
        else:
            return {'reply': 'عذراً، واجهت مشكلة في التفكير مع الـ Webhook. هل يمكنك إعادة صياغة سؤالك؟', 'session_id': session_id}

    # 5️⃣ دالة الـ OpenAI الاحتياطية (الأصلية)
# 5️⃣ دالة الـ OpenAI الاحتياطية (المحدثة لتقرأ من الإعدادات مباشرة)
    def _openai_reply(self, message, session_id, context, cfg, agent_name):
        
        # 1. سحب رسالة النظام من نموذج الإعدادات مباشرة
        base_system_prompt = cfg.system_message or 'أنت مساعد ذكي.'

        # 2. استبدال المتغيرات الديناميكية (الاسم والشركة) إذا تمت كتابتها في واجهة الإعدادات
        system_content = base_system_prompt.replace('{agent_name}', agent_name).replace('{company_name}', cfg.company_name or 'Ameen Hub')

        resp = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {cfg.openai_api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': cfg.ai_model or 'gpt-4o-mini',
                'messages': [
                    {'role': 'system', 'content': system_content},
                    {'role': 'user', 'content': message},
                ],
                'temperature': cfg.temperature or 0.7,
                'max_tokens': cfg.max_tokens or 500,
            },
            timeout=20,
        )
        if resp.status_code == 200:
            data = resp.json()
            reply_text = data.get('choices', [{}])[0].get('message', {}).get('content', '')
            return {'reply': reply_text, 'options': [], 'session_id': session_id}
        else:
            return {'reply': 'عذراً، الذكاء الاصطناعي المباشر غير متوفر حالياً.', 'session_id': session_id}
    # 6️⃣ دالة إنشاء الفرصة الآلية عند قرار n8n (الأصلية)
    def _create_odoo_records(self, collected_data, session_id):
        env = request.env
        partner = None
        if collected_data.get('email'):
            partner = env['res.partner'].sudo().search([('email', '=', collected_data['email'])], limit=1)
        if not partner and collected_data.get('name'):
            partner = env['res.partner'].sudo().create({
                'name': collected_data.get('name', 'عميل جديد (دردشة)'),
                'email': collected_data.get('email', ''),
                'phone': collected_data.get('phone', ''),
            })

        crm_lead = env['crm.lead'].sudo().create({
            'name': f"طلب تأمين عبر الذكاء الاصطناعي — {collected_data.get('name', 'عميل جديد')}",
            'partner_id': partner.id if partner else False,
            'contact_name': collected_data.get('name', ''),
            'phone': collected_data.get('phone', ''),
            'email_from': collected_data.get('email', ''),
            'description': f"طلب مُسجل آلياً عبر دردشة الذكاء الاصطناعي.\nجلسة رقم: {session_id}",
            'type': 'opportunity',
        })
        base_url = env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        return {
            'crm_lead_id': crm_lead.id,
            'portal_url': f'{base_url}/my/leads',
        }
