{
    'name': 'Insurance Broker Suite',
    'version': '19.0.2.3.0',
    'summary': 'Full-featured Insurance Broker Management System with Customer Portal & SAHAB AI',
    'description': '''
Insurance Broker Suite for Odoo 19
====================================
* Policy management with renewal alerts
* RFQ / quotation workflow
* Claims management
* Commission tracking
* Three Application Registries:
  - General Registry: جميع الطلبات من كل القنوات
  - Online Registry: طلبات البوابة الإلكترونية
  - Sales Team Registry: طلبات المبيعات مع نظام العمولة
* Customer-facing website (/insurance) with category → type → subtype → application form flow
* Customer portal (/my/insurance) for tracking application status
* Backend configuration for categories, types, sub-types, and insurance companies
* Dashboard with AI agent status and customer portal quick-link button
* AI Call Center stub
* Insurance Opportunities — نموذج موروث من crm.lead عبر _inherits:
  - يحتوي تلقائياً على جميع حقول crm.lead (الاسم، الشريك، المرحلة، الجوال...)
  - يُنشأ تلقائياً عند تسجيل العميل الدخول وزيارة صفحة التأمين
  - يتتبع رحلة العميل: categories → types → subtypes → form → payment → certificate
  - إنشاء طلب مبيعات تلقائي عند الوصول لمرحلة متقدمة
* نافذة تسجيل دخول حديثة ومنبثقة:
  - تظهر لأي زائر غير مسجل عند دخول أي صفحة من /insurance
  - تدعم تسجيل الدخول بالبريد وكلمة المرور
  - تدعم تسجيل الدخول عبر Google OAuth
  - بعد التسجيل يُنشأ سجل فرصة في crm.lead/insurance.opportunity
* SAHAB AI — conversational AI agent for insurance inquiry registration
* Oman Agent Sidebar — نظام المستشار الذكي والتسويق الموجه والمربوط بـ n8n
    ''',
    'author': 'Insurance Broker Suite',
    'category': 'Insurance',
    'license': 'OPL-1',
    'depends': [
        'base',
        'mail',
        'portal',
        'web',
        'crm',
        'website',
    ],
    'data': [
        # Security
        'security/ir.model.access.csv',
        # Sequences & CRON
        'data/insurance_sequence_data.xml',
        # CRM Pipeline Stages
        'data/crm_stage_data.xml',
        # Industry Tags seed data
        'data/insurance_industry_data.xml',
        # Default data (categories, types, subtypes)
        'data/insurance_category_data.xml',
        # Full seed data — all 52 insurance products, all models, all fields
        'data/insurance_full_seed_data.xml',
         'data/insurance_source_data.xml',
        # Backend views
        'views/insurance_dashboard_views.xml',
        'views/insurance_client_views.xml',
        'views/insurance_policy_views.xml',
        'views/insurance_rfq_views.xml',
        'views/insurance_claim_views.xml',
        'views/insurance_commission_views.xml',
        # Config views
        'views/insurance_category_views.xml',
        'views/insurance_type_views.xml',
        'views/insurance_subtype_views.xml',
        'views/insurance_company_views.xml',
        # Application Registries (General + Online + Sales)
        'views/insurance_application_views.xml',
        # Insurance Opportunities (insurance.opportunity inherits crm.lead)
        'views/insurance_opportunity_views.xml',
        # CRM Lead funnel extension views
        'views/crm_lead_funnel_views.xml',
        # SAHAB AI
        'views/sahab_ai_settings_views.xml',
        # Website / Portal templates
        'views/website_insurance.xml',
        'views/portal_insurance.xml',
        'views/website_insurance_provider.xml',
        'views/sahab_ai_widget.xml',
        # Login modal template (replaces old identify form)
        'views/insurance_identify_form.xml',
        
        # --- Oman Agent Template ---
        'views/oman_agent_templates.xml',
         'views/sahab_call_center.xml',
        
        # Menus (last)
        'views/insurance_menu.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'insurance_broker_suite/static/src/js/insurance_dashboard.js',
            'insurance_broker_suite/static/src/xml/insurance_dashboard.xml',
            'insurance_broker_suite/static/src/css/insurance_broker.css',
        ],
        'web.assets_frontend': [
            'insurance_broker_suite/static/src/css/insurance_portal.css',
            'insurance_broker_suite/static/src/css/insurance_provider.css',
            'insurance_broker_suite/static/src/css/sahab_ai_chat.css',
            'insurance_broker_suite/static/src/js/insurance_call_center.js',
            'insurance_broker_suite/static/src/js/sahab_ai_chat.js',
            'insurance_broker_suite/static/src/js/website_visit_tracker.js',
               'insurance_broker_suite/static/src/js/sahab_call_center.js',
            
            # --- Oman Agent Assets ---
       #     'insurance_broker_suite/static/src/css/oman_agent.css',
         #   'insurance_broker_suite/static/src/js/oman_agent.js',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
}
