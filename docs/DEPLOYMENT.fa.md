# استقرار، ارتقا و بازیابی

## وضعیت بسته

محیط توسعه محلی اجرا و آزمون شده است. Dockerfile و compose.prod.yaml بسته پیشنهادی تولید هستند؛ ساخت image تولید و آزمون انتها به انتهای آن هنوز تأیید نشده‌اند. پیش از استفاده واقعی روی یک میزبان آزمایشی مستقل بررسی شوند. نصب روی سرور شرکت انجام نشده است.

## بررسی سرور Ubuntu 24.04

فقط در پوشه پروژه جدید کار کنید، مثلاً `/opt/saeenaria-portal`. مسیر `/opt/inventory-etl`، MySQL موجود، شبکه و volumeهای سرویس‌های فعلی را تغییر ندهید.

```bash
bash deploy/preflight.sh
```

خروجی CPU، RAM آزاد، فضای دیسک، پورت‌ها، مصرف Docker و شبکه‌ها را بررسی کنید. ظرفیت کافی برای ساخت image و پشتیبان لازم است. هیچ حدی را بدون مشاهده بار واقعی تضمین نکنید. پورت پیش‌فرض ۱۸۰۸۵ صرفاً پیشنهاد است و باید آزاد باشد. شبکه پیش‌فرض اختصاصی پروژه نیز از نظر تداخل subnet با شبکه داخلی و Docker بررسی شود.

## آماده‌سازی مستقل

```bash
cd /opt/saeenaria-portal
cp deploy/.env.example .env
chmod 600 .env
# با ویرایشگر SITE_NAME و رمزهای مستقل را تعیین کنید.
docker compose -f compose.prod.yaml config --quiet
docker compose -f compose.prod.yaml build
docker compose -f compose.prod.yaml up -d db redis-cache redis-queue configurator
docker compose -f compose.prod.yaml --profile setup run --rm create-site
docker compose -f compose.prod.yaml up -d
```

پورت وب فقط به loopback متصل است. برای دسترسی شبکه، reverse proxy داخلی با HTTPS و نام دامنه مصوب به آن وصل کنید. دیتابیس و Redis منتشر نمی‌شوند. ابتدا سه حوزه، تخصیص کاربر، نوشتن، گزارش، websocket و worker و scheduler را روی میزبان آزمایشی بررسی کنید. imageهای پایه برچسب version-16 دارند؛ قبل از تولید digest مصوب آن‌ها را ثبت و pin کنید. نسخه کد Frappe در Dockerfile روی v16.52.0 مشخص شده است.

## پشتیبان

در مثال‌ها نام سایت واقعی را به جای portal.example.internal بگذارید:

```bash
docker compose -f compose.prod.yaml exec backend bench --site portal.example.internal backup --with-files --compress
mkdir -p backups
docker compose -f compose.prod.yaml cp backend:/home/frappe/frappe-bench/sites/portal.example.internal/private/backups/. ./backups/
```

همچنین `site_config.json` سایت (شامل encryption_key)، تنظیمات محیط، نسخه image و کد را در فضای امن جدا پشتیبان بگیرید. فایل رمزها و کلید سایت محرمانه است و نباید وارد Git شود. پشتیبان پایگاه به تنهایی برای فایل‌ها و مقادیر رمزگذاری‌شده کافی نیست. نگهداری، رمزگذاری و کپی خارج از سرور را طبق سیاست شرکت تنظیم کنید.

## بازیابی روی محیط جدا

سایت خالی با نسخه همسان بسازید. فایل پشتیبان پایگاه و archiveهای public و private را داخل کانتینر backend کپی کنید. سپس:

```bash
docker compose -f compose.prod.yaml exec backend bench --site portal.example.internal restore /tmp/database.sql.gz --with-public-files /tmp/files.tar --with-private-files /tmp/private-files.tar
docker compose -f compose.prod.yaml exec backend bench --site portal.example.internal migrate
```

نام واقعی archiveها و فشرده‌سازی را با خروجی backup مطابقت دهید. encryption_key قبلی را در تنظیمات سایت بازیابی‌شده حفظ کنید. تعداد رکورد، ورود کاربران، فایل خصوصی، گزارش و شاخص‌ها را بررسی کنید. بازیابی واقعی در این نشست اجرا نشده است.

## ارتقا

۱. پشتیبان کامل بگیرید و بازیابی آن را روی محیط مستقل آزمایش کنید.
۲. نسخه جدید را ابتدا روی staging با داده آزمایشی و آزمون‌های پروژه بررسی کنید.
۳. نگهداری سایت و توقف worker/scheduler را برای بازه ارتقا هماهنگ کنید.
۴. image نسخه‌دار جدید بسازید، سرویس‌ها را متوقف و configurator را با image جدید اجرا کنید، سپس migrate و راه‌اندازی کنید.
۵. در شکست ارتقای schema، بازگرداندن image به تنهایی کافی نیست؛ پایگاه و فایل‌های پشتیبان پیش از ارتقا را بازیابی کنید.

هرگز `docker compose down -v` را برای نگهداری عادی اجرا نکنید؛ volumeهای پروژه را حذف می‌کند.
