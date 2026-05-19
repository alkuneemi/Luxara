from odoo import http, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError
import json


class InsuranceWebsite(http.Controller):

    # ── PUBLIC WEBSITE ──────────────────────────────────────────────────────────

    @http.route('/insurance', type='http', auth='public', website=True)
    def insurance_home(self, **kwargs):
        categories = request.env['insurance.category'].sudo().search([
            ('website_published', '=', True),
            ('active', '=', True),
        ])
        return request.render('insurance_broker_suite.insurance_home', {
            'categories': categories,
        })

    
    @http.route('/insurance/category/<int:category_id>', type='http', auth='public', website=True)
    def insurance_category(self, category_id, **kwargs):
        category = request.env['insurance.category'].sudo().browse(category_id)
        if not category.exists() or not category.website_published:
            return request.not_found()
            
        show_guest_modal = False
        
        # التحقق: هل المستخدم زائر (غير مسجل الدخول) أم لا؟
        if request.env.user._is_public():
            # إذا كان زائراً ولم يقم بإدخال بياناته في هذه الجلسة مسبقاً
            if not request.session.get('guest_lead_created'):
                show_guest_modal = True
        else:
            # المستخدم مسجل دخوله: نقوم بإنشاء فرصة في موديول التأمين بناءً على الشروط الجديدة
            request.env['insurance.opportunity'].sudo()._create_website_opportunity({
                'partner_id': request.env.user.partner_id.id,
                'customer_name': request.env.user.partner_id.name,
                'customer_phone': request.env.user.partner_id.phone ,
                'customer_email': request.env.user.partner_id.email,
                'category_id': category.id,
            })

        types = category.type_ids.filtered(lambda t: t.website_published and t.active)
        return request.render('insurance_broker_suite.insurance_category_page', {
            'category': category,
            'types': types,
            'show_guest_modal': show_guest_modal,
        })

    # مسار استقبال بيانات الزائر غير المسجل وإنشاء الفرصة
    @http.route('/insurance/guest/lead', type='http', auth='public', website=True, methods=['POST'], csrf=False)
    def submit_guest_lead(self, **kwargs):
        try:
            raw = request.httprequest.get_data(as_text=True)
            body = json.loads(raw) if raw else {}
        except Exception:
            body = {}

        name = body.get('name')
        phone = body.get('phone')
        email = body.get('email')
        address = body.get('address')
        category_name = body.get('category_name', '')

        # البحث عن الفئة للحصول على الـ ID
        category = request.env['insurance.category'].sudo().search([('name', '=', category_name)], limit=1)

        if name and phone:
            # إنشاء الفرصة بناءً على الشروط من خلال الموديل
            request.env['insurance.opportunity'].sudo()._create_website_opportunity({
                'customer_name': name,
                'customer_phone': phone,
                'customer_email': email,
                'notes': f'Guest Address: {address}',
                'category_id': category.id if category else False,
            })
            # تعيين الجلسة لمنع ظهور النافذة مجدداً في نفس الزيارة
            request.session['guest_lead_created'] = True

        return request.make_response(
            json.dumps({'status': 'success'}),
            headers=[('Content-Type', 'application/json')]
        )
        
    @http.route('/insurance/type/<int:type_id>', type='http', auth='public', website=True)
    def insurance_type(self, type_id, **kwargs):
        ins_type = request.env['insurance.type'].sudo().browse(type_id)
        if not ins_type.exists() or not ins_type.website_published:
            return request.not_found()
        subtypes = ins_type.subtype_ids.filtered(lambda s: s.website_published and s.active)
        return request.render('insurance_broker_suite.insurance_type_page', {
            'ins_type': ins_type,
            'subtypes': subtypes,
        })

    @http.route('/insurance/apply/<int:subtype_id>', type='http', auth='public', website=True)
    def insurance_apply(self, subtype_id, **kwargs):
        subtype = request.env['insurance.subtype'].sudo().browse(subtype_id)
        if not subtype.exists() or not subtype.website_published:
            return request.not_found()
        return request.render('insurance_broker_suite.insurance_apply_form', {
            'subtype': subtype,
            'error': kwargs.get('error', {}),
            'values': kwargs.get('values', {}),
        })

    @http.route('/insurance/apply/<int:subtype_id>/submit', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def insurance_apply_submit(self, subtype_id, **post):
        subtype = request.env['insurance.subtype'].sudo().browse(subtype_id)
        if not subtype.exists():
            return request.not_found()

        # Validate required common fields
        errors = {}
        required = ['customer_name', 'customer_email', 'customer_phone']
        for field in required:
            if not post.get(field, '').strip():
                errors[field] = True

        if errors:
            return request.render('insurance_broker_suite.insurance_apply_form', {
                'subtype': subtype,
                'error': errors,
                'values': post,
            })

        # Build application values
        vals = {
            'subtype_id': subtype_id,
            'customer_name': post.get('customer_name', '').strip(),
            'customer_email': post.get('customer_email', '').strip(),
            'customer_phone': post.get('customer_phone', '').strip(),
            'id_number': post.get('id_number', '').strip(),
            'nationality': post.get('nationality', '').strip(),
            'status': 'submitted',
        }

        form_type = subtype.form_type

        # Motor fields
        if form_type == 'motor':
            vals.update({
                'motor_full_name': post.get('motor_full_name', ''),
                'motor_id_number': post.get('motor_id_number', ''),
                'motor_plate_number': post.get('motor_plate_number', ''),
                'motor_plate_character': post.get('motor_plate_character', ''),
                'motor_license_number': post.get('motor_license_number', ''),
                'motor_chassis_number': post.get('motor_chassis_number', ''),
                'motor_make': post.get('motor_make', ''),
                'motor_model': post.get('motor_model', ''),
                'motor_color': post.get('motor_color', ''),
            })
            if post.get('motor_year'):
                try:
                    vals['motor_year'] = int(post['motor_year'])
                except ValueError:
                    pass
            if post.get('motor_vehicle_registration_date'):
                vals['motor_vehicle_registration_date'] = post['motor_vehicle_registration_date']

        # Medical fields
        elif form_type in ('medical_individual', 'medical_corporate'):
            vals.update({
                'med_coverage_type': post.get('med_coverage_type', ''),
                'med_network_preference': post.get('med_network_preference', ''),
                'med_company_name': post.get('med_company_name', ''),
                'med_dental_required': bool(post.get('med_dental_required')),
                'med_optical_required': bool(post.get('med_optical_required')),
                'med_pre_existing': bool(post.get('med_pre_existing')),
                'med_pre_existing_details': post.get('med_pre_existing_details', ''),
            })
            if post.get('med_employee_count'):
                try:
                    vals['med_employee_count'] = int(post['med_employee_count'])
                except ValueError:
                    pass

        # Property / Fire fields
        elif form_type == 'property_fire':
            vals.update({
                'prop_address': post.get('prop_address', ''),
                'prop_cover_type': post.get('prop_cover_type', ''),
                'prop_usage': post.get('prop_usage', ''),
                'prop_any_previous_loss': bool(post.get('prop_any_previous_loss')),
                'prop_previous_loss_details': post.get('prop_previous_loss_details', ''),
                'prop_proposer_name': post.get('prop_proposer_name', ''),
                'prop_profession_business': post.get('prop_profession_business', ''),
                'prop_any_rejection': bool(post.get('prop_any_rejection')),
                'prop_rejection_details': post.get('prop_rejection_details', ''),
                'prop_construction_type': post.get('prop_construction_type', ''),
            })
            for f in ['prop_building_value', 'prop_contents_value']:
                if post.get(f):
                    try:
                        vals[f] = float(post[f].replace(',', ''))
                    except ValueError:
                        pass

        # Marine fields
        elif form_type == 'marine':
            vals.update({
                'marine_voyage_from': post.get('marine_voyage_from', ''),
                'marine_voyage_to': post.get('marine_voyage_to', ''),
                'marine_cargo_type': post.get('marine_cargo_type', ''),
                'marine_vessel_name': post.get('marine_vessel_name', ''),
                'marine_packing': post.get('marine_packing', ''),
            })
            for f in ['marine_departure_date', 'marine_arrival_date']:
                if post.get(f):
                    vals[f] = post[f]
            if post.get('marine_cargo_value'):
                try:
                    vals['marine_cargo_value'] = float(post['marine_cargo_value'].replace(',', ''))
                except ValueError:
                    pass

        # Life fields
        elif form_type == 'life':
            vals.update({
                'life_payment_frequency': post.get('life_payment_frequency', ''),
                'life_beneficiary_name': post.get('life_beneficiary_name', ''),
                'life_beneficiary_relation': post.get('life_beneficiary_relation', ''),
                'life_occupation': post.get('life_occupation', ''),
                'life_smoker': bool(post.get('life_smoker')),
                'life_hazardous_activity': bool(post.get('life_hazardous_activity')),
            })
            for f in ['life_sum_assured']:
                if post.get(f):
                    try:
                        vals[f] = float(post[f].replace(',', ''))
                    except ValueError:
                        pass
            if post.get('life_policy_term'):
                try:
                    vals['life_policy_term'] = int(post['life_policy_term'])
                except ValueError:
                    pass

        # Workmen Compensation
        elif form_type == 'workmen':
            vals.update({
                'wc_company_name': post.get('wc_company_name', ''),
                'wc_business_nature': post.get('wc_business_nature', ''),
                'wc_any_previous_claims': bool(post.get('wc_any_previous_claims')),
            })
            if post.get('wc_employee_count'):
                try:
                    vals['wc_employee_count'] = int(post['wc_employee_count'])
                except ValueError:
                    pass
            if post.get('wc_total_annual_wages'):
                try:
                    vals['wc_total_annual_wages'] = float(post['wc_total_annual_wages'].replace(',', ''))
                except ValueError:
                    pass

        # Link to portal user if logged in
        if request.env.user and request.env.user.partner_id and not request.env.user._is_public():
            vals['partner_id'] = request.env.user.partner_id.id

        application = request.env['insurance.application'].sudo().create(vals)

        # Handle file uploads
        files = request.httprequest.files.getlist('document_files')
        for f in files:
            if f and f.filename:
                import base64
                attachment = request.env['ir.attachment'].sudo().create({
                    'name': f.filename,
                    'datas': base64.b64encode(f.read()),
                    'res_model': 'insurance.application',
                    'res_id': application.id,
                })
                application.sudo().write({'document_ids': [(4, attachment.id)]})

        # Auto-create RFQ and dispatch to relevant insurance providers
        try:
            self._auto_create_rfq_for_application(application, subtype)
        except Exception:
            pass  # Never fail the application submission due to RFQ errors

        return request.redirect(f'/insurance/thank-you?ref={application.reference}&id={application.id}')

    def _auto_create_rfq_for_application(self, application, subtype):
        """Create an RFQ from a submitted application and notify relevant providers."""
        type_map = {
            'motor': 'motor',
            'medical_individual': 'medical',
            'medical_corporate': 'medical',
            'property_fire': 'property',
            'marine': 'marine',
            'life': 'life',
            'workmen': 'workmen_compensation',
        }
        insurance_type = type_map.get(subtype.form_type or '', 'motor')

        # Find or create a matching client record
        client = request.env['insurance.client'].sudo().search([
            ('email', '=', application.customer_email),
        ], limit=1)
        if not client:
            client = request.env['insurance.client'].sudo().create({
                'name': application.customer_name,
                'email': application.customer_email,
                'phone': application.customer_phone,
            })

        # Build requirements summary HTML
        lines = [
            f'<strong>Application Ref:</strong> {application.reference}',
            f'<strong>Insurance Product:</strong> {subtype.name}',
            f'<strong>Applicant:</strong> {application.customer_name}',
            f'<strong>Contact:</strong> {application.customer_phone} | {application.customer_email}',
        ]
        ft = subtype.form_type or ''
        if ft == 'motor':
            lines += [
                f'<strong>Vehicle:</strong> {application.motor_make or ""} {application.motor_model or ""} ({application.motor_year or ""})',
                f'<strong>Plate:</strong> {application.motor_plate_number or ""} {application.motor_plate_character or ""}',
                f'<strong>Chassis:</strong> {application.motor_chassis_number or ""}',
            ]
        elif ft in ('medical_individual', 'medical_corporate'):
            lines += [
                f'<strong>Coverage Type:</strong> {application.med_coverage_type or ""}',
                f'<strong>Network Preference:</strong> {application.med_network_preference or ""}',
            ]
            if application.med_company_name:
                lines.append(f'<strong>Company:</strong> {application.med_company_name}')
        elif ft == 'property_fire':
            lines += [
                f'<strong>Property Type:</strong> {getattr(application, "prop_type", "")}',
                f'<strong>Property Value:</strong> {getattr(application, "prop_value", "")} OMR',
            ]
        elif ft == 'life':
            lines += [
                f'<strong>Sum Assured:</strong> {getattr(application, "life_sum_assured", "")} OMR',
                f'<strong>Term:</strong> {getattr(application, "life_policy_term", "")} years',
            ]

        req_html = '<br/>'.join(lines)

        rfq = request.env['insurance.rfq'].sudo().create({
            'application_id': application.id,
            'client_id': client.id,
            'insurance_type': insurance_type,
            'status': 'draft',
            'notes': (
                f'Auto-generated from application {application.reference}.\n'
                f'Client: {application.customer_name} | {application.customer_email}'
            ),
            'requirements_summary': req_html,
        })
        rfq.action_send_to_providers()
        return rfq

    @http.route('/insurance/thank-you', type='http', auth='public', website=True)
    def insurance_thank_you(self, ref='', id=0, **kwargs):
        application = None
        if id:
            application = request.env['insurance.application'].sudo().browse(int(id))
            if not application.exists():
                application = None
        return request.render('insurance_broker_suite.insurance_thank_you', {
            'reference': ref,
            'application': application,
        })



      # ── WEBSITE VISIT OPPORTUNITY TRACKER ──────────────────────────────────────

    @http.route('/insurance/track-visit', type='http', auth='public', website=True, methods=['POST'], csrf=False)
    def track_website_visit(self, **kwargs):
      import json as _json
      if request.env.user._is_public():
          return request.make_response(
              _json.dumps({'status': 'public'}),
              headers=[('Content-Type', 'application/json')]
          )
      partner = request.env.user.partner_id
      existing = request.env['crm.lead'].sudo().search([
          ('partner_id', '=', partner.id),
          ('type', '=', 'opportunity'),
          ('active', '=', True),
          ('stage_id.is_won', '=', False),
      ], limit=1)
      if existing:
          return request.make_response(
              _json.dumps({'status': 'exists', 'id': existing.id}),
              headers=[('Content-Type', 'application/json')]
          )
      stage = request.env['crm.stage'].sudo().search([
          ('name', 'ilike', 'Opportunit'),
      ], limit=1)
      if not stage:
          stage = request.env['crm.stage'].sudo().search([], limit=1, order='sequence asc')
      opportunity = request.env['crm.lead'].sudo().create({
          'name': f'Website Visit — {partner.name}',
          'partner_id': partner.id,
          'type': 'opportunity',
          'stage_id': stage.id if stage else False,
          'description': (
              f'Auto-created: Client "{partner.name}" visited the insurance '
              f'website at /insurance and browsed available products.'
          ),
      })
      return request.make_response(
          _json.dumps({'status': 'created', 'id': opportunity.id}),
          headers=[('Content-Type', 'application/json')]
      )


class InsurancePortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'insurance_application_count' in counters:
            partner = request.env.user.partner_id
            values['insurance_application_count'] = request.env['insurance.application'].sudo().search_count([
                ('partner_id', '=', partner.id),
            ])
        return values

    @http.route('/my/insurance', type='http', auth='user', website=True)
    def portal_my_insurance(self, page=1, **kwargs):
        partner = request.env.user.partner_id
        domain = [('partner_id', '=', partner.id)]
        total = request.env['insurance.application'].sudo().search_count(domain)
        pager = portal_pager(
            url='/my/insurance',
            total=total,
            page=page,
            step=10,
        )
        applications = request.env['insurance.application'].sudo().search(
            domain, limit=10, offset=pager['offset'], order='create_date desc'
        )
        return request.render('insurance_broker_suite.portal_my_insurance', {
            'applications': applications,
            'pager': pager,
            'page_name': 'my_insurance',
        })

    @http.route('/my/insurance/<int:application_id>', type='http', auth='user', website=True)
    def portal_my_insurance_detail(self, application_id, **kwargs):
        partner = request.env.user.partner_id
        application = request.env['insurance.application'].sudo().browse(application_id)
        if not application.exists():
            return request.not_found()
        # Internal backend users (managers/staff) can preview any application.
        # Portal/public customers can only see their own applications.
        is_internal = request.env.user.has_group('base.group_user')
        if not is_internal and application.partner_id != partner:
            return request.not_found()
        # Fetch RFQs and all provider quotes for this application
        rfqs = request.env['insurance.rfq'].sudo().search([
            ('application_id', '=', application_id),
        ], order='create_date desc')
        quotes = rfqs.mapped('quote_ids').sorted('premium')
        return request.render('insurance_broker_suite.portal_my_insurance_detail', {
            'application': application,
            'rfqs': rfqs,
            'quotes': quotes,
            'page_name': 'my_insurance',
        })

    # ── AI CALL CENTER ───────────────────────────────────────────────────────────

    @http.route('/insurance/ai-chat', type='http', auth='public', website=True,
                methods=['POST'], csrf=False)
    def insurance_ai_chat(self, **kwargs):
        import json as _json
        try:
            raw = request.httprequest.get_data(as_text=True)
            body = _json.loads(raw) if raw else {}
        except Exception:
            body = {}

        message = (body.get('message') or '').strip()
        session_id = body.get('session_id') or 'anon'

        if not message:
            return request.make_response(
                _json.dumps({'error': 'No message provided'}),
                headers=[('Content-Type', 'application/json')]
            )

        # Build DB context (categories, types visible on website)
        context = self._build_ai_context(message)

        # Try n8n webhook (configured via Settings → Technical → Parameters)
        n8n_url = request.env['ir.config_parameter'].sudo().get_param(
            'insurance_broker_suite.n8n_webhook_url', '')

        if n8n_url:
            try:
                import urllib.request as _urllib
                import urllib.error
                payload = _json.dumps({
                    'message': message,
                    'session_id': session_id,
                    'context': context,
                }).encode('utf-8')
                req = _urllib.Request(
                    n8n_url, data=payload,
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                with _urllib.urlopen(req, timeout=18) as resp:
                    data = _json.loads(resp.read().decode('utf-8'))
                    return request.make_response(
                        _json.dumps({
                            'reply': data.get('reply', ''),
                            'quick_replies': data.get('quick_replies', []),
                            'source': 'ai',
                        }),
                        headers=[('Content-Type', 'application/json')]
                    )
            except Exception:
                pass  # Fall through to rule-based reply

        # Rule-based fallback (reads live data from DB)
        result = self._insurance_rule_reply(message, context)
        return request.make_response(
            _json.dumps(result),
            headers=[('Content-Type', 'application/json')]
        )

    def _build_ai_context(self, message):
        msg_lower = message.lower()
        context = {}

        # Published categories
        cats = request.env['insurance.category'].sudo().search([
            ('website_published', '=', True), ('active', '=', True)
        ])
        context['categories'] = [{'id': c.id, 'name': c.name} for c in cats]

        # Keyword → category name mapping for enriched context
        kw_map = {
            'motor': ['motor', 'car', 'vehicle', 'سيارة', 'مركبة', 'fleet'],
            'medical': ['medical', 'health', 'طبي', 'صحة', 'doctor', 'hospital'],
            'life': ['life', 'حياة', 'annuity', 'term', 'personal accident'],
            'property': ['property', 'fire', 'home', 'منزل', 'عقار', 'building'],
            'marine': ['marine', 'cargo', 'بحري', 'shipping', 'freight'],
            'engineering': ['engineering', 'construction', 'car ', 'ear ', 'هندسي'],
            'liability': ['liability', 'مسؤولية', 'indemnity', 'malpractice'],
            'cyber': ['cyber', 'سيبراني', 'data breach', 'digital'],
        }

        matched_types = []
        for cat_keyword, keywords in kw_map.items():
            if any(kw in msg_lower for kw in keywords):
                types = request.env['insurance.type'].sudo().search([
                    ('website_published', '=', True),
                    ('active', '=', True),
                    ('category_id.name', 'ilike', cat_keyword),
                ], limit=8)
                matched_types.extend([{'id': t.id, 'name': t.name} for t in types])
                if matched_types:
                    break

        if matched_types:
            context['relevant_types'] = matched_types

        # Live statistics for context richness
        try:
            context['stats'] = {
                'total_policies': request.env['insurance.policy'].sudo().search_count([('active', '=', True)]),
                'total_clients': request.env['insurance.client'].sudo().search_count([('active', '=', True)]),
                'total_products': request.env['insurance.subtype'].sudo().search_count([
                    ('website_published', '=', True), ('active', '=', True)
                ]),
            }
        except Exception:
            pass

        return context

    def _insurance_rule_reply(self, message, context):
        msg = message.lower()
        cats = [c['name'] for c in context.get('categories', [])]
        cats_str = ', '.join(cats[:6]) or 'Motor, Medical, Life, Property, Marine'

        # ── Motor ──────────────────────────────────────────────
        if any(k in msg for k in ['motor', 'car', 'vehicle', 'سيارة', 'مركبة', 'fleet', 'comprehensive', 'third party']):
            return {
                'reply': (
                    '🚗 **Motor Insurance** — We offer full coverage options:\n\n'
                    '• **Comprehensive** — Full cover: accident, fire, theft & third party\n'
                    '• **Third Party Liability (TPL)** — Mandatory basic coverage\n'
                    '• **Fleet Motor** — Corporate/company vehicle fleets\n'
                    '• **Classic Car** — Agreed value for vintage vehicles\n\n'
                    'To apply, click **Browse Insurance → Motor** and fill in your vehicle details. '
                    'We compare rates from all major Omani insurers and respond within **2 hours**.'
                ),
                'quick_replies': ['Apply for Comprehensive', 'Third Party Only', 'Fleet Motor Quote', 'What documents do I need?'],
                'source': 'rule',
            }

        # ── Medical ────────────────────────────────────────────
        if any(k in msg for k in ['medical', 'health', 'طبي', 'صحة', 'doctor', 'hospital', 'dental', 'optical']):
            return {
                'reply': (
                    '🏥 **Medical Insurance** — Our most popular category:\n\n'
                    '• **Individual Medical** — Personal health coverage\n'
                    '• **Family Medical** — Spouse + dependants under one plan\n'
                    '• **Group Medical** — Corporate employee health plans\n'
                    '• **Critical Illness** — Lump-sum on serious diagnosis\n'
                    '• **Dental & Optical** — Add-on riders available\n\n'
                    'Our network covers **180+ hospitals** and **600+ clinics** across Oman. '
                    'Pre-existing conditions are assessed case by case.'
                ),
                'quick_replies': ['Individual Medical', 'Family Plan', 'Group Medical', 'Critical Illness'],
                'source': 'rule',
            }

        # ── Life ───────────────────────────────────────────────
        if any(k in msg for k in ['life', 'حياة', 'term', 'annuity', 'personal accident', 'child', 'disability']):
            return {
                'reply': (
                    '❤️ **Life & Personal Insurance:**\n\n'
                    '• **Term Life** — Affordable pure death benefit protection\n'
                    '• **Personal Accident** — Cover for injuries, disability, death\n'
                    '• **Child Annuity** — Savings plan securing your child\'s education\n'
                    '• **Group Life** — Employee death-in-service benefit\n'
                    '• **Workmen Compensation (WC)** — Legal employer liability\n\n'
                    'Tell me more about your family situation and I\'ll recommend the best plan.'
                ),
                'quick_replies': ['Term Life', 'Personal Accident', 'Child Annuity', 'Group Life / WC'],
                'source': 'rule',
            }

        # ── Property ───────────────────────────────────────────
        if any(k in msg for k in ['property', 'fire', 'home', 'منزل', 'عقار', 'building', 'contents', 'relocation']):
            return {
                'reply': (
                    '🏠 **Property Insurance:**\n\n'
                    '• **Home Comprehensive** — Building structure + home contents\n'
                    '• **Fire & Allied Perils** — Fire, lightning, flood, storm\n'
                    '• **Property All Risk (PAR)** — Commercial properties, all risks\n'
                    '• **Relocation Insurance** — Moving/transit protection\n'
                    '• **Plate Glass** — Shop fronts and large glass panels\n\n'
                    'What type of property would you like to insure? Residential or commercial?'
                ),
                'quick_replies': ['Home Insurance', 'Commercial Property', 'Fire Insurance', 'Relocation'],
                'source': 'rule',
            }

        # ── Marine ─────────────────────────────────────────────
        if any(k in msg for k in ['marine', 'cargo', 'بحري', 'shipping', 'freight', 'yacht', 'vessel', 'hull']):
            return {
                'reply': (
                    '⚓ **Marine Insurance:**\n\n'
                    '• **Marine Cargo** — Goods in transit (sea, air, road)\n'
                    '• **Marine Hull** — Vessel hull and machinery\n'
                    '• **Yacht** — Personal watercraft cover\n'
                    '• **Freight Forwarder Liability** — Cargo handler coverage\n\n'
                    'We work with Lloyd\'s of London markets for specialist marine risks. '
                    'Please share your cargo type, route, and value for a tailored quote.'
                ),
                'quick_replies': ['Marine Cargo Quote', 'Yacht Insurance', 'Hull & Machinery', 'Freight Forwarder'],
                'source': 'rule',
            }

        # ── Claims ─────────────────────────────────────────────
        if any(k in msg for k in ['claim', 'مطالبة', 'accident', 'damage', 'stolen', 'broken', 'loss']):
            return {
                'reply': (
                    '📋 **Filing a Claim** — Here\'s how:\n\n'
                    '1. **Login** to your portal at `/my/insurance`\n'
                    '2. Find your active policy and click **"Report Claim"**\n'
                    '3. Fill in incident details and upload supporting documents\n'
                    '4. A claims adjuster will contact you within **4 hours**\n\n'
                    '**Emergency Claims Hotline:** 📞 +968 2400 0000 (24/7)\n\n'
                    'For motor accidents: take photos, get police report, and call immediately.'
                ),
                'quick_replies': ['Login to Portal', 'Emergency Hotline', 'What documents do I need?', 'Track Existing Claim'],
                'source': 'rule',
            }

        # ── Quote / pricing ────────────────────────────────────
        if any(k in msg for k in ['quote', 'price', 'cost', 'premium', 'سعر', 'تسعير', 'how much', 'كم']):
            return {
                'reply': (
                    '💰 **Getting a Quote is Free and Fast:**\n\n'
                    '1. Click **Browse Insurance** above\n'
                    '2. Select your insurance category and product\n'
                    '3. Fill in the application form\n'
                    '4. We compare all major insurers and respond within **2 hours**\n\n'
                    'Alternatively, tell me what type of insurance you need and I can guide you directly.'
                ),
                'quick_replies': ['Motor Quote', 'Medical Quote', 'Property Quote', 'Life Quote'],
                'source': 'rule',
            }

        # ── Application status ─────────────────────────────────
        if any(k in msg for k in ['status', 'application', 'track', 'follow', 'متابعة', 'حالة']):
            return {
                'reply': (
                    '🔍 **Track Your Application:**\n\n'
                    'Login to your customer portal to track all your applications, policies, and claims:\n\n'
                    '👉 `/my/insurance` — Your insurance dashboard\n\n'
                    'You\'ll find real-time status updates, policy documents, and claim history. '
                    'Don\'t have an account? Register using the email you provided in your application.'
                ),
                'quick_replies': ['Go to My Portal', 'I forgot my login', 'Contact Support'],
                'source': 'rule',
            }

        # ── Arabic greeting ────────────────────────────────────
        if any(k in msg for k in ['مرحبا', 'السلام', 'اهلا', 'مساء', 'صباح', 'كيف']):
            return {
                'reply': (
                    'أهلاً وسهلاً! أنا **أمين**، مساعدك الذكي لخدمات التأمين. 🛡️\n\n'
                    'يمكنني مساعدتك في:\n'
                    '• الحصول على عروض أسعار للتأمين\n'
                    '• تقديم طلبات تأمين جديدة\n'
                    '• متابعة المطالبات والوثائق\n'
                    '• الإجابة على أسئلتك التأمينية\n\n'
                    f'لدينا {len(context.get("categories", []))} فئات تأمين تشمل: {cats_str}\n\n'
                    'ما الذي تحتاج مساعدة فيه اليوم؟'
                ),
                'quick_replies': ['تأمين السيارات', 'التأمين الطبي', 'تأمين الحياة', 'عرض جميع المنتجات'],
                'source': 'rule',
            }

        # ── Default greeting / fallback ────────────────────────
        stats = context.get('stats', {})
        products_count = stats.get('total_products', 52)
        return {
            'reply': (
                f'Hello! I\'m **Ameen**, your AI Insurance Expert. 🛡️\n\n'
                f'We offer **{products_count} insurance products** across {len(cats)} categories including: {cats_str}.\n\n'
                'I can help you:\n'
                '• Get a **free quote** for any insurance\n'
                '• **Apply online** in minutes\n'
                '• **Track** your applications and claims\n'
                '• Answer any **insurance questions**\n\n'
                'What type of insurance are you looking for?'
            ),
            'quick_replies': ['🚗 Motor Insurance', '🏥 Medical Insurance', '❤️ Life Insurance', '🏠 Property Insurance'],
            'source': 'rule',
        }


# ════════════════════════════════════════════════════════════════════════════
#  Insurance Provider Portal Controller
#  Access: token-based (no login required)
#  Routes: /insurance/provider/*
#  API:    /insurance/provider/api/*  (Bearer token or ?token= param)
# ════════════════════════════════════════════════════════════════════════════
class InsuranceProviderPortal(http.Controller):

    def _get_provider(self, token):
        """Resolve a provider from a portal access token."""
        if not token:
            return None
        return request.env['insurance.company.provider'].sudo().search([
            ('portal_token', '=', token),
            ('portal_active', '=', True),
            ('active', '=', True),
        ], limit=1)

    # ── Web Portal Routes ────────────────────────────────────────────────────

    @http.route('/insurance/provider/', type='http', auth='public', website=True)
    def provider_home(self, token='', **kwargs):
        provider = self._get_provider(token)
        if not provider:
            return request.render('insurance_broker_suite.provider_portal_login', {})
        rfqs = request.env['insurance.rfq'].sudo().search([
            ('provider_ids', 'in', [provider.id]),
        ], order='create_date desc')
        quoted_rfq_ids = request.env['insurance.rfq.quote'].sudo().search([
            ('provider_id', '=', provider.id),
        ]).mapped('rfq_id.id')
        return request.render('insurance_broker_suite.provider_portal_dashboard', {
            'provider': provider,
            'rfqs': rfqs,
            'quoted_rfq_ids': quoted_rfq_ids,
            'token': token,
        })

    @http.route('/insurance/provider/rfq/<int:rfq_id>', type='http', auth='public', website=True)
    def provider_rfq_detail(self, rfq_id, token='', **kwargs):
        provider = self._get_provider(token)
        if not provider:
            return request.redirect('/insurance/provider/')
        rfq = request.env['insurance.rfq'].sudo().browse(rfq_id)
        if not rfq.exists() or provider.id not in rfq.provider_ids.ids:
            return request.not_found()
        existing_quote = request.env['insurance.rfq.quote'].sudo().search([
            ('rfq_id', '=', rfq_id),
            ('provider_id', '=', provider.id),
        ], limit=1)
        return request.render('insurance_broker_suite.provider_rfq_detail', {
            'provider': provider,
            'rfq': rfq,
            'existing_quote': existing_quote,
            'token': token,
            'error': kwargs.get('error', ''),
        })

    @http.route('/insurance/provider/rfq/<int:rfq_id>/submit',
                type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def provider_rfq_submit_quote(self, rfq_id, token='', **post):
        provider = self._get_provider(token)
        if not provider:
            return request.redirect('/insurance/provider/')
        rfq = request.env['insurance.rfq'].sudo().browse(rfq_id)
        if not rfq.exists() or provider.id not in rfq.provider_ids.ids:
            return request.not_found()

        try:
            premium = float(post.get('premium') or 0)
        except (ValueError, TypeError):
            premium = 0

        if premium <= 0:
            return request.render('insurance_broker_suite.provider_rfq_detail', {
                'provider': provider,
                'rfq': rfq,
                'existing_quote': None,
                'token': token,
                'error': 'Please enter a valid annual premium amount.',
            })

        from odoo import fields as _f
        quote_vals = {
            'rfq_id': rfq.id,
            'provider_id': provider.id,
            'insurer': provider.name,
            'premium': premium,
            'deductible': float(post.get('deductible') or 0),
            'coverage': post.get('coverage', '').strip(),
            'exclusions': post.get('exclusions', '').strip(),
            'network': post.get('network', '').strip(),
            'add_ons': post.get('add_ons', '').strip(),
            'notes': post.get('notes', '').strip(),
            'submitted_via_portal': True,
            'submitted_at': _f.Datetime.now(),
        }
        try:
            quote_vals['claim_settlement_ratio'] = float(post.get('claim_settlement_ratio') or 0)
        except (ValueError, TypeError):
            pass
        if post.get('validity_date'):
            quote_vals['validity_date'] = post['validity_date']

        existing = request.env['insurance.rfq.quote'].sudo().search([
            ('rfq_id', '=', rfq.id),
            ('provider_id', '=', provider.id),
        ], limit=1)
        if existing:
            existing.write(quote_vals)
        else:
            request.env['insurance.rfq.quote'].sudo().create(quote_vals)

        if rfq.status == 'sent':
            rfq.write({'status': 'responses_received'})

        return request.redirect(
            f'/insurance/provider/quote/success?token={token}&rfq_id={rfq_id}'
        )

    @http.route('/insurance/provider/quote/success', type='http', auth='public', website=True)
    def provider_quote_success(self, token='', rfq_id=0, **kwargs):
        provider = self._get_provider(token)
        rfq = None
        if rfq_id:
            rfq = request.env['insurance.rfq'].sudo().browse(int(rfq_id))
            if not rfq.exists():
                rfq = None
        return request.render('insurance_broker_suite.provider_quote_success', {
            'provider': provider,
            'rfq': rfq,
            'token': token,
        })

    @http.route('/insurance/provider/api', type='http', auth='public', website=True)
    def provider_api_docs(self, token='', **kwargs):
        provider = self._get_provider(token)
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        return request.render('insurance_broker_suite.provider_api_docs', {
            'provider': provider,
            'token': token,
            'base_url': base_url,
        })

    # ── REST API Endpoints ───────────────────────────────────────────────────

    @http.route('/insurance/provider/api/rfqs',
                type='http', auth='public', methods=['GET'], csrf=False)
    def api_list_rfqs(self, **kwargs):
        token = (
            request.httprequest.headers.get('Authorization', '').replace('Bearer ', '').strip()
            or kwargs.get('token', '')
        )
        provider = self._get_provider(token)
        if not provider:
            return request.make_response(
                json.dumps({'error': 'Invalid or missing token', 'code': 401}),
                headers=[('Content-Type', 'application/json')],
                status=401,
            )
        rfqs = request.env['insurance.rfq'].sudo().search([
            ('provider_ids', 'in', [provider.id]),
        ], order='create_date desc', limit=50)
        quoted_rfq_ids = set(
            request.env['insurance.rfq.quote'].sudo().search([
                ('provider_id', '=', provider.id),
            ]).mapped('rfq_id.id')
        )
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        result = []
        for rfq in rfqs:
            result.append({
                'id': rfq.id,
                'reference': rfq.reference_no,
                'insurance_type': rfq.insurance_type,
                'status': rfq.status,
                'sent_date': rfq.sent_date and rfq.sent_date.isoformat(),
                'response_deadline': rfq.response_deadline and rfq.response_deadline.isoformat(),
                'requirements': rfq.notes or '',
                'quoted': rfq.id in quoted_rfq_ids,
                'detail_url': f'{base_url}/insurance/provider/rfq/{rfq.id}?token={token}',
            })
        return request.make_response(
            json.dumps({'provider': provider.name, 'rfqs': result, 'count': len(result)}),
            headers=[('Content-Type', 'application/json')],
        )

    @http.route('/insurance/provider/api/quote',
                type='http', auth='public', methods=['POST'], csrf=False)
    def api_submit_quote(self, **kwargs):
        token = (
            request.httprequest.headers.get('Authorization', '').replace('Bearer ', '').strip()
            or kwargs.get('token', '')
        )
        provider = self._get_provider(token)
        if not provider:
            return request.make_response(
                json.dumps({'error': 'Invalid or missing token', 'code': 401}),
                headers=[('Content-Type', 'application/json')],
                status=401,
            )
        try:
            raw = request.httprequest.get_data(as_text=True)
            body = json.loads(raw) if raw else {}
        except Exception:
            body = {}

        rfq_id = body.get('rfq_id')
        premium = body.get('premium')
        if not rfq_id or premium is None:
            return request.make_response(
                json.dumps({'error': 'rfq_id and premium are required', 'code': 400}),
                headers=[('Content-Type', 'application/json')],
            )
        rfq = request.env['insurance.rfq'].sudo().browse(int(rfq_id))
        if not rfq.exists() or provider.id not in rfq.provider_ids.ids:
            return request.make_response(
                json.dumps({'error': 'RFQ not found or not assigned to this provider', 'code': 404}),
                headers=[('Content-Type', 'application/json')],
            )
        try:
            from odoo import fields as _f
            quote = request.env['insurance.rfq.quote'].sudo().create({
                'rfq_id': rfq.id,
                'provider_id': provider.id,
                'insurer': provider.name,
                'premium': float(premium),
                'deductible': float(body.get('deductible') or 0),
                'coverage': body.get('coverage', ''),
                'exclusions': body.get('exclusions', ''),
                'network': body.get('network', ''),
                'add_ons': body.get('add_ons', ''),
                'notes': body.get('notes', ''),
                'claim_settlement_ratio': float(body.get('claim_settlement_ratio') or 0),
                'validity_date': body.get('validity_date') or False,
                'submitted_via_portal': True,
                'submitted_at': _f.Datetime.now(),
            })
            if rfq.status == 'sent':
                rfq.write({'status': 'responses_received'})
            return request.make_response(
                json.dumps({
                    'success': True,
                    'quote_id': quote.id,
                    'message': 'Quote submitted successfully',
                }),
                headers=[('Content-Type', 'application/json')],
            )
        except Exception as e:
            return request.make_response(
                json.dumps({'error': str(e), 'code': 500}),
                headers=[('Content-Type', 'application/json')],
            )
