# استقرار، ارتقا و بازیابی

## وضعیت بسته

محیط توسعه محلی اجرا و آزمون شده است. ساخت image تولید و بررسی آفلاین آن موفق شده است؛ اجرای انتها به انتهای compose.prod.yaml، HTTPS و TLS واقعی منابع هنوز تأیید نشده‌اند. پیش از استفاده واقعی روی یک میزبان آزمایشی مستقل بررسی شوند. نصب روی سرور شرکت انجام نشده است.

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

پورت وب فقط به loopback متصل است. برای دسترسی شبکه، reverse proxy داخلی با HTTPS و نام دامنه مصوب به آن وصل کنید. دیتابیس و Redis منتشر نمی‌شوند. ابتدا سه حوزه، تخصیص کاربر، نوشتن، گزارش، websocket و worker و scheduler را روی میزبان آزمایشی بررسی کنید. imageهای پایه و سرویس‌ها اکنون digest مشخص دارند؛ نسخه کد Frappe در Dockerfile روی v16.52.0 و commit متناظر بررسی می‌شود. راهنمای SECURE_CONFIGURATION_FA.md را برای TLS منابع، مسئول موجودی و constraints وابستگی‌ها بخوانید.

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

## بررسی همگام‌سازی خودکار پس از نصب یا جابه‌جایی سرور

اسکریپت `apps/saeenaria_portal/create-site.sh` در نصب اولیه زمان‌بند را فعال می‌کند و سرویس‌های worker و scheduler در Compose با `restart: unless-stopped` اجرا می‌شوند. فعال بودن زمان‌بند به تنهایی موفقیت دریافت از سپیدار را تضمین نمی‌کند؛ اتصال منابع و پردازش صف نیز باید بررسی شوند. همگام‌سازی کاتالوگ در hooks اپ هر ساعت ثبت شده است.

در انتقال سرور، علاوه بر دیتابیس و فایل‌ها، `.env`، `site_config.json` (به‌خصوص encryption_key و گزینه اتصال منابع) و فایل خصوصی `purchase-order-connections.json` را از پشتیبان امن بازیابی کنید. گواهی‌های اتصال، در صورت استفاده، باید در مسیر قابل دسترسی سرویس‌ها بازیابی شوند. رمزها را وارد Git نکنید. کپی مستقیم کد داخل کانتینر بخشی از image نیست؛ پیش از انتقال، image حاوی آخرین کد Git را بسازید یا همان image به‌روز را منتقل کنید.

در دستورهای زیر نام سایت واقعی را جایگزین کنید؛ نام سایت سرور فعلی `SaeenAria.Portal` است:

```bash
docker compose -f compose.prod.yaml exec backend bench --site SaeenAria.Portal migrate
docker compose -f compose.prod.yaml exec backend bench --site SaeenAria.Portal enable-scheduler
docker compose -f compose.prod.yaml up -d worker scheduler
docker compose -f compose.prod.yaml exec backend bench doctor
docker compose -f compose.prod.yaml exec backend bench --site SaeenAria.Portal execute saeenaria_portal.purchase_reports.product_catalog.sync_worker
```

اجرای مستقیم آخر، اتصال واقعی و دریافت کاتالوگ را بررسی می‌کند؛ نتیجه موفق شامل `added`، `source_items` و `conflicts` است. پس از آن زمان «آخرین همگام‌سازی» صفحه کالاها را در نوبت خودکار بعدی بررسی کنید. انتخاب فیلتر «کالاهای جدید سپیدار» فقط فهرست محلی را فیلتر می‌کند و دریافت تازه انجام نمی‌دهد. تکمیل گروه و مرجع کالاها همچنان دستی است.

در سرور فعلی، اتصال دیتابیس سپیدار بدون TLS انتخاب شده است و مقدار `purchase_order_require_tls` در `site_config.json` سایت باید بولین JSON یعنی `false` باشد، نه رشته `"false"`. این تنظیم مستقل از HTTPS وب‌سایت است. configurator مقدار پیش‌فرض مشترک را true می‌گذارد؛ تنظیم اختصاصی سایت را هنگام بازیابی حفظ کنید. اگر اتصال رمزنگاری‌شده لازم است، به‌جای این استثنا، TLS و CA معتبر منبع را طبق راهنمای SECURE_CONFIGURATION_FA.md تنظیم کنید.

وجود worker آنلاین یا خالی شدن صف، به تنهایی اثبات موفقیت کارها نیست. اگر تعداد کارها پیوسته زیاد می‌شود یا زمان همگام‌سازی تغییر نمی‌کند، خروجی این دستورات را بررسی کنید و صف را بدون تشخیص علت پاک نکنید:

```bash
docker compose -f compose.prod.yaml ps
docker compose -f compose.prod.yaml logs --tail=150 worker scheduler
```

## مراحل ارتقا

۱. پشتیبان کامل بگیرید و بازیابی آن را روی محیط مستقل آزمایش کنید.
۲. نسخه جدید را ابتدا روی staging با داده آزمایشی و آزمون‌های پروژه بررسی کنید.
۳. نگهداری سایت و توقف worker/scheduler را برای بازه ارتقا هماهنگ کنید.
۴. image نسخه‌دار جدید بسازید، سرویس‌ها را متوقف و configurator را با image جدید اجرا کنید، سپس migrate و راه‌اندازی کنید.
۵. در شکست ارتقای schema، بازگرداندن image به تنهایی کافی نیست؛ پایگاه و فایل‌های پشتیبان پیش از ارتقا را بازیابی کنید.

هرگز `docker compose down -v` را برای نگهداری عادی اجرا نکنید؛ volumeهای پروژه را حذف می‌کند.


## خرید مستقل از فایل تنظیمات اکسل — ۲۰۲۶-۱۰-۲۴

پس از پشتیبان دیتابیس، `bench --site SITE migrate` را اجرا و workerها و سرویس وب را با کد جدید راه‌اندازی کنید. ساختار `Portal Incoming Order` و hook پیش‌فرض تنظیمات با مهاجرت نصب می‌شوند. سیاست و کاتالوگ راه‌اندازی‌شده قبلی حفظ می‌شوند. در نصب تازه، مدیر سامانه کاتالوگ را با `product_catalog.initialize` از سپیدار راه‌اندازی و اطلاعات مرجع را در پورتال تکمیل می‌کند؛ تنظیمات جدید از پیش‌فرض داخلی ساخته می‌شوند.

اتصال خرید فقط SQL Server سپیدار را لازم دارد. اجرای `saeenaria_portal.purchase_reports.service.refresh_data` تمام هشت گزارش را از سپیدار و دیتابیس پورتال می‌سازد؛ snapshot موفق دارای `processor=portal-native-v2` است. پایش دوره‌ای نیز همین ورودی‌های محلی را استفاده می‌کند. هیچ فایل اکسل تنظیمات، جدول انتقال شیت، نمای رسوب بیرونی یا سرویس ETL برای این مسیر لازم نیست. اتصال MySQL گزارش‌های مستقل CRM را در صورت استفاده نگه دارید.

پیش از قطع نسخه قدیمی، مانده سفارش‌های در راه آن را یک بار بررسی و اگر خالی نیست در `/portal-purchase#incoming` ثبت کنید. در سایت توسعه بررسی‌شده، این منبع صفر ردیف داشت. پشتیبان snapshot قبل از تغییر در `private/native-purchase-backup-20261024-122442` و پشتیبان دیتابیس در `private/backups/20261024_122157-portal_localhost-database.sql.gz` نگهداری شد. هیچ اطلاعات تکمیلی کالا یا مقدار سیاست جاری در این تغییر بازنشانی نشد.

خاموش‌کردن سرویس بیرونی مشترک، پاک‌کردن فایل مرجع یا حذف جدول‌های قدیمی لازم نیست و برای مصرف‌کنندگان دیگر انجام نشده است. بازیابی نسخه قبل نیازمند کد و دیتابیس سازگار است؛ تغییر پرچم راه‌اندازی، fallback قدیمی ایجاد نمی‌کند.
