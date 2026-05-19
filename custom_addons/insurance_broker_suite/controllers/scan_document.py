# -*- coding: utf-8 -*-
import json
import base64
import logging
import requests

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

# ── Prompts per document type ────────────────────────────────────────────────
SCAN_PROMPTS = {
    'passport': (
        'You are an OCR expert. Extract ALL visible text from this passport image. '
        'Return ONLY a valid JSON object with these exact keys (use empty string if not found): '
        '{"full_name":"","id_number":"","nationality":"","date_of_birth":"","expiry_date":"","gender":""}. '
        'No explanation, no markdown, just the JSON object.'
    ),
    'id_card': (
        'You are an OCR expert. Extract ALL visible text from this national ID / civil card image. '
        'Return ONLY a valid JSON object: '
        '{"full_name":"","id_number":"","nationality":"","date_of_birth":"","gender":""}. '
        'No explanation, no markdown, just the JSON.'
    ),
    'car_registration': (
        'You are an OCR expert. Extract ALL visible text from this vehicle registration card image. '
        'Return ONLY a valid JSON object: '
        '{"plate_number":"","plate_character":"","make":"","model":"","year":"","chassis_number":"","color":"","registration_date":"","owner_name":"","owner_id":""}. '
        'No explanation, no markdown, just the JSON.'
    ),
    'driving_license': (
        'You are an OCR expert. Extract ALL visible text from this driving licence image. '
        'Return ONLY a valid JSON object: '
        '{"full_name":"","license_number":"","id_number":"","issue_date":"","expiry_date":"","nationality":""}. '
        'No explanation, no markdown, just the JSON.'
    ),
    'health_card': (
        'You are an OCR expert. Extract ALL visible text from this health insurance / medical card image. '
        'Return ONLY a valid JSON object: '
        '{"member_name":"","card_number":"","policy_number":"","coverage_type":"","company_name":"","expiry_date":""}. '
        'No explanation, no markdown, just the JSON.'
    ),
    'general': (
        'You are an OCR expert. Extract ALL visible text and data from this document image. '
        'Identify the document type and extract every readable field. '
        'Return ONLY a valid JSON object with snake_case keys matching the visible field labels. '
        'No explanation, no markdown, just the JSON.'
    ),
}

# ── Field mapping: AI key → HTML form field name ─────────────────────────────
FIELD_MAP = {
    # Personal / Passport / ID
    'full_name':         'customer_name',
    'id_number':         'id_number',
    'nationality':       'nationality',
    'owner_name':        'customer_name',
    'owner_id':          'id_number',
    'member_name':       'customer_name',
    # Motor fields
    'plate_number':      'motor_plate_number',
    'plate_character':   'motor_plate_character',
    'make':              'motor_make',
    'model':             'motor_model',
    'year':              'motor_year',
    'chassis_number':    'motor_chassis_number',
    'color':             'motor_color',
    'registration_date': 'motor_vehicle_registration_date',
    # Driving licence
    'license_number':    'motor_license_number',
    # Health card
    'card_number':       'id_number',
    'coverage_type':     'med_coverage_type',
    'company_name':      'med_company_name',
}


class DocumentScanController(http.Controller):

    @http.route('/insurance/ai/scan-document', type='json',
                auth='public', website=True, csrf=False)
    def scan_document(self, image_b64='', document_type='general', **kwargs):
        """
        Receives a base64 image from the website form scanner.
        Sends it to AI (OpenAI vision or n8n) and returns extracted fields
        ready to auto-fill the form.
        """
        if not image_b64:
            return {'success': False, 'error': 'No image received.'}

        cfg = request.env['sahab.ai.config'].sudo().get_config()
        prompt = SCAN_PROMPTS.get(document_type, SCAN_PROMPTS['general'])

        extracted_raw = {}

        try:
            if cfg.mode == 'direct_api' and cfg.openai_api_key:
                extracted_raw = self._scan_with_openai(image_b64, prompt, cfg)
            elif cfg.mode == 'n8n_webhook' and cfg.n8n_webhook_url:
                extracted_raw = self._scan_with_n8n(image_b64, document_type, prompt, cfg)
            else:
                return {'success': False, 'error': 'AI not configured. Please set up SAHAB AI settings.'}
        except Exception as e:
            _logger.error('Document scan error: %s', e)
            return {'success': False, 'error': str(e)[:300]}

        # Map AI keys → HTML form field names
        form_fields = {}
        for ai_key, value in extracted_raw.items():
            if value and isinstance(value, str) and value.strip():
                html_name = FIELD_MAP.get(ai_key)
                if html_name:
                    form_fields[html_name] = value.strip()
                else:
                    # Pass unmapped fields as-is (fallback)
                    form_fields[ai_key] = value.strip()

        return {
            'success': True,
            'document_type': document_type,
            'fields': form_fields,
            'raw': extracted_raw,
        }

    # ── OpenAI Vision ─────────────────────────────────────────────────────────
    def _scan_with_openai(self, image_b64, prompt, cfg):
        # Detect mime type from base64 prefix or default to jpeg
        mime = 'image/jpeg'
        if image_b64.startswith('data:'):
            parts = image_b64.split(',', 1)
            mime = parts[0].replace('data:', '').replace(';base64', '')
            image_b64 = parts[1]

        resp = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Authorization': f'Bearer {cfg.openai_api_key}',
                'Content-Type': 'application/json',
            },
            json={
                'model': 'gpt-4o',
                'messages': [{
                    'role': 'user',
                    'content': [
                        {'type': 'text', 'text': prompt},
                        {'type': 'image_url', 'image_url': {
                            'url': f'data:{mime};base64,{image_b64}',
                            'detail': 'high'
                        }},
                    ]
                }],
                'max_tokens': 800,
                'temperature': 0.1,
            },
            timeout=30,
        )
        if resp.status_code != 200:
            raise Exception(f'OpenAI Vision error: HTTP {resp.status_code} — {resp.text[:200]}')

        content = resp.json()['choices'][0]['message']['content'].strip()
        # Strip markdown code blocks if present
        if content.startswith('```'):
            content = content.split('\n', 1)[-1].rsplit('```', 1)[0]
        return json.loads(content)

    # ── n8n Webhook ───────────────────────────────────────────────────────────
    def _scan_with_n8n(self, image_b64, document_type, prompt, cfg):
        # Use test URL first, then live URL (same pattern as oman_agent.py)
        base_url = cfg.n8n_webhook_url or ''
        # Build a dedicated scan webhook path
        scan_url = base_url.rstrip('/') + '/scan' if base_url else ''

        payload = {
            'action': 'scan_document',
            'document_type': document_type,
            'prompt': prompt,
            'image_b64': image_b64,
        }

        resp = requests.post(
            scan_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30,
        )
        if resp.status_code != 200:
            raise Exception(f'n8n scan webhook error: HTTP {resp.status_code}')

        data = resp.json()
        # n8n should return {"fields": {...}} or the raw dict
        return data.get('fields', data)
