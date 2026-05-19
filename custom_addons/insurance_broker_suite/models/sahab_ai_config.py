# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError


class SahabAIConfig(models.Model):
    """Singleton configuration record for SAHAB AI settings."""
    _name = 'sahab.ai.config'
    _description = 'SAHAB AI Configuration'

    name = fields.Char(default='SAHAB AI', readonly=True)

    mode = fields.Selection([
        ('direct_api', 'Direct API (GPT-4o)'),
        ('n8n_webhook', 'n8n Workflow'),
    ], string='Integration Mode', default='n8n_webhook', required=True)

    openai_api_key = fields.Char(string='OpenAI API Key', groups='base.group_system')
    ai_model = fields.Selection([
        ('gpt-4o', 'GPT-4o (Recommended)'),
        ('gpt-4o-mini', 'GPT-4o Mini'),
        ('gpt-4-turbo', 'GPT-4 Turbo'),
        ('gpt-4', 'GPT-4'),
        ('gpt-3.5-turbo', 'GPT-3.5 Turbo'),
    ], string='AI Model', default='gpt-4o')

    temperature = fields.Float(string='Temperature', default=0.65)
    max_tokens = fields.Integer(string='Max Tokens', default=600)

    n8n_webhook_url = fields.Char(string='n8n Webhook URL')

    connection_status = fields.Selection([
        ('untested', 'Not Tested'),
        ('ok', 'Connected'),
        ('error', 'Connection Error'),
    ], string='Connection Status', default='untested', readonly=True)
    connection_message = fields.Char(string='Status Message', readonly=True)

    # إعدادات هوية ورسالة النظام للايجنت (مستشارك الصادق)
    agent_name = fields.Char(string='Agent Name', default='Oman Agent')
    company_name = fields.Char(string='Company Name', default='Ameen Hub Insurance Brokerage')
    
    welcome_message = fields.Text(
        string='Welcome Message (Arabic)',
        default='أهلاً وسهلاً بك! أنا مستشارك التأميني الصادق، يسعدني تحليل حركاتك ومساعدتك في اختيار أفضل تغطية تأمينية بأقل تكلفة ممكنة.',
    )
    
    system_message = fields.Text(
        string='Agent System Message (Prompt)',
        default=(
            'أنت مستشار تأميني ذكي ومخلص وتعمل كخبير تأمين مالي وقانوني في سلطنة عمان. '
            'مهمتك هي تحليل ملف العميل المرفق والعمليات المعلقة والاشتراكات المنتهية، '
            'وتقديم نصائح استشارية مخلصة وتوجيهات ترويجية ذكية تخدم مصلحة العميل أولاً وتزيد مبيعات الشركة ثانياً.'
        ),
        help="رسالة النظام الأساسية (System Prompt) التي توضح دور الايجنت وسلوكه وتُرسل ديناميكياً لـ n8n"
    )

    @api.model
    def get_config(self):
        cfg = self.search([], limit=1)
        if not cfg:
            cfg = self.create({'name': 'SAHAB AI'})
            
        # إضافة هذا الشرط لتعبئة رسالة النظام تلقائياً إذا كانت فارغة
        if not cfg.system_message:
            cfg.system_message = (
                'أنت مستشار تأميني ذكي ومخلص وتعمل كخبير تأمين مالي وقانوني في سلطنة عمان. '
                'مهمتك هي تحليل ملف العميل المرفق والعمليات المعلقة والاشتراكات المنتهية، '
                'وتقديم نصائح استشارية مخلصة وتوجيهات ترويجية ذكية تخدم مصلحة العميل أولاً وتزيد مبيعات الشركة ثانياً.'
            )
            
        return cfg

    def action_test_connection(self):
        self.ensure_one()
        try:
            import requests as _req
            if self.mode == 'direct_api':
                if not self.openai_api_key:
                    raise UserError('Please enter your OpenAI API Key first.')
                resp = _req.post(
                    'https://api.openai.com/v1/chat/completions',
                    headers={
                        'Authorization': 'Bearer %s' % self.openai_api_key,
                        'Content-Type': 'application/json',
                    },
                    json={
                        'model': self.ai_model or 'gpt-4o',
                        'messages': [{'role': 'user', 'content': 'ping'}],
                        'max_tokens': 5,
                    },
                    timeout=15,
                )
                if resp.status_code == 200:
                    self.write({'connection_status': 'ok',
                                'connection_message': 'Connected — Model: %s' % self.ai_model})
                else:
                    err = resp.json().get('error', {}).get('message', resp.text)
                    self.write({'connection_status': 'error', 'connection_message': err[:200]})
            elif self.mode == 'n8n_webhook':
                if not self.n8n_webhook_url:
                    raise UserError('Please enter the n8n Webhook URL first.')
                resp = _req.post(
                    self.n8n_webhook_url,
                    json={'message': 'ping', 'session_id': 'test', 'context': {}},
                    timeout=15,
                )
                if resp.status_code == 200:
                    self.write({'connection_status': 'ok',
                                'connection_message': 'n8n Webhook reachable'})
                else:
                    self.write({'connection_status': 'error',
                                'connection_message': 'HTTP %s' % resp.status_code})
        except UserError:
            raise
        except Exception as e:
            self.write({'connection_status': 'error', 'connection_message': str(e)[:200]})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'SAHAB AI — Connection Test',
                'message': self.connection_message or 'Done',
                'type': 'success' if self.connection_status == 'ok' else 'danger',
                'sticky': False,
            },
        }
