# أضف أمر RUN هذا قبل خطوة تثبيت pip مباشرة:
RUN apt-get update && apt-get remove -y python3-cryptography

# خطوتك الحالية:
RUN if [ -f "requirements.txt" ]; then pip install --no-cache-dir -r requirements.txt --break-system-packages; fi
