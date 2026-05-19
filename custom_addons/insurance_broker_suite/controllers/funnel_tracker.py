import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

SESSION_OPP_KEY = 'insurance_funnel_opp_id'


class InsuranceFunnelTracker(http.Controller):

    # ══════════════════════════════════════════════════════════════════════════
    #  INTERNAL HELPERS
    # ══════════════════════════════════════════════════════════════════════════

    def _get_opportunity(self):
        """Return the insurance.opportunity linked to this session (sudo), or empty set."""
        opp_id = request.session.get(SESSION_OPP_KEY)
        if not opp_id:
            return request.env['insurance.opportunity'].sudo().browse()
        opp = request.env['insurance.opportunity'].sudo().browse(opp_id).exists()
        if not opp:
            request.session.pop(SESSION_OPP_KEY, None)
        return opp

    def _create_opportunity(self, category_id=None, **extra):
        """Create a fresh insurance.opportunity (and its crm.lead), persist in session."""
        env = request.env
        partner = None
        if not env.user._is_public():
            partner = env.user.partner_id

        # ── التعديل هنا: البحث عن سجل المصدر الخاص بالموقع الإلكتروني من الموديل الجديد ──
        website_source = env['insurance.source'].sudo().search([('code', '=', 'website')], limit=1)

        vals = {
            'type': 'opportunity',
            'ins_source_id': website_source.id if website_source else False, # ربط المعرف ID الجديد
        }

        if partner:
            vals.update({
                'partner_id': partner.id,
                'contact_name': partner.name,
                'email_from': partner.email or '',
                'phone': partner.phone or '',
            })

        if category_id:
            category = env['insurance.category'].sudo().browse(category_id)
            if category.exists():
                vals['name'] = f'Website — {category.name} — {partner.name if partner else "Visitor"}'
                vals['ins_category_id'] = category_id
            else:
                vals['name'] = f'Website Insurance — {partner.name if partner else "Visitor"}'
        else:
            vals['name'] = f'Website Insurance — {partner.name if partner else "Visitor"}'

        # ── تحديث ذكي وموسع للبحث عن مرحلة الفرص ──
        stage = env['crm.stage'].sudo().search([
            ('id', '=', 11)
        ], limit=1, order='sequence asc')

        if not stage:
            stage = env['crm.stage'].sudo().search([
                '|', '|',
                ('name', 'ilike', 'opp'),
                ('name', 'ilike', 'فرص'),
            ], limit=1, order='sequence asc')

        if not stage:
            stage = env['crm.stage'].sudo().search([], limit=1, order='sequence asc')

        if stage:
            vals['stage_id'] = stage.id

        vals.update(extra)
        opp = env['insurance.opportunity'].sudo().create(vals)
        request.session[SESSION_OPP_KEY] = opp.id
        return opp

    def _get_or_create_opportunity(self, **create_kwargs):
        opp = self._get_opportunity()
        return opp if opp else self._create_opportunity(**create_kwargs)

    def _get_google_login_url(self, redirect):
        """Return the Google OAuth URL if the provider is configured, else None."""
        try:
            provider = request.env['auth.oauth.provider'].sudo().search([
                ('enabled', '=', True),
                ('name', 'ilike', 'Google'),
            ], limit=1)
            if provider:
                base = request.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
                return (
                    f'/auth/oauth/signin?provider_id={provider.id}'
                    f'&redirect={redirect}&db={request.env.cr.dbname}'
                )
        except Exception:
            pass
        return None

    # ══════════════════════════════════════════════════════════════════════════
    #  MAIN INSURANCE ENTRY POINT
    # ══════════════════════════════════════════════════════════════════════════

    @http.route('/insurance', type='http', auth='public', website=True)
    def insurance_main(self, **kwargs):
        """
        صفحة التأمين الرئيسية.
        - إذا كان المستخدم مسجلاً: تُعرض الصفحة مباشرة + تُسجَّل فرصة.
        - إذا لم يكن مسجلاً: تُعرض الصفحة مع نافذة تسجيل الدخول المنبثقة.
        """
        is_public = request.env.user._is_public()

        categories = request.env['insurance.category'].sudo().search([
            ('website_published', '=', True),
            ('active', '=', True),
        ])

        if not is_public:
            opp = self._get_or_create_opportunity()
            opp._funnel_advance(
                '1_categories',
                action_name='زار الأقسام الرئيسية',
                page_url='/insurance',
            )

        google_url = self._get_google_login_url('/insurance') if is_public else None

        return request.render('insurance_broker_suite.insurance_home', {
            'categories': categories,
            'show_login_modal': is_public,
            'google_login_url': google_url,
            'login_redirect': '/insurance',
        })

    # ══════════════════════════════════════════════════════════════════════════
    #  FUNNEL ROUTES
    # ══════════════════════════════════════════════════════════════════════════

    @http.route('/insurance/categories', type='http', auth='public', website=True)
    def insurance_categories(self, **kwargs):
        """Alias to main page, kept for backward compatibility."""
        return request.redirect('/insurance')

    @http.route('/insurance/category/<int:category_id>/types', type='http',
                auth='public', website=True)
    def insurance_category_types(self, category_id, **kwargs):
        if request.env.user._is_public():
            google_url = self._get_google_login_url(
                f'/insurance/category/{category_id}/types')
            categories = request.env['insurance.category'].sudo().search([
                ('website_published', '=', True), ('active', '=', True)])
            return request.render('insurance_broker_suite.insurance_home', {
                'categories': categories,
                'show_login_modal': True,
                'google_login_url': google_url,
                'login_redirect': f'/insurance/category/{category_id}/types',
            })

        category = request.env['insurance.category'].sudo().browse(category_id)
        if not category.exists() or not category.website_published:
            return request.not_found()

        opp = self._get_or_create_opportunity(category_id=category_id)
        opp._funnel_advance(
            '2_types',
            action_name=f'زار أنواع: {category.name}',
            page_url=f'/insurance/category/{category_id}/types',
            last_category_id=category_id,
        )
        if not opp.ins_category_id:
            opp.sudo().write({'ins_category_id': category_id})

        types = category.type_ids.filtered(
            lambda t: t.website_published and t.active)
        return request.render('insurance_broker_suite.insurance_category_page', {
            'category': category,
            'types': types,
        })

    @http.route('/insurance/type/<int:type_id>/subtypes', type='http',
                auth='public', website=True)
    def insurance_type_subtypes(self, type_id, **kwargs):
        if request.env.user._is_public():
            google_url = self._get_google_login_url(
                f'/insurance/type/{type_id}/subtypes')
            categories = request.env['insurance.category'].sudo().search([
                ('website_published', '=', True), ('active', '=', True)])
            return request.render('insurance_broker_suite.insurance_home', {
                'categories': categories,
                'show_login_modal': True,
                'google_login_url': google_url,
                'login_redirect': f'/insurance/type/{type_id}/subtypes',
            })

        ins_type = request.env['insurance.type'].sudo().browse(type_id)
        if not ins_type.exists() or not ins_type.website_published:
            return request.not_found()

        opp = self._get_or_create_opportunity()
        opp._funnel_advance(
            '3_subtypes',
            action_name=f'زار الأنواع الفرعية: {ins_type.name}',
            page_url=f'/insurance/type/{type_id}/subtypes',
            last_type_id=type_id,
        )
        if not opp.ins_type_id:
            opp.sudo().write({'ins_type_id': type_id})

        subtypes = ins_type.subtype_ids.filtered(
            lambda s: s.website_published and s.active)
        return request.render('insurance_broker_suite.insurance_type_page', {
            'ins_type': ins_type,
            'subtypes': subtypes,
        })

    @http.route('/insurance/application/form', type='http',
                auth='public', website=True)
    def insurance_application_form(self, subtype_id=None, **kwargs):
        redirect = f'/insurance/application/form?subtype_id={subtype_id}' if subtype_id else '/insurance/application/form'
        if request.env.user._is_public():
            google_url = self._get_google_login_url(redirect)
            categories = request.env['insurance.category'].sudo().search([
                ('website_published', '=', True), ('active', '=', True)])
            return request.render('insurance_broker_suite.insurance_home', {
                'categories': categories,
                'show_login_modal': True,
                'google_login_url': google_url,
                'login_redirect': redirect,
            })

        extra = {}
        if subtype_id:
            extra['last_subtype_id'] = int(subtype_id)

        opp = self._get_or_create_opportunity()
        opp._funnel_advance(
            '4_form',
            action_name='فتح استمارة التقديم',
            page_url='/insurance/application/form',
            **extra,
        )
        if subtype_id and not opp.ins_subtype_id:
            opp.sudo().write({'ins_subtype_id': int(subtype_id)})

        subtype = None
        if subtype_id:
            subtype = request.env['insurance.subtype'].sudo().browse(int(subtype_id))
            if not subtype.exists():
                subtype = None

        return request.render('insurance_broker_suite.insurance_apply_form', {
            'subtype': subtype,
            'error': {},
            'values': {},
        })

    @http.route('/insurance/payment', type='http', auth='user', website=True)
    def insurance_payment(self, **kwargs):
        opp = self._get_or_create_opportunity()
        opp._funnel_advance(
            '5_payment',
            action_name='وصل إلى صفحة الدفع',
            page_url='/insurance/payment',
        )
        return request.render('insurance_broker_suite.insurance_payment_page', {})

    @http.route('/insurance/success', type='http', auth='user', website=True)
    def insurance_success(self, **kwargs):
        opp = self._get_or_create_opportunity()
        opp._funnel_advance(
            '6_completed',
            action_name='أكمل العملية بنجاح — تم الدفع',
            page_url='/insurance/success',
        )
        request.session.pop(SESSION_OPP_KEY, None)
        return request.render('insurance_broker_suite.insurance_success_page', {})

    # ══════════════════════════════════════════════════════════════════════════
    #  LOGIN HANDLER — AJAX endpoint for the login modal
    # ══════════════════════════════════════════════════════════════════════════

    @http.route('/insurance/ajax-login', type='http', auth='public',
                website=True, methods=['POST'], csrf=True)
    def insurance_ajax_login(self, login='', password='', redirect='/', **kwargs):
        import werkzeug
        try:
            request.session.authenticate(request.env.cr.dbname, login, password)
            if not request.env.user._is_public():
                opp = self._get_or_create_opportunity()
                opp._funnel_advance(
                    '1_categories',
                    action_name='سجّل دخوله وزار صفحة التأمين',
                    page_url=redirect,
                )
                return request.redirect(redirect or '/insurance')
        except Exception:
            pass
        return request.redirect(f'{redirect or "/insurance"}?login_error=1')

    # ══════════════════════════════════════════════════════════════════════════
    #  ASYNC JSON ENDPOINT (for JavaScript-driven tracking)
    # ══════════════════════════════════════════════════════════════════════════

    @http.route('/insurance/track', type='json', auth='public',
                website=True, methods=['POST'], csrf=False)
    def track_step_json(self, step, action_name, page_url=None,
                        category_id=None, type_id=None, subtype_id=None):
        VALID = {'1_categories', '2_types', '3_subtypes',
                 '4_form', '5_payment', '6_completed'}
        if step not in VALID:
            return {'status': 'error', 'reason': 'invalid step'}
        if request.env.user._is_public():
            return {'status': 'error', 'reason': 'not logged in'}

        extra = {}
        if category_id:
            extra['last_category_id'] = int(category_id)
        if type_id:
            extra['last_type_id'] = int(type_id)
        if subtype_id:
            extra['last_subtype_id'] = int(subtype_id)

        opp = self._get_or_create_opportunity()
        opp._funnel_advance(step, action_name=action_name,
                            page_url=page_url, **extra)
        return {'status': 'ok', 'lead_id': opp.lead_id.id, 'opp_id': opp.id}
