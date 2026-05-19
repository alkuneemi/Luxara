FROM odoo:19.0

USER root

# 1. تحديث النظام وتثبيت المتطلبات الأساسية للنظام
RUN apt-get update && \
    apt-get install -y git ca-certificates python3-num2words python3-libsass || \
    (apt-get install -y python3-pip && pip install --no-cache-dir num2words libsass --break-system-packages) && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /mnt/extra-addons

# 2. استقبال التوكن وسحب مستودع Luxara الفعلي (فرع 19.0)
ARG GITHUB_TOKEN
RUN if [ -z "$GITHUB_TOKEN" ]; then echo "ERROR: GITHUB_TOKEN is not set"; exit 1; fi && \
    git clone --depth 1 -b 19.0 https://${GITHUB_TOKEN}@github.com/alkuneemi/Luxara.git .

# 3. إعادة تنظيم الملفات
RUN if [ -d "custom_addons" ]; then cp -r custom_addons/* . ; fi

# 4. التثبيت التلقائي لملف requirements.txt (الخطوة المفقودة)
# تأكد أن ملف requirements.txt موجود في جذر مستودع الـ GitHub الخاص بك
RUN if [ -f "requirements.txt" ]; then pip install --no-cache-dir -r requirements.txt --break-system-packages; fi

# 5. تهيئة مسار ثابت ومفتوح الصلاحيات للبيانات والجلسات
RUN mkdir -p /var/lib/odoo/data_dir && \
    chown -R odoo:odoo /var/lib/odoo

USER odoo

ENV ODOO_DATA_DIR=/var/lib/odoo/data_dir

EXPOSE 8069
CMD ["odoo"]
