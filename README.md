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
docker compose -f compose.dev.yaml exec bench python /workspace/apps/saein_portal/generate_doctypes.py
docker compose -f compose.dev.yaml exec bench bash /workspace/docker/install-app.sh
docker compose -f compose.dev.yaml exec bench bash -c 'cd portal-bench && bench --site portal.localhost execute saein_portal.seed.run'
docker compose -f compose.dev.yaml restart bench
```

راه‌اندازی مجدد روزمره فقط `docker compose -f compose.dev.yaml up -d` است. دیتابیس پورت عمومی ندارد و وب فقط روی کامپیوتر محلی منتشر می‌شود. volumeهای اختصاصی داده‌ها را نگه می‌دارند. هیچ سرویس شرکت تغییر نکرده است.

## آزمون‌ها

```powershell
docker compose -f compose.dev.yaml exec bench bash -c 'cd portal-bench && bench --site portal.localhost execute saein_portal.smoke.run'
docker compose -f compose.dev.yaml exec bench bash -c 'cd portal-bench && bench --site portal.localhost execute saein_portal.smoke.extended'
docker compose -f compose.dev.yaml exec bench bash -c 'cd portal-bench && bench --site portal.localhost execute saein_portal.http_smoke.run'
```

آزمون‌های دامنه و قواعد از transaction rollback استفاده می‌کنند و داده عملکردی آزمایشی باقی نمی‌گذارند.

## مستندات

- [نیازمندی‌ها](docs/REQUIREMENTS.fa.md)
- [معماری](docs/ARCHITECTURE.fa.md)
- [راهنمای کاربران](docs/USER_GUIDE.fa.md)
- [استقرار، ارتقا، پشتیبان و بازیابی](docs/DEPLOYMENT.fa.md)
- [اتصال‌های آینده](docs/INTEGRATIONS.fa.md)
- [محدودیت‌ها](docs/LIMITATIONS.fa.md)
- [وضعیت ادامه کار](PROJECT_STATUS.md)

Compose توسعه روی سرور تولید اجرا نشود. بسته تولید جداست و هنوز آزمون ساخت image و استقرار کامل نشده است.
