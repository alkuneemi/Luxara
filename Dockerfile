FROM odoo:19.0

USER root

# 1. تحديث النظام وتثبيت المتطلبات
RUN apt-get update && \
    apt-get install -y git ca-certificates python3-num2words || \
    (apt-get install -y python3-pip && pip install --no-cache-dir num2words --break-system-packages) && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /mnt/extra-addons

# 2. استقبال التوكن وسحب مستودع Luxara الفعلي (فرع 19.0)
ARG GITHUB_TOKEN
RUN if [ -z "$GITHUB_TOKEN" ]; then echo "ERROR: GITHUB_TOKEN is not set"; exit 1; fi && \
    git clone --depth 1 -b 19.0 https://${GITHUB_TOKEN}@github.com/alkuneemi/Luxara.git .

# 3. إعادة تنظيم الملفات
RUN if [ -d "custom_addons" ]; then cp -r custom_addons/* . ; fi

# 4. تهيئة مسار بديل وآمن للبيانات والجلسات داخل الحاوية
RUN mkdir -p /tmp/odoo/sessions /tmp/odoo/filestore && \
    chown -R odoo:odoo /tmp/odoo

# تعيين متغيرات البيئة لإجبار أودو على استخدام المسار الجديد ذو الصلاحيات المفتوحة
ENV ODOO_RC=/etc/odoo/odoo.conf
RUN echo "[options]\ndata_dir = /tmp/odoo" > /etc/odoo/odoo.conf && \
    chown odoo:odoo /etc/odoo/odoo.conf

USER odoo

EXPOSE 8069
CMD ["odoo"]
