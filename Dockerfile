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

# 4. إنشاء مجلد داخل مسار الـ HOME الخاص بمستخدم odoo حيث يمتلك الصلاحيات الكاملة تلقائياً
RUN mkdir -p /var/lib/odoo/.local/share/Odoo/sessions && \
    chown -R odoo:odoo /var/lib/odoo

USER odoo

# تعيين المتغير البيئي القياسي لأودو ليتوجه لهذا المجلد الآمن مباشرة لحفظ الجلسات والبيانات
ENV XDG_DATA_HOME=/var/lib/odoo/.local/share

EXPOSE 8069
CMD ["odoo"]
