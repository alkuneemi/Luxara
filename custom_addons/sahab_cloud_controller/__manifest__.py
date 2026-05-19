# -*- coding: utf-8 -*-
  {
      'name': 'Sahab Cloud Controller',
      'version': '19.0.1.0.0',
      'summary': 'إدارة دورة حياة حاويات عملاء Sahab Cloud',
      'description': """
          موديول التحكم المركزي لمنصة Sahab Cloud.
          يدير إنشاء وتشغيل وإيقاف بيئات Odoo للعملاء
          عبر التكامل مع n8n وRailway وGitHub.
      """,
      'author': 'Sahab Cloud',
      'website': 'https://sahabcloud.app',
      'category': 'Technical/SaaS',
      'license': 'LGPL-3',
      'depends': [
          'base',
          'mail',
          'sale_management',
          'portal',
      ],
      'data': [
          'security/ir.model.access.csv',
          'data/webhook_templates.xml',
          'views/saas_package_views.xml',
          'views/saas_client_views.xml',
          'views/saas_server_views.xml',
          'views/saas_menus.xml',
      ],
      'installable': True,
      'application': True,
      'auto_install': False,
  }
  