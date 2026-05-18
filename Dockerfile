FROM odoo:19.0

USER root

# 1. تثبيت أدوات النظام والمكتبات المطلوبة (بما فيها git و num2words)
RUN apt-get update && apt-get install -y git ca-certificates && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir num2words

WORKDIR /mnt/extra-addons

# 2. استقبال التوكن السري من إعدادات ريلوي أثناء البناء وسحب فرع staging بحسابك السمول
ARG GITHUB_TOKEN
RUN if [ -z "$GITHUB_TOKEN" ]; then echo "ERROR: GITHUB_TOKEN is not set"; exit 1; fi && \
    git clone --depth 1 -b staging https://${GITHUB_TOKEN}@github.com/alkuneemi/luxara-addons.git .

USER odoo

EXPOSE 8069
CMD ["odoo"]
