# -*- coding: utf-8 -*-
import json
import uuid
import requests
import base64
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class SahabAIController(http.Controller):

    @http.route('/sahab/ai/cc_interact', type='http', auth='public', methods=['POST'], csrf=False, website=True)
    def cc_interact(self, **post):
        """
        يستقبل النص المستخلص فورياً من الواجهة، يرسله لـ n8n، ويعيد الرد الصوتي والنصي.
        """
        cfg = request.env['sahab.ai.config'].sudo().get_config()
        session_id = post.get('session_id') or str(uuid.uuid4())
        user_message = post.get('message', '').strip()
        
        _logger.info(f"Call Center Received Instant Text: {user_message} (Session: {session_id})")

        if not user_message:
            return request.make_response(json.dumps({
                'user_text': '',
                'reply': 'لم يتم استلام أي نص. يرجى التحدث مجدداً.',
                'audio_base64': '',
                'session_id': session_id
            }), headers=[('Content-Type', 'application/json')])

        # 1. تمرير النص المستخلص إلى اليبهوك n8n
        agent_name = cfg.agent_name or 'Ameen'
        ai_result = self._bridge_to_ai(user_message, session_id, cfg, agent_name)
        reply_text = ai_result.get('reply', 'عذراً، واجهت مشكلة في الاتصال بالخادم الذكي.')

        # 2. تحويل رد الـ اليبهوك النصي إلى ملف صوتي مسموع عبر OpenAI TTS
        audio_base64 = ""
        if reply_text and cfg.openai_api_key:
            try:
                tts_resp = requests.post(
                    'https://api.openai.com/v1/audio/speech',
                    headers={
                        'Authorization': f'Bearer {cfg.openai_api_key}',
                        'Content-Type': 'application/json'
                    },
                    json={
                        'model': 'tts-1',
                        'voice': 'onyx',  # صوت ذكوري احترافي وعميق ومناسب جداً
                        'input': reply_text
                    },
                    timeout=20
                )
                if tts_resp.status_code == 200:
                    audio_base64 = base64.b64encode(tts_resp.content).decode('utf-8')
                else:
                    _logger.error(f"OpenAI TTS Failed: {tts_resp.text}")
            except Exception as e:
                _logger.error(f"Exception during OpenAI TTS Generation: {str(e)}")

        # إرجاع النتيجة المتكاملة للواجهة الأمامية لتقوم بتشغيلها
        return request.make_response(json.dumps({
            'user_text': user_message,
            'reply': reply_text,
            'audio_base64': audio_base64,
            'session_id': session_id,
            'options': ai_result.get('options', [])
        }), headers=[('Content-Type', 'application/json')])

    def _bridge_to_ai(self, message, session_id, cfg, agent_name):
        """إرسال الطلب المباشر لـ n8n Webhook"""
        if cfg.mode == 'n8n_webhook' and cfg.n8n_webhook_url:
            try:
                user = request.env.user
                partner = user.partner_id if not user._is_public() else False
                
                payload = {
                    'message': message,
                    'session_id': session_id,
                    'system_message': cfg.system_message or '',
                    'call_center_mode': True,
                    'client_info': {
                        'is_logged_in': not user._is_public(),
                        'name': partner.name if partner else 'زائر صوتي مباشر',
                        'email': partner.email if partner else '',
                    }
                }
                resp = requests.post(
                    cfg.n8n_webhook_url,
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=20
                )
                if resp.status_code == 200:
                    data = resp.json()
                    reply = data.get('reply') or data.get('message') or data.get('recommendation') or 'تمت معالجة اتصالك.'
                    return {
                        'reply': reply,
                        'options': data.get('options', []) or data.get('quick_replies', [])
                    }
            except Exception as e:
                _logger.error(f"Error connecting to n8n Webhook: {str(e)}")

        # الرد الاحتياطي لـ OpenAI لضمان عدم انقطاع المكالمة أبداً
        if cfg.openai_api_key:
            try:
                resp = requests.post(
                    'https://api.openai.com/v1/chat/completions',
                    headers={
                        'Authorization': f'Bearer {cfg.openai_api_key}',
                        'Content-Type': 'application/json',
                    },
                    json={
                        'model': cfg.ai_model or 'gpt-4o-mini',
                        'messages': [
                            {'role': 'system', 'content': f"أنت {agent_name}، مستشار تأمين عماني ذكي بالصوت. أجب باختصار شديد وبطريقة ودية عُمانية مخلصة."},
                            {'role': 'user', 'content': message},
                        ],
                        'temperature': 0.6,
                    },
                    timeout=15,
                )
                if resp.status_code == 200:
                    text = resp.json()['choices'][0]['message']['content']
                    return {'reply': text, 'options': []}
            except Exception as e:
                _logger.error(f"OpenAI Fallback Error: {str(e)}")

        return {'reply': 'الخادم الذكي تحت الصيانة حالياً، تفضل بالتحدث مجدداً بعد قليل.', 'options': []}
