# پورتال داخلی جوش و برش صائین آریا

نسخه اولیه محلی مبتنی بر **Frappe 16.52.0**، بدون ERPNext.

نشانی: http://portal.localhost:8085/portal
کاربر اولیه: `Administrator`؛ رمز تصادفی در فایل محلی `.env` مقابل `ADMIN_PASSWORD` است. این فایل خارج از Git است.

## امکانات اولیه

- سه حوزه و تخصیص چندگانه کاربر، کنترل دسترسی در سرور.
- فرم فارسی RTL و ورودی شمسی اقدام، گزارش اقدامات، شاخص‌های مستقل، گزارش حوزه و تصمیم مدیریت.
- ۳۲ شناسنامه شاخص و ۲۷ قالب هفتگی و ماهانه؛ قالب‌ها تا تعیین مسئول غیرفعال‌اند.
- گردش گزارش، تصویر شاخص‌های هنگام ارسال و قفل تأییدشده با اصلاحیه مستقل.
- تقویم کاری شنبه تا چهارشنبه، تعطیلات و تولید برنامه بدون تکرار.
- ورود CSV با پیش‌نمایش خطا و تأیید، جلوگیری از تکرار، چاپ فارسی و CSV اقدامات.
- جداسازی نمایش داده واقعی و آزمایشی.

## اجرای محلی

Docker Desktop با Linux containers لازم است. `.env.example` را به `.env` کپی و رمزهای مستقل تصادفی تعیین کنید؛ در محیط آماده‌شده فایل از قبل وجود دارد.

```powershell
docker compose -f compose.dev.yaml up -d
docker compose -f compose.dev.yaml exec --user root bench chown frappe:frappe /home/frappe/workspace
docker compose -f compose.dev.yaml exec bench bash /workspace/docker/bootstrap.sh
docker compose -f compose.dev.yaml exec bench bash /workspace/docker/install-app.sh
docker compose -f compose.dev.yaml exec bench bash -c 'cd portal-bench && bench --site portal.localhost execute saeenaria_portal.seed.run'
docker compose -f compose.dev.yaml exec bench bash -lc 'cd /home/frappe/workspace/portal-bench && bench --site portal.localhost migrate && bench --site portal.localhost enable-scheduler'

docker compose -f compose.dev.yaml restart bench
```

راه‌اندازی مجدد روزمره فقط `docker compose -f compose.dev.yaml up -d` است. دیتابیس پورت عمومی ندارد و وب فقط روی کامپیوتر محلی منتشر می‌شود. volumeهای اختصاصی داده‌ها را نگه می‌دارند. هیچ سرویس شرکت تغییر نکرده است.

## آزمون‌ها

```powershell
docker compose -f compose.dev.yaml exec bench bash -c 'cd portal-bench && bench --site portal.localhost execute saeenaria_portal.smoke.run'
docker compose -f compose.dev.yaml exec bench bash -c 'cd portal-bench && bench --site portal.localhost execute saeenaria_portal.smoke.extended'
docker compose -f compose.dev.yaml exec bench bash -c 'cd portal-bench && bench --site portal.localhost execute saeenaria_portal.http_smoke.run'
```

آزمون‌های دامنه و قواعد از transaction rollback استفاده می‌کنند و داده عملکردی آزمایشی باقی نمی‌گذارند.

## مستندات

- [نیازمندی‌ها](docs/REQUIREMENTS.fa.md)
- [معماری](docs/ARCHITECTURE.fa.md)
- [راهنمای کاربران](docs/USER_GUIDE.fa.md)
- [استقرار، ارتقا، پشتیبان و بازیابی](docs/DEPLOYMENT.fa.md)
- [اتصال‌های آینده](docs/INTEGRATIONS.fa.md)
- [محدودیت‌ها](docs/LIMITATIONS.fa.md)
- [گزارش بررسی ساختار و امنیت](docs/CODE_SECURITY_REVIEW_FA.md)
- [تنظیمات امن منابع و اجرای مجموعه آزمون‌ها](docs/SECURE_CONFIGURATION_FA.md)
- [وضعیت ادامه کار](PROJECT_STATUS.md)

Compose توسعه روی سرور تولید اجرا نشود. بسته تولید جداست؛ ساخت image و بررسی آفلاین آن موفق شده، اما استقرار انتها به انتها، HTTPS و TLS منابع واقعی هنوز باید در staging تأیید شوند.

## ادامه روی رایانه دیگر

کد را از همین مخزن clone یا pull کنید و مراحل اجرای محلی بالا را انجام دهید. دستور `generate_doctypes.py` مربوط به تولید اولیه ساختار است؛ آن را برای راه‌اندازی یا ارتقا اجرا نکنید چون ممکن است تنظیمات جدید فرم‌ها را بازنویسی کند. ساختار فعلی فرم‌ها در مخزن ذخیره شده است.

- داده‌های سایت، کاربران، نقش‌ها، مرخصی‌ها و فایل‌های بارگذاری‌شده در Docker volume هستند و با Git منتقل نمی‌شوند. برای ادامه با همان داده‌ها، بکاپ دیتابیس و فایل‌های سایت و تنظیمات لازم را جداگانه و خصوصی منتقل و بازیابی کنید؛ راهنمای بازیابی در docs/DEPLOYMENT.fa.md است.
- فایل `.env`، فایل‌های `.local/` و رمزها عمداً در مخزن نیستند. برای نصب تازه از `.env.example` استفاده و رمزهای جدید تعیین کنید.
- برای ارتقای سایت موجود، پس از دریافت کد `bench --site portal.localhost migrate` و سپس پاک‌سازی cache را اجرا کنید. اگر نام اپ روی رایانه قبلی `saein_portal` بوده، راهنمای تغییر نام و PROJECT_STATUS.md را پیش از ارتقا بررسی کنید؛ نصب فعلی از `saeenaria_portal` استفاده می‌کند.
- مسیرهای اصلی: `/portal`، `/portal-staff` برای مرخصی و مأموریت، `/portal-reviews` برای بررسی فعالیت‌ها، و `/portal-training` برای آموزش.


گزارش‌های خرید و موجودی از ۲۰۲۶-۱۰-۲۴ به فایل تنظیمات اکسل یا ETL آن وابسته نیستند: داده‌های عملیاتی مستقیماً از سپیدار و سیاست، کاتالوگ و سفارش‌های در راه از دیتابیس پورتال خوانده می‌شوند. مدیریت مانده سفارش‌ها در `/portal-purchase#incoming` و بررسی مغایرت و تکمیل کالا در `/portal-products?status=issues` انجام می‌شود. راه‌اندازی و ارتقا: [گزارش‌های خرید](docs/PURCHASE_REPORTS_FA.md) و [استقرار](docs/DEPLOYMENT.fa.md).
