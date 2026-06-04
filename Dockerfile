FROM odoo:19.0

USER root

# 1. تحديث النظام وتثبيت المتطلبات الأساسية ومكتبات قواعد البيانات
RUN apt-get update && \
    apt-get install -y git ca-certificates python3-num2words python3-libsass libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /mnt/extra-addons

# 2. سحب مستودع Luxara
ARG GITHUB_TOKEN
RUN if [ -z "$GITHUB_TOKEN" ]; then echo "ERROR: GITHUB_TOKEN is not set"; exit 1; fi && \
    git clone --depth 1 -b 19.0 https://${GITHUB_TOKEN}@github.com/alkuneemi/Luxara.git .

# 3. تنظيم الموديولات وتثبيت المتطلبات
RUN if [ -d "custom_addons" ]; then cp -r custom_addons/* . ; fi
RUN if [ -f "requirements.txt" ]; then \
    pip install --no-cache-dir --ignore-installed cryptography -r requirements.txt --break-system-packages; \
    fi

# 4. الحل الجذري: إنشاء مجلدات الكاش والتنسيقات ومنحها صلاحيات كاملة ومطلقة
RUN mkdir -p /var/lib/odoo/data_dir/filestore && \
    mkdir -p /var/lib/odoo/data_dir/sessions && \
    chmod -R 777 /var/lib/odoo && \
    chown -R odoo:odoo /var/lib/odoo

USER odoo

# توجيه أودو للمسار الجديد ذو الصلاحيات المفتوحة
ENV ODOO_DATA_DIR=/var/lib/odoo/data_dir

EXPOSE 8069
CMD ["odoo"]
