# -*- coding: utf-8 -*-
"""
Controller: Smart Pricing Page — صفحة التسعيرة الذكية
Route: /ameen/pricing/<subtype_id>
Strategy: العميل يحصل على أفضل 3 أسعار فوراً بدون إدخال بيانات مسبق
"""
import json
import urllib.request
import urllib.error
import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class AmeenPricingController(http.Controller):

    # ─────────────────────────────────────────────────────────────────────────
    # GET /ameen/pricing/<subtype_id>  — صفحة التسعيرة الذكية الرئيسية
    # ─────────────────────────────────────────────────────────────────────────
    @http.route('/ameen/pricing/<int:subtype_id>', type='http',
                auth='public', website=True, sitemap=False)
    def ameen_pricing_page(self, subtype_id, **kwargs):
        """
        الصفحة الرئيسية للتسعيرة الذكية:
        - القسم العلوي: وكيل صحاب يُنشئ تقرير HTML مقارنة أفضل 3 أسعار
        - القسم السفلي: كل عروض شركات التأمين (قابلة للاختيار)
        """
        subtype = request.env['insurance.subtype'].sudo().browse(subtype_id)
        if not subtype.exists():
            return request.redirect('/ameen')

        # جلب كل التسعيرات المتاحة لهذا المنتج
        pricing_records = request.env['insurance.company.pricing'].sudo().search([
            ('subtype_id', '=', subtype_id),
            ('active', '=', True),
        ], order='base_premium asc')

        # أفضل 3 أسعار (للعرض المقارن)
        top3 = pricing_records[:3]

        # إعداد بيانات JSON للواجهة الأمامية
        all_prices_json = json.dumps([{
            'id': p.id,
            'company_name': p.company_id.name,
            'company_logo': p.company_id.logo_url or '',
            'base_premium': p.base_premium,
            'min_premium': p.min_premium,
            'max_premium': p.max_premium,
            'currency': p.currency or 'OMR',
            'coverage_summary': p.coverage_summary or '',
            'exclusions': p.exclusions or '',
            'add_ons': p.add_ons or '',
            'notes': p.pricing_notes or '',
        } for p in pricing_records], ensure_ascii=False)

        top3_json = json.dumps([{
            'id': p.id,
            'company_name': p.company_id.name,
            'base_premium': p.base_premium,
            'currency': p.currency or 'OMR',
        } for p in top3], ensure_ascii=False)

        return request.render('insurance_broker_suite.ameen_pricing_page', {
            'subtype': subtype,
            'pricing_records': pricing_records,
            'top3': top3,
            'all_prices_json': all_prices_json,
            'top3_json': top3_json,
            'form_url': f'/insurance/apply/{subtype_id}',
        })

    # ─────────────────────────────────────────────────────────────────────────
    # POST /ameen/pricing/ai-compare  — طلب تقرير الذكاء الاصطناعي من صحاب
    # ─────────────────────────────────────────────────────────────────────────
    @http.route('/ameen/pricing/ai-compare', type='http',
                auth='public', methods=['POST'], csrf=False, sitemap=False)
    def ameen_ai_compare(self, **kwargs):
        """
        يُستدعى من الواجهة الأمامية بعد تحميل الصفحة.
        يُرسل بيانات التسعيرة لوكيل صحاب (n8n) ويُعيد HTML تقرير المقارنة.
        """
        try:
            raw = request.httprequest.get_data(as_text=True)
            body = json.loads(raw) if raw else {}
        except Exception:
            body = {}

        subtype_id = int(body.get('subtype_id', 0))
        prices_data = body.get('prices', [])

        if not subtype_id or not prices_data:
            return request.make_response(
                json.dumps({'error': 'Missing data', 'html': ''}),
                headers=[('Content-Type', 'application/json')]
            )

        subtype = request.env['insurance.subtype'].sudo().browse(subtype_id)
        if not subtype.exists():
            return request.make_response(
                json.dumps({'error': 'Not found', 'html': ''}),
                headers=[('Content-Type', 'application/json')]
            )

        # صياغة الرسالة لوكيل صحاب
        product_name = subtype.name or ''
        prices_text = '\n'.join([
            f"- {p.get('company_name','')}: {p.get('base_premium',0)} {p.get('currency','OMR')} "
            f"(min: {p.get('min_premium',0)}, max: {p.get('max_premium',0)})"
            for p in prices_data[:10]
        ])

        ai_message = (
            f"أنت وكيل تأمين متخصص. قدم تقرير HTML احترافي ومقارنة مرئية لأفضل 3 أسعار "
            f"لمنتج التأمين: {product_name}\n\n"
            f"الأسعار المتاحة:\n{prices_text}\n\n"
            f"المطلوب: أنشئ كود HTML كامل يعرض:\n"
            f"1. بطاقة 'الأفضل' للسعر الأول مع شارة 'الأوفر'\n"
            f"2. بطاقة السعر الثاني مع 'الأشمل تغطية'\n"
            f"3. بطاقة السعر الثالث مع 'الأعلى جودة'\n"
            f"استخدم ألوان: #344B9B (أساسي), #5CAFE4 (ثانوي), تصميم بطاقات أنيق بدون CSS خارجي."
        )

        # الاتصال بـ n8n / صحاب
        n8n_url = request.env['ir.config_parameter'].sudo().get_param(
            'insurance_broker_suite.n8n_webhook_url', '')
        sahab_url = request.env['ir.config_parameter'].sudo().get_param(
            'insurance_broker_suite.sahab_pricing_webhook', '') or n8n_url

        comparison_html = ''

        if sahab_url:
            try:
                payload = json.dumps({
                    'message': ai_message,
                    'session_id': f'pricing_{subtype_id}',
                    'mode': 'pricing_comparison',
                    'subtype_id': subtype_id,
                    'product_name': product_name,
                    'prices': prices_data[:3],
                    'context': {
                        'action': 'generate_comparison_html',
                        'language': 'ar',
                        'brand_color': '#344B9B',
                    }
                }).encode('utf-8')

                req = urllib.request.Request(
                    sahab_url, data=payload,
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                with urllib.request.urlopen(req, timeout=25) as resp:
                    resp_data = json.loads(resp.read().decode('utf-8'))
                    comparison_html = (
                        resp_data.get('html') or
                        resp_data.get('reply') or
                        resp_data.get('output') or ''
                    )
            except Exception as e:
                _logger.warning(f'Sahab pricing AI error: {e}')

        # Fallback HTML إذا لم يتصل بالذكاء الاصطناعي
        if not comparison_html and prices_data:
            comparison_html = _build_fallback_comparison_html(prices_data[:3], product_name)

        return request.make_response(
            json.dumps({'html': comparison_html, 'status': 'ok'}),
            headers=[('Content-Type', 'application/json')]
        )


def _build_fallback_comparison_html(prices, product_name):
    """HTML احتياطي جميل إذا لم يتوفر اتصال بصحاب"""
    badges = ['🥇 الأوفر سعراً', '🥈 الأشمل تغطية', '🥉 الأعلى جودة']
    border_colors = ['#344B9B', '#5CAFE4', '#84CFFF']
    cards_html = ''
    for i, p in enumerate(prices[:3]):
        badge = badges[i] if i < len(badges) else ''
        border = border_colors[i] if i < len(border_colors) else '#344B9B'
        is_best = i == 0
        cards_html += f'''
        <div style="flex:1;min-width:200px;border:2.5px solid {border};border-radius:16px;
                    padding:24px;text-align:center;background:{('#EEF2FF' if is_best else '#fff')};
                    box-shadow:0 4px 20px rgba(52,75,155,0.12);position:relative;">
          {"<div style='position:absolute;top:-14px;left:50%;transform:translateX(-50%);background:#344B9B;color:#fff;padding:4px 16px;border-radius:20px;font-size:13px;font-weight:700;white-space:nowrap;'>الأفضل</div>" if is_best else ''}
          <div style="font-size:14px;font-weight:700;color:#344B9B;margin-bottom:8px;">{badge}</div>
          <div style="font-size:22px;font-weight:900;color:#1a1a2e;margin-bottom:4px;">{p.get('company_name','')}</div>
          <div style="font-size:34px;font-weight:900;color:{border};margin:12px 0;">
            {p.get('base_premium', 0):.3f}
          </div>
          <div style="font-size:13px;color:#666;">{p.get('currency','OMR')} / سنوياً</div>
          <div style="margin-top:16px;font-size:12px;color:#888;">
            من {p.get('min_premium',0):.3f} إلى {p.get('max_premium',0):.3f} {p.get('currency','OMR')}
          </div>
        </div>'''

    return f'''
    <div style="font-family:'Cairo',sans-serif;direction:rtl;padding:20px;">
      <div style="text-align:center;margin-bottom:24px;">
        <h2 style="color:#344B9B;font-size:22px;margin:0 0 6px;">
          🤖 مقارنة ذكية — {product_name}
        </h2>
        <p style="color:#666;font-size:14px;">أفضل 3 عروض منتقاة بواسطة صحاب AI</p>
      </div>
      <div style="display:flex;gap:20px;flex-wrap:wrap;justify-content:center;">
        {cards_html}
      </div>
    </div>'''
