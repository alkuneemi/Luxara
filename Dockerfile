FROM python:3.11-slim-bookworm

# تثبيت اعتمادات النظام الأساسية التي يحتاجها أودو لقراءة ملفات PDF والـ الويب
RUN apt-get update && apt-get install -y \
    git \
    nodejs \
    npm \
    xz-utils \
    wget \
    libxml2-dev \
    libxslt1-dev \
    libpcap-dev \
    libldap2-dev \
    libsasl2-dev \
    libffi-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# تثبيت محول التقارير wkhtmltopdf الشهير لأودو
RUN wget https://github.com/wkhtmltopdf/wkhtmltopdf/releases/download/0.12.6.1-2/wkhtmltopdf_0.12.6.1-2.bullseye_amd64.deb \
    && apt-get update && apt-get install -y ./wkhtmltopdf_0.12.6.1-2.bullseye_amd64.deb \
    && rm ./wkhtmltopdf_0.12.6.1-2.bullseye_amd64.deb

# تجهيز مجلد العمل داخل السيرفر
WORKDIR /app

# نسخ الكود بالكامل إلى السيرفر
COPY . .

# تثبيت مكتبات البايثون الخاصة بأودو المتواجدة في ملف الاعتمادات
RUN pip install --no-cache-dir -r requirements.txt

# فتح المنفذ الافتراضي
EXPOSE 8069

# أمر تشغيل أودو وربطه بالمنفذ الديناميكي لـ Railway
CMD ["python3", "odoo-bin", "--http-port=8069"]
