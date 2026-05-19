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

# 3. الحيلة الذكية: إعادة تنظيم الملفات لكي يراها أودو بدون odoo.conf
# سنقوم بنسخ الموديولات المخصصة من مجلد custom_addons ونرفعها للمجلد الرئيسي مباشرة
RUN if [ -d "custom_addons" ]; then cp -r custom_addons/* . ; fi

USER odoo

EXPOSE 8069
CMD ["odoo"]
