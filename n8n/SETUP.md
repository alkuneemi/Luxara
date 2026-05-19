# Sahab Cloud — n8n SaaS Orchestrator

  ## الإعداد الكامل (قبل تشغيل الـ Workflow)

  ### 1. إنشاء Credentials في n8n

  #### GitHub API Token
  - **Type:** HTTP Header Auth
  - **Name:** `GitHub API Token`
  - **Header Name:** `Authorization`
  - **Header Value:** `token YOUR_GITHUB_PERSONAL_ACCESS_TOKEN`
  - الصلاحيات المطلوبة: `repo`, `workflow`

  #### Railway API Token
  - **Type:** HTTP Header Auth
  - **Name:** `Railway API Token`
  - **Header Name:** `Authorization`
  - **Header Value:** `Bearer YOUR_RAILWAY_API_TOKEN`
  - الرابط: https://railway.app/account/tokens

  ---

  ### 2. إعداد متغيرات البيئة في n8n (Variables)

  | اسم المتغير | القيمة | مثال |
  |---|---|---|
  | `SAHAB_WEBHOOK_SECRET` | مفتاح الأمان المشترك مع Odoo | `my-secret-key-123` |
  | `GITHUB_OWNER` | اسم حساب GitHub | `alkuneemi` |
  | `GITHUB_REPO` | اسم المستودع | `Luxara` |
  | `RAILWAY_PROJECT_ID` | معرف المشروع على Railway | `abc123...uuid` |
  | `RAILWAY_ENVIRONMENT_ID` | معرف البيئة على Railway | `def456...uuid` |
  | `BASE_DOMAIN` | النطاق الأساسي للمنصة | `sahabcloud.app` |

  > للحصول على RAILWAY_PROJECT_ID وRAILWAY_ENVIRONMENT_ID:
  > اذهب إلى Railway → Settings → يظهر Project ID في الرابط أو الإعدادات.

  ---

  ### 3. إعداد Odoo (sahab_cloud_controller)

  في Odoo → Sahab Cloud → إعدادات السيرفر، أدخل:
  - **رابط n8n Webhook:** `https://YOUR_N8N_URL/webhook/sahab-cloud`
  - **مفتاح الأمان:** نفس قيمة `SAHAB_WEBHOOK_SECRET`
  - **رابط GitHub:** `https://github.com/alkuneemi/Luxara`
  - **GitHub Token:** نفس التوكن المستخدم في Credentials
  - **Railway Project ID:** نفس القيمة أعلاه
  - **النطاق الأساسي:** `sahabcloud.app`

  ---

  ### 4. استيراد الـ Workflow في n8n

  1. افتح n8n
  2. New Workflow → Import from File
  3. اختر ملف `sahab_cloud_saas_workflow.json`
  4. ربط الـ Credentials (GitHub + Railway)
  5. فعّل الـ Workflow (Toggle Active)
  6. انسخ رابط الـ Webhook وضعه في Odoo

  ---

  ## هيكل العمليات (Actions)

  | العملية | الوصف | مصدر الطلب |
  |---|---|---|
  | `provision` | إنشاء بيئة عميل جديدة كاملة | Odoo → زر تفعيل الحاوية |
  | `provision_staging` | إنشاء بيئة اختبار معزولة | Odoo → زر إنشاء بيئة اختبار |
  | `suspend` | إيقاف مؤقت (عدم السداد) | Odoo → زر إيقاف مؤقت |
  | `resume` | استئناف الخدمة بعد السداد | Odoo → زر استئناف الخدمة |
  | `redeploy` | إعادة بناء الحاوية بالكود الجديد | Odoo → زر تحديث النظام |
  | `merge_staging` | دمج الاختبار على الإنتاج | Odoo → زر دمج وتطبيق |
  | `ping` | اختبار الاتصال | Odoo → زر اختبار الاتصال |

  ---

  ## Webhook URL

  `POST https://YOUR_N8N_URL/webhook/sahab-cloud`

  ### مثال على الحمولة (provision)
  ```json
  {
    "action": "provision",
    "client_id": 42,
    "partner_name": "شركة الأمين",
    "email": "info@alameen.com",
    "subdomain": "alameen",
    "prod_branch": "prod-alameen",
    "package": "الباقة المتكاملة",
    "modules": "account,sale_management,insurance_broker_suite",
    "github_repo": "https://github.com/alkuneemi/Luxara",
    "github_branch": "prod-alameen",
    "base_branch": "19.0",
    "callback_url": "https://sahab.odoo.com/saas/callback/42"
  }
  ```
  