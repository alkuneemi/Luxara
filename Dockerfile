FROM odoo:19.0

USER root

# 1. تثبيت أداة git وتحديث الشهادات الأمنية داخل الحاوية
RUN apt-get update && apt-get install -y git ca-certificates && rm -rf /var/lib/apt/lists/*

# 2. الانتقال إلى مجلد الإضافات الخارجية لـ أودو
WORKDIR /mnt/extra-addons

# 3. سحب الموديولات المخصصة باستخدام التوكن الجديد والرابط المصحح بحالة الأحرف (AlKuneemi)
RUN git clone --depth 1 -b 19.0 https://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@github.com/AlKuneemi/luxara-addons.git .

# 4. إعادة الصلاحيات للمستخدم الافتراضي لأودو
USER odoo

EXPOSE 8069
CMD ["odoo"]
