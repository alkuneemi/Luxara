FROM odoo:19.0

USER root

# 1. تحديث النظام وتثبيت المتطلبات البرمجية لتجميع التنسيقات والواجهة
RUN apt-get update && \
    apt-get install -y git ca-certificates python3-num2words python3-libsass && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /mnt/extra-addons

# 2. سحب مستودع الأكواد المخصصة
ARG GITHUB_TOKEN
RUN if [ -z "$GITHUB_TOKEN" ]; then echo "ERROR: GITHUB_TOKEN is not set"; exit 1; fi && \
    git clone --depth 1 -b 19.0 https://${GITHUB_TOKEN}@github.com/alkuneemi/Luxara.git .

# 3. تنظيم الموديولات المخصصة
RUN if [ -d "custom_addons" ]; then cp -r custom_addons/* . ; fi

# 4. تثبيت ملف المتطلبات البرمجية للموديولات إن وجد
RUN if [ -f "requirements.txt" ]; then pip install --no-cache-dir -r requirements.txt --break-system-packages; fi

# 5. تهيئة المجلد الداخلي ذو الصلاحيات المفتوحة بالكامل
RUN mkdir -p /var/lib/odoo/data_dir && \
    chown -R odoo:odoo /var/lib/odoo

USER odoo
ENV ODOO_DATA_DIR=/var/lib/odoo/data_dir

EXPOSE 8069
CMD ["odoo"]
