# تنظیمات و آزمون تغییرات ساختاری و امنیتی

## مسیرهای کد

نشانی‌های عمومی در `saeenaria_portal.api` ثابت مانده‌اند. منطق اقدامات و داشبورد در `services/actions.py`، کاربران و عضویت در `services/people.py` و حساب کاربری در `services/account.py` است. این سرویس‌ها whitelist نیستند و از HTTP مستقیماً قابل فراخوانی نیستند؛ کنترل مجوز داخل خود سرویس‌ها نیز حفظ شده است.

در گزارش موجودی، استخراج و محاسبه به `purchase_reports/workflow_data.py` و نگهداری نسخه‌ها به `workflow_storage.py` منتقل شده است. `workflow.py` هماهنگی گردش کار و مسیرهای قبلی فراخوانی را نگه می‌دارد. قالب‌بندی و lint در `ruff.toml` فعلاً برای همین مرزهای بازآرایی‌شده اجباری است؛ فایل‌های قدیمی به‌تدریج می‌توانند به این پوشش اضافه شوند.

خروجی CSV اقدامات از endpoint سرور `saeenaria_portal.api.export_actions` با POST و CSRF دریافت می‌شود. شناسه‌های ارسالی دوباره با اقدامات مجاز کاربر و فیلترها تطبیق می‌یابند. CSV اقدامات و خرید هر دو از `csv_safety.safe_csv_cell` استفاده می‌کنند.

## اتصال رمزنگاری‌شده منابع

فایل اتصال همچنان در `private/purchase-order-connections.json` سایت قرار دارد. کلید `tls` هر منبع را به اطلاعات فعلی آن اضافه کنید. مثال زیر فقط شکل تنظیمات را نشان می‌دهد؛ نام‌ها و مسیرها نمونه‌اند:

```json
{
  "require_tls": true,
  "mysql": {
    "host": "mysql.internal.example",
    "port": 3306,
    "database": "reporting",
    "user": "portal_reader",
    "password": "REPLACE_PRIVATELY",
    "tls": {
      "enabled": true,
      "ca_file": "/home/frappe/frappe-bench/sites/SITE/private/mysql-ca.pem"
    }
  },
  "sqlserver": {
    "server": "sql.internal.example",
    "port": 1433,
    "database": "reporting",
    "user": "portal_reader",
    "password": "REPLACE_PRIVATELY",
    "tls": {
      "enabled": true,
      "ca_file": "/home/frappe/frappe-bench/sites/SITE/private/sqlserver-ca.pem"
    }
  }
}
```

نام host/server باید با گواهی سرور تطابق داشته باشد؛ غیرفعال کردن اعتبارسنجی گواهی یا محدود کردن رمزنگاری به مرحله ورود در این تنظیمات پشتیبانی نمی‌شود. CA باید در کانتینر برنامه و worker قابل خواندن باشد. MySQL علاوه بر گزینه‌های driver، برقراری سوکت TLS را پیش از اجرای پرس‌وجو بررسی می‌کند. برای SQL Server، CA به driver داده می‌شود و `validate_host=True` و `enc_login_only=False` تنظیم می‌شوند.

`configure.sh` تولید، `purchase_order_require_tls=true` را در تنظیمات مشترک bench قرار می‌دهد. بنابراین نبود تنظیم TLS معتبر، اتصال منبع را متوقف می‌کند. محیط توسعه فعلی بدون تغییر خودکار فایل اتصال به کار ادامه می‌دهد؛ برای فعال‌سازی سخت‌گیرانه در سایت موجود، پس از آماده کردن گواهی‌ها اجرا کنید:

```bash
bench --site SITE set-config purchase_order_require_tls True --parse
```

گواهی و تنظیمات واقعی منابع در این تغییر ساخته یا جایگزین نشده‌اند. فعال بودن TLS و مجوز SELECT واقعی حساب‌ها باید توسط مدیر همان سرورها تأیید شود. `readonly=True` به‌تنهایی مجوزهای SQL Server را محدود نمی‌کند. حساب اختصاصی گزارش باید فقط SELECT لازم داشته باشد و عضو نقش‌های نوشتن یا مدیریت نباشد.

در Linux، فایل اتصال باید متعلق به کاربر سرویس باشد، برای گروه و سایر کاربران قابل خواندن نباشد (مثلاً mode 0600) و پوشه private دسترسی محدود داشته باشد. نسخه پشتیبان آن نیز شامل رمز است و باید خصوصی و رمزنگاری‌شده نگهداری شود. فراداده محیط توسعه فعلی بررسی شد و فایل اتصال mode 0600 دارد؛ مجوز آن تغییر نکرد. تنظیم CA و TLS هر دو منبع هنوز موجود نیست. با env/bin/python /workspace/docker/check-source-security.py می‌توان این فراداده را بدون چاپ میزبان و رمز دوباره بررسی کرد.

مراجع driver: [PyMySQL connection options](https://pymysql.readthedocs.io/en/latest/modules/connections.html)، [python-tds TLS options](https://python-tds.readthedocs.io/en/1.16.1/pytds.html).

## مسئول پایش موجودی

تطبیق با نام کامل فرد حذف شده است. مسئول را با شناسه کاربر فعال سامانه تنظیم کنید:

```bash
bench --site SITE set-config inventory_reporting_owner USER_LOGIN
```

اگر این کلید در سایت قدیمی وجود نداشته باشد، فقط مسئول یکتای برنامه‌های موجود `INVPLAN-forecast`، `INVPLAN-variance` و `INVPLAN-urgency` به‌عنوان سازگاری انتخاب می‌شود. نبود مسئول یکتا یا غیرفعال بودن کاربر، خطای روشن می‌دهد؛ انتخاب تصادفی عضو واحد انجام نمی‌شود. مقدار تنظیم‌شده نامعتبر نیز با fallback پنهان نمی‌شود.

## اجرای بررسی‌ها

کنترل کیفیت مستقل از سایت:

```bash
python -m pip install -r requirements-dev.txt
python docker/check-code.py
```

این دستور lint و قالب‌بندی بخش‌های بازآرایی‌شده، نحو تمام Pythonها، تمام JavaScriptهای public و اسکریپت داخلی داشبورد را بررسی می‌کند. گردش GitHub Actions همین بررسی‌ها، آزمون‌های محاسباتی مستقل و اعتبار Composeها را اجرا می‌کند. اجرای remote گردش CI در این تغییر انجام نشده است.

در bench نصب‌شده، از ریشه bench اجرا کنید؛ مسیر `/workspace/docker` مربوط به mount توسعه فعلی است:

```bash
env/bin/python /workspace/docker/run-regressions.py --http
```

نام سایت از تنها سایت موجود تشخیص داده می‌شود. برای bench چندسایته یا مسیر متفاوت:

```bash
PORTAL_TEST_SITE=SITE PORTAL_TEST_BENCH=/path/to/bench env/bin/python /path/to/docker/run-regressions.py
```

گزینه `--http` به وب‌سرور در حال اجرا و `ADMIN_PASSWORD` محیط نیاز دارد. `PORTAL_TEST_HTTP_URL` آدرس داخلی آزمون را عوض می‌کند. نشست آزمون HTTP با POST دارای CSRF بسته می‌شود. آزمون‌های نقش و گردش بررسی از کاربران و حوزه‌های تصادفی موقت استفاده می‌کنند و تغییرات دیتابیس rollback می‌شوند؛ اتصال TLS با mock بررسی می‌شود و به منابع واقعی وصل نمی‌شود.

## ساخت

تصاویر bench توسعه، MariaDB و Redis به digest تصاویر فعلی نصب‌شده متصل شده‌اند. پایه‌های تولید نیز با digest حل‌شده از registry تثبیت شده‌اند. وابستگی‌های مستقیم jdatetime، python-tds و pyOpenSSL نسخه دقیق دارند. نسخه ۱۳۴ بسته نصب‌شده محیط موفق Linux/Python 3.14 در apps/saeenaria_portal/constraints-runtime.txt ثبت و هنگام نصب framework و برنامه به uv و pip اعمال می‌شود. فایل hash بسته‌ها و ابزارهای سیستم‌عامل را قفل نمی‌کند. پس از ارتقای کنترل‌شده و موفقیت مجموعه آزمون‌ها، با env/bin/python /workspace/docker/export-runtime-constraints.py آن را بازتولید کنید. ارتقای digestها و constraints باید همراه آزمون و برنامه به‌روزرسانی امنیتی انجام شود.

ساخت محلی انجام و image `saeenaria-portal:review-check` با موفقیت ساخته شد. بررسی آفلاین داخل image و pip check نیز موفق بود. بازتولید بدون استقرار:

```bash
docker build --tag saeenaria-portal:review-check .
```

برای تکرار بررسی آفلاین، پوشه docker را فقط‌خواندنی روی /checks در کانتینر mount و با Python محیط image، /checks/check-production-image.py را اجرا کنید؛ این بررسی هیچ اتصال شبکه‌ای نیاز ندارد.

Compose تولید همچنان به HTTPS در reverse proxy محیط واقعی، گواهی منابع، رمزهای مستقل و آزمون بازیابی backup نیاز دارد. آماده بودن این زیرساخت با آزمون‌های کد اثبات نمی‌شود.
