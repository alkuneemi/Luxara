FROM odoo:19.0

USER root

# 1. تثبيت أدوات النظام المعتادة
RUN apt-get update && apt-get install -y git ca-certificates && rm -rf /var/lib/apt/lists/*

# 2. تثبيت مكتبة num2words مع تخطي حماية النظام لبيئة الحاوية المعزولة
RUN pip install --no-cache-dir num2words --break-system-packages

WORKDIR /mnt/extra-addons

# 3. استنساخ المديولات من مستودع luxara-addons الخاص
RUN --mount=type=secret,id=GITHUB_TOKEN \
    if [ -f /run/secrets/GITHUB_TOKEN ]; then \
        TOKEN=$(cat /run/secrets/GITHUB_TOKEN); \
    else \
        TOKEN="${GITHUB_TOKEN}"; \
    fi && \
    if [ -z "$TOKEN" ]; then echo "ERROR: GITHUB_TOKEN is missing"; exit 1; fi && \
    git clone --depth 1 -b staging https://${TOKEN}@github.com/alkuneemi/luxara-addons.git .

# 4. نسخ المديولات المخصصة من هذا المستودع (custom_addons/)
#    تُضاف فوق المديولات المستنسخة دون حذفها
COPY custom_addons/ /mnt/extra-addons/

USER odoo

EXPOSE 8069
CMD ["odoo"]
