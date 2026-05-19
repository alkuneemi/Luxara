FROM odoo:19.0

USER root

# 1. تثبيت أدوات النظام المعتادة
RUN apt-get update && apt-get install -y git ca-certificates && rm -rf /var/lib/apt/lists/*

# 2. تثبيت مكتبة num2words
RUN pip install --no-cache-dir num2words --break-system-packages

WORKDIR /mnt/extra-addons

# 3. استنساخ المديولات من مستودع luxara-addons
#    GITHUB_TOKEN يُمرَّر كـ Build Variable من Railway
ARG GITHUB_TOKEN
RUN if [ -z "$GITHUB_TOKEN" ]; then echo "ERROR: GITHUB_TOKEN build variable is missing"; exit 1; fi && \
    git clone --depth 1 -b staging https://${GITHUB_TOKEN}@github.com/alkuneemi/luxara-addons.git .

# 4. نسخ المديولات المخصصة من هذا المستودع (custom_addons/)
COPY custom_addons/ /mnt/extra-addons/

USER odoo

EXPOSE 8069
CMD ["odoo"]
