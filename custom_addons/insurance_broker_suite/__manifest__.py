{
    'name': 'Insurance Broker Suite',
    'version': '19.0.5.0.0',
    'summary': 'Full-featured Insurance Broker Management System — Ameen Portal with Universal Quoting Engine & Customer Portal',
    'description': '''
Insurance Broker Suite for Odoo 19 — Ameen Portal
====================================================
* Ameen Portal Home Page (/): بوابة أمين الرئيسية المتكاملة
* Policy management with renewal alerts
* Universal Quoting Engine — نظام تسعيرة عام:
  - Manual Entry: موظفو البروكر يدخلون الأسعار يدوياً
  - Direct Portal: بوابة مباشرة — العميل يدخل بوابة الشركة بدون تسجيل دخول (رابط مباشر)
  - API Integration: ربط تلقائي عبر API مع شركات التأمين
* Company Integration Settings — إعدادات التكامل لكل شركة
* Product Pricing per Company: تسعيرة لكل منتج لكل شركة
* RFQ / quotation workflow
* Claims management
* Commission Rate Table — نسب العمولات المتفق عليها
* Automated Journal Entries — قيود محاسبية تلقائية
* Payment Gateway (Stripe) — بوابة الدفع الإلكتروني
* Commission tracking
* Three Application Registries:
  - General Registry: جميع الطلبات من كل القنوات
  - Online Registry: طلبات البوابة الإلكترونية
  - Sales Team Registry: طلبات المبيعات مع نظام العمولة
* Customer-facing website (/insurance) with dynamic forms per insurance type
* Insurance Opportunities with Requirement Details tab
* Customer portal (/my/insurance) for tracking application status
* SAHAB AI — conversational AI agent
* Oman Agent Sidebar
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
        'account',
        'payment',
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
        'views/insurance_commission_rate_views.xml',
        'views/insurance_commission_views.xml',
        # Config views
        'views/insurance_category_views.xml',
        'views/insurance_type_views.xml',
        'views/insurance_subtype_views.xml',
        'views/insurance_company_views.xml',
        # Product Pricing (per company per subtype)
        'views/insurance_company_pricing_views.xml',
        # Application Registries (General + Online + Sales)
        'views/insurance_application_views.xml',
        # Insurance Opportunities (insurance.opportunity inherits crm.lead)
        'views/insurance_opportunity_views.xml',
        # Universal Quotation System
        'views/insurance_quotation_views.xml',
        # CRM Lead funnel extension views
        'views/crm_lead_funnel_views.xml',
        # SAHAB AI
        'views/sahab_ai_settings_views.xml',
        # ════ AMEEN PORTAL HOME PAGE ════
        'views/ameen_home.xml',
        # Website / Portal templates
        'views/website_insurance.xml',
        'views/portal_insurance.xml',
        'views/website_insurance_provider.xml',
        'views/insurance_direct_portal.xml',
        'views/sahab_ai_widget.xml',
        # Login modal template
        'views/insurance_identify_form.xml',
        # Oman Agent
        'views/oman_agent_templates.xml',
        'views/sahab_call_center.xml',
        # Commission Rate Menu
        'views/insurance_commission_menu_patch.xml',
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
            # Portal styles
            'insurance_broker_suite/static/src/css/insurance_portal.css',
            'insurance_broker_suite/static/src/css/insurance_provider.css',
            'insurance_broker_suite/static/src/css/sahab_ai_chat.css',
            'insurance_broker_suite/static/src/js/insurance_call_center.js',
            'insurance_broker_suite/static/src/js/sahab_ai_chat.js',
            'insurance_broker_suite/static/src/js/website_visit_tracker.js',
            'insurance_broker_suite/static/src/js/sahab_call_center.js',
            # AI Document Scanner
            'insurance_broker_suite/static/src/css/ai_doc_scanner.css',
            'insurance_broker_suite/static/src/js/ai_doc_scanner.js',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'auto_install': False,
    'application': True,
}
