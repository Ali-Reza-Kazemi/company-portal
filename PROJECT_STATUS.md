# وضعیت پروژه

۲۰۲۶-۱۰-۱۴ — نسخه اولیه محلی 0.1.0

## انجام‌شده

- مخزن main و remote موجود بررسی شدند؛ محیط محدود D را نمی‌بیند و کار پروژه با دسترسی تأییدشده خارج از sandbox اجرا شد.
- Docker Desktop راه‌اندازی و سرویس‌های مستقل saeenaria-portal-dev ساخته شدند.
- Frappe 16.52.0 و اپ saeenaria_portal 0.1.0 نصب و اجرا شدند؛ ERPNext نصب نشده است.
- MariaDB 11.8 و دو Redis، network و volume مستقل؛ وب loopback:8085 و websocket loopback:19085.
- .env با رمز تصادفی ساخته و نادیده‌گرفتن آن با git check-ignore بررسی شد.
- ۱۱ DocType اختصاصی، سه حوزه، ۳۲ شناسنامه شاخص، ۲۷ قالب غیرفعال و پنج سیاست تجاری بدون مقدار ثبت شدند.
- مسیر اقدام تا گزارش، KPI جدا، درخواست تصمیم، گردش و قفل گزارش، CSV دو مرحله‌ای و برنامه کاری پیاده شد.
- رابط اولیه فارسی RTL و ورود شمسی اقدام، خروجی چاپ و CSV اقدامات آماده است.
- Dockerfile و Compose مستقل تولید، preflight و راهنماهای فارسی نوشته شدند؛ روی سرور شرکت اقدامی انجام نشده است.

## نتیجه بررسی

- Compose توسعه و تولید: config --quiet موفق (نام سایت نمونه فقط برای بررسی تولید).
- تبدیل شمسی ۱۴۰۵/۰۷/۲۲ و ۱۴۰۳/۱۲/۳۰ و رد ۱۴۰۴/۱۲/۳۰: موفق.
- دسترسی فهرست، خواندن، نوشتن بین حوزه‌ها و جلوگیری از انتقال؛ ویرایش حوزه مجاز: موفق.
- تقسیم بر صفر، ناموجود در برابر صفر، هدف نامشخص، قفل گزارش تأییدشده: موفق.
- تعطیلات و پنجشنبه/جمعه و تولید بدون تکرار: موفق.
- پیش‌نمایش CSV بدون ذخیره، ثبت و رد تکرار: موفق.
- ورود واقعی HTTP، سه حوزه، جداسازی آزمایشی، صفحه ورود CSV و asset تقویم: موفق.
- پس از restart کانتینر دیتابیس و Bench، همان سایت و ۳۲ شاخص و ۲۷ قالب در دسترس بودند.
- آزمون‌ها rollback دارند؛ داده عملکردی واقعی یا آزمایشی بدون درخواست ایجاد نشده است.

## محدودیت و قدم بعدی

فهرست کامل در docs/LIMITATIONS.fa.md است. اولویت بعد: بررسی تصویری با ورود در مرورگر، تکمیل فرم‌های تخصصی و شمسی Desk، اتصال محاسبات به ورودی‌های واقعی و آزمون image تولید و بازیابی روی staging. استقرار شرکت پس از دسترسی و preflight واقعی انجام می‌شود. هیچ رمز در این فایل نیست.

## به‌روزرسانی فونت
- وزیرمتن v33.003 با فایل WOFF2 محلی و مجوز OFL اضافه شد؛ روی صفحات پورتال و CSS میزکار و وب اعمال شد.
- مرورگر بارگذاری فونت را تأیید کرد. فایل فونت HTTP 200 دارد.
- خطای قبلی loadMetrics تعریف‌نشده هنگام بررسی صفحه مشاهده و تابع بارگذاری شاخص و مدیریت اضافه شد.

## تغییر نام فنی
- نام اپ، پکیج، پوشه‌ها، ماژول و ارجاع‌ها به saeenaria_portal تغییر کرد.
- پروژه Docker، کانتینرها، شبکه و volumeها به پیشوند saeenaria منتقل شدند.
- پیش از انتقال پشتیبان کامل سایت گرفته شد؛ داده‌های سه حوزه، ۳۲ شاخص و ۲۷ قالب حفظ شدند.
- آزمون‌های دسترسی، قواعد، تقویم، CSV و HTTP با نام جدید موفق بودند.
- تاریخچه Git و پشتیبان تاریخی برای حفظ قابلیت بازیابی بازنویسی نمی‌شوند.

## آماده‌سازی کاربران
- سه حساب معرفی‌شده توسط کاربر ایجاد و ورود HTTP هر سه بررسی شد؛ ایمیلی ارسال نشده است.
- یک مدیر شرکت و دو مسئول حوزه ثبت شدند؛ مسئول موجودی و فناوری اطلاعات یک حساب مشترک دارد.
- سه تخصیص فعال حوزه و ۲۷ قالب دارای مسئول ثبت شد؛ قالب‌ها همچنان غیرفعال‌اند.
- بررسی مشاهده و نوشتن حوزه‌ها برای حساب‌های واقعی موفق بود.
- یک اقدام با برچسب آزمایشی در حوزه فناوری اطلاعات برای آموزش ساخته شد؛ داده واقعی عملکردی وارد نشده است.
- فایل تحویل رمزهای اولیه فقط در مسیر محلی نادیده‌گرفته‌شده Git نگهداری می‌شود؛ هیچ رمزی در این سند نیست.

## فعال‌سازی هفتگی توسط کاربر
- کاربر هر ۱۵ قالب هفتگی سه حوزه را فعال کرد؛ هر حوزه پنج قالب فعال دارد و ماهانه‌ها غیرفعال‌اند.
- ۱۵ اقدام واقعی هفته ۲۰۲۶-۱۰-۱۷ تا ۲۰۲۶-۱۰-۲۱ از قالب‌ها ساخته شد؛ پنج اقدام برای هر حوزه.
- نبود موعد پنجشنبه/جمعه و عدم تولید تکراری بررسی شد.

## ساده‌سازی ثبت پیشرفت و تصمیم نبود هدف
- دکمه «ثبت پیشرفت» کنار اقدام در پورتال، فرم همان صفحه و نمایش پیش‌فرض کارهای مسئول اضافه شد.
- API این مسیر فقط به مسئول خود اقدام یا مدیر سامانه اجازه به‌روزرسانی پیشرفت می‌دهد؛ خواندن/نوشتن حوزه نیز در سرور کنترل می‌شود.
- زمان ثبت تکمیل، هویت ثبت‌کننده و موعد در زمان تکمیل در سرور نگهداری می‌شوند؛ ویرایش توضیح پس از تکمیل زمان اولیه را تغییر نمی‌دهد. بازکردن دوباره کار زمان فعلی را پاک می‌کند؛ تاریخچه تغییرات باقی است.
- وضعیت انجام در موعد/تأخیر مستقل از ارزیابی شاخص‌ها نمایش داده می‌شود؛ برای سوابق فاقد زمان تکمیل، زمان تخمین زده نمی‌شود.
- طبق تصمیم صریح کاربر، فعلاً هیچ هدف عددی فعال نیست و هدف اولیه دسترس‌پذیری نیز برداشته شد.
- بررسی ثبت پیشرفت مسئول، رد مسئول دیگر/حوزه دیگر، تکمیل بدون نتیجه، کنترل تغییر هم‌زمان، زمان سرور و وضعیت موعد موفق بود؛ آزمون‌ها rollback شدند.
- دکمه و بازشدن فرم در مرورگر بررسی شد؛ هنگام بررسی UI هیچ پیشرفتی در کار واقعی ذخیره نشد.

## نمایش نام فارسی شاخص
- title_field و show_title_field_in_link برای Portal Metric و Portal Domain تنظیم شدند؛ شناسه‌ها و سوابق تغییر نکردند.
- جست‌وجوی شاخص با عنوان فارسی فعال است و انتخاب شاخص در فرم مقدار به حوزه انتخاب‌شده محدود می‌شود.
- پاسخ جست‌وجوی حساب علیرضا برای «تیکت» شامل نام چهار شاخص مرتبط بود؛ هر ۳۲ شناسنامه حفظ شد.

## تفکیک اختیار تعریف شاخص از ثبت مقدار
- تعریف و ویرایش شناسنامه، فرمول و آستانه شاخص فقط برای مدیر شرکت و مدیر سامانه مجاز است؛ مسئول و همکار شناسنامه را فقط می‌خوانند.
- مقدار واقعی شاخص در حوزه مجاز همچنان توسط مسئول ثبت می‌شود؛ هدف و پرچم هدف در سطح مجوز فیلد حفاظت شدند.
- اعتبارسنجی سرور و واردکننده CSV تغییر هدف توسط غیرمدیر را کنترل می‌کنند؛ برای رکورد موجود، کارمند هویت شاخص/دوره را تغییر نمی‌دهد.
- آزمون حساب علیرضا، مسئول بازاریابی و مدیر شرکت برای مجوزها و CSV موفق بود؛ داده‌های آزمون rollback شدند.

## تقویم شمسی فرم‌های پورتال
- همه فیلدهای Date و Datetime فرم‌های اختصاصی با انتخابگر مشترک شمسی نمایش و وارد می‌شوند؛ نام ماه فارسی، هفته از شنبه و ورود دستی ارقام فارسی/انگلیسی پشتیبانی می‌شود.
- بخش ساعت فیلدهای تاریخ‌وساعت جدا و با زمان تهران نمایش داده می‌شود؛ فیلدهای فقط‌خواندنی قابل ویرایش نشده‌اند.
- فیلدهای اصلی Date/Datetime و قواعد سمت سرور حفظ شدند؛ تاریخ نمایش شمسی است و مقدار ذخیره‌شده ISO باقی می‌ماند.
- فرم مستقل آزمایشی در مرورگر باز و انتخاب ۲۲ مهر ۱۴۰۵ بررسی شد؛ اطلاعاتی در رکورد واقعی ذخیره نشد.
- تبدیل رفت‌وبرگشت، کبیسه و رد روز نامعتبر و پوشش metadata تمام تاریخ‌های اپ بررسی شد.

## تقویم یکپارچه و بازطراحی
- کنترل‌های استاندارد Date، Datetime و DateRange در میزکار Frappe به تقویم شمسی مشترک وصل شدند؛ فیلترها، فرم‌های عمومی و قالب‌بندی تاریخ فهرست‌ها نیز از آن استفاده می‌کنند.
- فیلدهای HTML تاریخ قبلی حذف شدند و عرض ورودی استاندارد برگشت؛ در بررسی مرورگر عرض تاریخ و فیلد منبع هر دو ۴۲۰ پیکسل بود.
- پنجره ۳۹۰ پیکسلی با انتخابگر سال و ماه در سربرگ، شبکه روزها، نشان امروز و رنگ تعطیلات طراحی شد. در موبایل عرض پنجره با صفحه تطبیق دارد.
- پنجشنبه و جمعه تعطیل کاری نشان داده می‌شوند؛ تعطیلات Portal Holiday با عنوان از API داخلی خوانده می‌شوند. برای حفظ امکان ثبت تاریخ رویداد، تعطیلات در انتخاب دستی غیرفعال نشده‌اند؛ برنامه خودکار همچنان موعد کاری را کنترل می‌کند.
- تعطیلات رسمی نامشخص حدس زده نمی‌شوند؛ مدیر سامانه باید آن‌ها را در Portal Holiday ثبت کند.
- کنترل‌های تاریخ، زمان و بازه، ارقام فارسی، ورود ISO داخلی، محدوده معکوس، ساعت نامعتبر و کبیسه آزموده شدند؛ مجوزهای شاخص کارکنان حفظ شد.
- الهام چیدمان انتخاب ماه/سال: https://github.com/babakhani/pwt.datepicker و https://github.com/behzadi/persianDatepicker ؛ بسته یا کد این کتابخانه‌ها اضافه نشده است.
- بررسی واقعی انتخاب تاریخ و تاریخ‌وساعت در فرم مرورگر موفق بود؛ مشکل قالب داخلی روز-ماه-سال Frappe اصلاح شد و برای آن بررسی سازگاری اضافه شد.

## ریز گزارش قابل فهم
- JSON تصویر شاخص‌ها در فرم Portal Report پنهان و نمای HTML فارسی فقط‌خواندنی اضافه شد.
- نمای گزارش شامل وضعیت گردش، واقعی/آزمایشی، دوره شمسی، نام شاخص، مقدار واقعی، واحد، اعتبار داده، هدف، تغییر دوره، ارزیابی و منبع و زمان به‌روزرسانی است.
- نبود هدف و داده مستقل نمایش داده می‌شوند؛ اطلاعات با text() درج می‌شود تا محتوای متنی منبع به HTML اجرایی تبدیل نشود.
- گزارش آموزشی موجود در مرورگر با مقدار ۳ تیکت حل‌شده بررسی شد؛ hash تصویر ثبت‌شده قبل و بعد یکسان بود و هیچ محتوای گزارش تغییر نکرد.

## ترجمه گردش گزارش
- هر چهار مرحله Draft، Submitted، Needs Revision و Approved با فایل ترجمه فارسی اپ کامل شدند؛ مقادیر فنی و گردش ذخیره‌شده تغییر نکردند.
- خروجی ترجمه فارسی برای چهار مرحله بررسی و کش سایت پاک شد.

## خوانایی گزارش و تصمیم در صفحه مسئول
- متن‌های پیوسته بخش مدیریت به دو ستون مجزا و کارت‌های مستقل گزارش/درخواست تصمیم تبدیل شدند.
- عنوان، وضعیت فارسی، حوزه و برچسب آزمایشی جداست؛ دستاورد، مانع، برنامه بعد، شرح درخواست و پاسخ برچسب مستقل دارند.
- نظر/پاسخ مدیر در کادر متمایز و تاریخ‌ها به شمسی نمایش داده می‌شوند؛ لینک جزئیات هر مورد اضافه شد.
- چیدمان در عرض کم تک‌ستونه است و درج متن با textContent از اجرای HTML جلوگیری می‌کند.
- گزارش و تصمیم آموزشی موجود در مرورگر بررسی شدند؛ دسترسی حساب علیرضا و عدم دسترسی مسئول بازاریابی به گزارش IT تأیید شد. هیچ داده گزارش یا تصمیم تغییر نکرد.

## انتخاب مسئول اقدام بر اساس حوزه
- فیلد ایمیل دستی پورتال به انتخابگر نام کاربران فعال تخصیص‌یافته به حوزه تبدیل شد؛ با تغییر حوزه، مسئول قبلی پاک و فهرست تازه دریافت می‌شود.
- دریافت فهرست با مجوز خواندن حوزه کنترل می‌شود؛ کاربران غیرفعال و تخصیص‌های غیرفعال نمایش داده نمی‌شوند.
- مدیر شرکت می‌تواند اقدام جدید به مسئول حوزه محول کند؛ مجوز ویرایش اقدامات موجود تغییر نکرد.
- ثبت آزمایشی با حساب مدیر و انتخاب علیرضا موفق بود؛ منع مشاهده کاربران IT برای مسئول بازاریابی تأیید شد. داده آزمون rollback شد و بررسی نحو JavaScript موفق بود.

## بازخورد ثبت اقدام و تقویم صفحه پورتال
- پیام در حال ثبت، موفقیت شامل عنوان/مسئول/شناسه/موعد و خطای ثبت کنار دکمه اقدام نمایش داده می‌شود؛ دکمه تا پایان درخواست غیرفعال است و عنوان پس از موفقیت پاک می‌شود.
- چهار ورودی شروع، موعد، از موعد و تا موعد به انتخابگر شمسی با ظاهر مشترک تقویم، انتخاب ماه/سال و تعطیلات متصل شدند؛ ورود دستی و عرض استاندارد حفظ شد.
- بازه معکوس در فرم و فیلتر پیش از درخواست کنترل و خطا در همان بخش نمایش داده می‌شود.
- انتخاب روز در فیلتر و تقویم موعد در مرورگر بررسی شد؛ پیام خطای بازه معکوس فرم بدون ثبت داده تأیید شد. نحو اسکریپت‌ها بررسی شد.

## مدیر واحد، منابع انسانی و سربرگ پورتال
- نقش مدیر واحد به‌صورت پرچم is_manager در عضویت هر حوزه اضافه شد؛ واگذاری کار توسط مدیر همان حوزه یا مدیر شرکت مجاز است. کارمند فقط برای خود اقدام ثبت می‌کند و امکان تغییر کار دیگران ندارد.
- بخش اعضا و نقش واحد برای مدیر شرکت/سامانه و Portal HR Manager اضافه شد؛ تغییر با زمان آخرین ویرایش کنترل و سابقه عضویت ثبت می‌شود. اعطای منابع انسانی فقط توسط مدیر شرکت/سامانه انجام می‌شود.
- هیچ فردی طبق انتخاب کاربر مدیر واحد یا منابع انسانی نشده است. تمام تغییرات افراد در آزمون rollback شدند.
- نام حساب، نقش، خروج POST با CSRF و لینک‌های دسترسی سریع به سربرگ اضافه شد؛ راهنمای داخل صفحه و docs/UNIT_ROLES_FA.md فراهم شد.
- آزمون واگذاری مدیر در حوزه خود، منع واگذاری کارمند و حوزه دیگر، مدیریت نقش توسط مدیر و منابع انسانی و منع ارتقای دسترسی توسط مدیر واحد/منابع انسانی موفق بود. ظاهر فرم و جدول عضویت در مرورگر بررسی شد.

## هویت بصری شرکت
- لوگوی رسمی کاربر بدون تغییر فایل به public/images/saeenaria-logo.webp اضافه و با پس‌زمینه سفید در سربرگ پورتال و صفحه ورود CSV استفاده شد.
- تم آبی #01148b و قرمز #ed2428 بر اساس رنگ‌های فایل لوگو، برای سربرگ، لینک‌ها، دکمه‌ها، جداول، کارت پاسخ مدیریت و انتخابگر شمسی هماهنگ شد. رنگ‌های معنایی موفقیت و خطا حفظ شدند.
- استایل مشترک branding.css به وب و میزکار اضافه شد؛ نسخه موبایل سربرگ در مرورگر بررسی شد و لوگو با نسبت اصلی نمایش داده می‌شود.

## مرتب‌سازی پورتال با تب‌ها
- بخش‌های کارها، ثبت و واگذاری، شاخص‌ها، گزارش‌ها و تصمیم‌ها و اعضا به تب‌های مستقل تبدیل شدند؛ فقط پنل انتخاب‌شده نمایش داده می‌شود.
- فیلتر مشترک حوزه/بازه/نوع داده در بخش جمع‌شونده برای تب‌های گزارش قرار گرفت؛ خروجی و چاپ کنار کارها باقی ماند.
- لینک مستقیم هر تب، تاریخچه مرورگر، حرکت صفحه‌کلید و حفظ فرم هنگام تعویض تب پشتیبانی می‌شوند. تب اعضا همچنان فقط از HTML مجاز سمت سرور ساخته می‌شود.
- نمایش تک‌پنل، جابه‌جایی تب و حفظ مقدار آزمایشی فرم در مرورگر بررسی شد؛ مقدار آزمایشی پاک شد و رکوردی ذخیره نشد.

## هویت بصری صفحه ورود
- لوگوی رسمی در Website Settings و hook برنامه تنظیم شد؛ قالب استاندارد ورود Frappe حفظ شد.
- CSS محدود به data-path=login، زمینه روشن آبی، فرم سفید، دکمه آبی و خط قرمز هویت شرکت را اعمال می‌کند؛ عنوان و توضیح فارسی اضافه شدند.
- دریافت مستقل صفحه مهمان، وجود ورودی‌های ورود و بارگیری موفق لوگو/CSS/JS و نحو JavaScript بررسی شد. نشست فعلی کاربر بسته نشد.

## فارسی‌سازی متن‌های ورود
- برچسب نام کاربری/ایمیل، رمز، دکمه ورود، بازیابی رمز، ورود ایمیلی، ثبت‌نام و پیام‌های اعتبارسنجی/تأیید هویت در صفحه ورود فارسی شدند.
- ترجمه محدود به متن رابط و ویژگی‌های توضیحی است؛ مقدار ورودی نام کاربری، ایمیل و رمز دست‌نخورده است. جهت صفحه فارسی و ورودی حساب همچنان چپ‌به‌راست است.
- تغییرات پیام‌های پویا نیز ترجمه می‌شوند؛ نحو JavaScript بررسی و کش وب پاک شد.

## میزکار مدیریت کاربردی
- لینک سربرگ برای کارکنان عادی حذف و برای مدیران/منابع انسانی به /portal-admin متصل شد.
- صفحه مدیریتی فارسی با میانبرهای کارها، برنامه‌ها، گزارش، تصمیم، شاخص و اعضا ساخته شد؛ گروه تنظیمات فقط برای مدیر سامانه است و میانبرها مجوز خواندن همان DocType را بررسی می‌کنند.
- مسیر صفحه با کنترل سمت سرور از دسترسی مستقیم کارمند محافظت می‌شود؛ نقش‌های موجود تغییر نکردند.
- منع دسترسی حساب کارمند آزمایشی، نمایش گروه‌های مدیر شرکت/سامانه و چیدمان واقعی صفحه در مرورگر بررسی شد. حساب آزمایشی rollback شد.

## فارسی‌سازی منوهای میزکار پورتال
- عنوان برنامه، نام نمایشی هر ۱۱ نوع سند، منوی کناری و وضعیت‌های رایج در ترجمه فارسی اپ تکمیل شدند.
- برای برچسب‌های ترجمه‌نشده پوسته جدید Frappe، لایه نمایشی فارسی با حفظ مسیرها، شناسه‌ها و مقادیر فرم اضافه شد.
- عنوان و تمام منوهای کناری صفحه مقادیر شاخص‌ها پس از تازه‌سازی در مرورگر فارسی مشاهده شدند؛ نحو اسکریپت بررسی شد.

## قواعد فارسی و تعطیلات رسمی خودکار
- title_field/search_fields قواعد و تعطیلات تنظیم شد و ستون شناسه فنی در تنظیمات فهرست مخفی شد؛ عنوان فارسی قواعد در مرورگر تأیید شد. شناسه‌ها و روابط پایگاه داده تغییر نکردند.
- دریافت مستقیم تقویم سالانه جاری از https://www.time.ir/event-year پیاده شد؛ قالب ۱۲ ماه، تعداد روزها، سال، تبدیل شمسی/میلادی، تعطیلات ثابت و تعداد منطقی تعطیلات پیش از ذخیره اعتبارسنجی می‌شوند. تاریخ قمری محاسباتی حدس زده نمی‌شود.
- ۲۶ تاریخ تعطیل رسمی ۱۴۰۵ ثبت شد. تکرار دریافت ۲۶ مورد بدون تغییر و صفر مورد تازه داشت؛ ویرایش دستی حفظ شد و پاسخ نامعتبر داده قبلی را تغییر نداد.
- فعال‌بودن و منبع/سال/عنوان دریافتی برای تعطیلات ثبت می‌شود؛ حذف تعطیلی از منبع فقط مورد واردشده و ویرایش‌نشده همان سال را غیرفعال می‌کند. رکوردهای دستی حفظ می‌شوند.
- صفحه /portal-holidays برای مدیر شرکت/سامانه با آخرین دریافت و دکمه به‌روزرسانی دستی ساخته شد و در میزکار مدیریت لینک دارد. اجرای واقعی دکمه در مرورگر موفق بود.
- job روزانه قبل از تولید اقدامات قرار گرفت؛ در آغاز سال، دریافت سال تازه تلاش می‌شود و در طول سال بررسی هفتگی انجام می‌شود. اگر منبع سال تازه منتشر نکرده یا ساختارش عوض شده باشد، به‌روزرسانی متوقف و خطا ثبت می‌شود؛ داده سال تازه جعل نمی‌شود. زمان‌بند سایت فعال است؛ روشن‌بودن Docker، worker و اینترنت لازم است.
- تقویم و برنامه‌ساز فقط تعطیلات فعال را لحاظ می‌کنند؛ پنجشنبه/جمعه همچنان مستقل لحاظ می‌شوند. اقدامات قبلی بازنویسی نشدند.

## انتخاب روز هفته با نام
- فیلد عددی weekday در فرم برنامه پنهان و انتخابگر فارسی شنبه تا جمعه برای تناوب هفتگی اضافه شد؛ نگاشت عددی داخلی و برنامه‌های قبلی حفظ شدند.
- روز ماه فقط برای تناوب ماهانه/فصلی دیده می‌شود؛ سرور مقدار روز هفته نامعتبر را رد می‌کند.
- فرم جدید و نمایش هفت گزینه پس از انتخاب تناوب هفتگی در مرورگر تأیید شد؛ رکوردی ذخیره نشد.

## انتخاب مسئول برنامه با فیلتر حوزه و استثنای بین‌واحدی
- جست‌وجوی مسئول برنامه به کاربران فعال همان حوزه محدود شد؛ مدیر مجاز می‌تواند با دکمه «نمایش همه کارکنان» اعضای فعال سایر حوزه‌ها را جست‌وجو و با دکمه برگشت دوباره محدود کند.
- تغییر حوزه یا دامنه جست‌وجو مسئول قبلی را پاک می‌کند. انتخاب استثنا در برنامه ثبت و سمت سرور اعتبارسنجی می‌شود؛ واگذاری به دیگران فقط برای مدیر حوزه/سامانه/شرکت است.
- کار تولیدشده از برنامه بین‌واحدی فقط برای مسئول آن قابل مشاهده و ثبت پیشرفت است؛ عضویت عمومی حوزه اعطا نمی‌شود و گزارش‌ها و شاخص‌های حوزه همچنان محدودند. کارمند بین‌واحدی نمی‌تواند هویت، مسئول و موعد کار را تغییر دهد.
- فیلتر محدود/گسترده، تولید کار بین‌واحدی، ثبت پیشرفت مسئول و منع تغییر موعد/دسترسی گزارش حوزه با داده موقت بررسی و rollback شد. هر دو دکمه در فرم مرورگر تأیید شدند؛ برنامه‌ای ذخیره نشد.

## همه کاربران و چک‌باکس انتخاب مسئول برنامه
- علت نبودن چنارانی و حسنپور، محدودیت حالت گسترده به کاربران دارای عضویت حوزه بود؛ هر دو حساب فعال اما بدون عضویت حوزه هستند.
- حالت گسترده اکنون تمام حساب‌های فعال System User را نمایش می‌دهد؛ Guest و حساب سیستمی Administrator حذف می‌مانند. عضویت حوزه جدیدی به کسی اعطا نشد.
- دکمه به چک‌باکس «نمایش همه کاربران فعال» تبدیل شد. انتخاب عادی همچنان محدود به اعضای حوزه است.
- اعتبارسنجی برنامه امکان انتخاب حساب فعال بدون حوزه در حالت استثنا را می‌دهد. مدیر شرکت برای ثبت پیشرفت کار خودش مجوز نوشتن پایه دارد؛ کنترل رکورد همچنان تغییر کار سایر افراد را منع می‌کند.
- انتخاب هر دو حساب، ساخت موقت برنامه/کار و ثبت پیشرفت توسط خودشان آزمایش و rollback شد؛ چک‌باکس در مرورگر تأیید شد.

## نام مسئول در فهرست کشویی برنامه
- فیلد لینک ایمیلی مسئول در فرم برنامه پنهان و انتخابگر کشویی نام کاربران جایگزین شد؛ مقدار مرجع User در پایگاه داده حفظ شده است.
- فیلتر حوزه و چک‌باکس همه کاربران اعمال می‌شوند؛ نام مسئول قبلی خارج از فهرست نیز برای مشاهده سابقه حفظ می‌شود.
- عرض و ارتفاع با تناوب هماهنگ است؛ پاسخ‌های قدیمی درخواست هنگام تغییر حوزه نادیده گرفته می‌شوند.
- فرم s3miheis2r در مرورگر بررسی شد و گزینه انتخاب‌شده «علیرضا کاظمی» به‌جای ایمیل نمایش داده شد؛ رکورد تغییر نکرد.

## شرح اقدام و خروجی مورد انتظار
- فیلد Text شرح به Portal Action و Portal Template اضافه شد؛ API ثبت، داشبورد و ورود/خروج CSV آن را پشتیبانی می‌کنند.
- برنامه‌ساز شرح را هنگام ایجاد هر اقدام کپی می‌کند؛ تغییرات بعدی برنامه شرح کارهای ساخته‌شده را بازنویسی نمی‌کند.
- در پورتال، شرح در فرم ثبت، جزئیات بازشونده هر ردیف و پنجره ثبت پیشرفت نمایش داده می‌شود؛ درج نمایشی با textContent است.
- برای رکوردهای قبلی بدون شرح، پیام نبود شرح نمایش داده می‌شود و داده حدسی تولید نشد. انتخاب شد شرح فعلاً اختیاری باشد تا سوابق و واردکننده‌های قبلی قابل استفاده بمانند.
- ذخیره دستی، خروجی داشبورد، انتقال شرح از برنامه و ثبات شرح کار قبلی با تغییر برنامه بررسی و rollback شد. فیلد در فرم واقعی برنامه مشاهده شد.

## فهرست برنامه‌ها و انتقال گروهی وظایف
- فهرست برنامه‌ها با ستون عنوان اقدام به جای شناسه، نام مسئول، خلاصه ۱۲کلمه‌ای شرح و حوزه تنظیم شد. نام و خلاصه برای رکوردهای قبلی بدون تغییر زمان ویرایش پر شدند؛ شرح خالی جعل نشد.
- صفحه /portal-reassign با انتخاب مبدأ/مقصد/حوزه، اجازه بین‌واحدی، پیش‌نمایش و انتخاب مستقل ردیف‌ها اضافه و در میزکار مدیریت و منوی فهرست برنامه‌ها لینک شد.
- برنامه‌ها و کارهای باز منتقل می‌شوند؛ تکمیل‌شده/لغوشده از پیش‌نمایش حذف‌اند. موعد، پیشرفت، نتیجه و شرح تغییر نمی‌کند و Version با حساب عامل ثبت می‌شود.
- انتقال در تراکنش با قفل ردیف‌ها و اثرانگشت پیش‌نمایش اجرا می‌شود؛ تغییر رکوردها پس از پیش‌نمایش، انتقال را رد می‌کند. مدیر واحد محدود به حوزه خود و مدیر شرکت/سامانه/منابع انسانی مجازند.
- آزمون انتقال انتخابی برنامه/کار، حفظ موعد و پیشرفت و تکمیل‌شده، ثبت تاریخچه و رد پیش‌نمایش قدیمی موفق و rollback شد. ستون‌ها و پیش‌نمایش ۳۱ وظیفه واقعی در مرورگر فقط مشاهده شدند؛ هیچ وظیفه واقعی منتقل نشد.
- راهنما: docs/REASSIGNMENT_FA.md

## راهنمای محیط‌ها و ناوبری مشترک
- سه محیط پورتال روزانه، فرم‌ها و فهرست‌های داده و ساخت فنی Frappe توضیح داده شدند؛ /portal-guide راهنمای فارسی داخل سامانه است.
- منوی جمع‌شونده «جابه‌جایی محیط» در پورتال، صفحات جانبی و میزکار Frappe اضافه شد. مسیر فعلی مشخص و لینک‌ها از API متناسب با نقش برگردانده می‌شوند.
- کارکنان فقط پورتال/راهنما، مدیران فرم‌ها و میزکار مدیریت و مدیر سامانه لینک ساخت فنی را دارند؛ مجوز داده یا نقش‌ها تغییر نکرد.
- منو در /desk/build و رفتن به راهنما در مرورگر تأیید شد. خروجی نقش‌های کارمند، مدیر شرکت و مدیر سامانه بررسی و حساب آزمایشی rollback شد.
- بنا بر درخواست کاربر، منوی جابه‌جایی محیط برای کارکنان عادی حذف شد؛ API برای آنان فهرست خالی می‌دهد و دکمه ساخته نمی‌شود. نمایش برای مدیران/منابع انسانی حفظ و بررسی شد.

## سه دسته کارها و پیشرفت
- دسته‌های شروع‌نشده (Open)، در دست اقدام (In Progress/Blocked) و پایان‌یافته (Completed/Cancelled) با تعداد هر دسته اضافه شدند؛ وضعیت لغوشده مشخص باقی می‌ماند.
- با تغییر وضعیت و دریافت دوباره، کار خودکار در دسته درست قرار می‌گیرد. حالت خالی، نمایش موبایل و خروجی CSV دسته انتخاب‌شده لحاظ شدند.
- شمارش ۱۳ شروع‌نشده، ۱ در دست اقدام و ۱ پایان‌یافته و جابه‌جایی دسته‌ها در مرورگر بررسی شد؛ داده کارها تغییر نکرد.

## نمایش نام کاربران به‌جای ایمیل
- نمایش عنوان کامل User برای فیلدهای لینک استاندارد میزکار با Property Setter فعال شد؛ شناسه User، ایمیل ورود و روابط سوابق دست‌نخورده‌اند.
- API کارها نام مسئول و ثبت‌کننده تکمیل را کنار شناسه برمی‌گرداند؛ جدول پورتال و خروجی خواندنی CSV نام مسئول را نشان می‌دهند. پاسخ تصمیم نیز نام پاسخ‌دهنده دارد.
- فهرست مدیریت اعضا نام کاربران غیرفعال را هم برای سوابق نگه می‌دارد؛ انتخابگرها فقط فعال‌ها را نشان می‌دهند. fallback نمایشی ایمیل از انتخابگرها حذف شد.
- داده API، عنوان لینک User و نمایش نام علیرضا کاظمی/رابعه خانبابایی در جدول واقعی مرورگر بررسی شدند. برای خارج‌کردن قالب قدیمی از حافظه، سرویس bench راه‌اندازی مجدد شد.

## واگذاری بین‌واحدی در فرم ثبت اقدام پورتال
- چک‌باکس «نمایش همه کاربران فعال، از جمله سایر حوزه‌ها» به ثبت اقدام اضافه شد و فقط برای مدیر مجاز حوزه نمایش داده می‌شود؛ تغییر حوزه آن را خاموش و مسئول را پاک می‌کند.
- اجازه بین‌واحدی در رکورد اقدام ثبت و سمت سرور کنترل می‌شود؛ کارمند عادی نمی‌تواند آن را فعال کند. مسئول خارجی فقط همان کار را می‌بیند و پیشرفت ثبت می‌کند.
- آزمون ثبت دستی به حسنپور، ثبت پیشرفت توسط ایشان و منع انتخاب گسترده/واگذاری توسط کارمند عادی موفق و rollback شد. در مرورگر چک‌باکس و فهرست هر چهار کاربر مشاهده شد؛ کار واقعی ثبت نشد.

- تمام ۱۸ گزینه نوع ورودی Portal Record به فایل ترجمه فارسی و لایه نمایش میزکار اضافه شدند؛ مقادیر ذخیره‌شده و شروط محاسبات تغییر نکردند. پوشش گزینه‌های metadata و نحو اسکریپت بررسی شد.

## مدیریت حساب شخصی
- نام/آیکون حساب در سربرگ پورتال به لینک قابل‌کلیک /portal-account تبدیل و متن مدیریت حساب اضافه شد؛ برای کارکنان و مدیران یکسان در دسترس است.
- صفحه شخصی شامل نام، نام خانوادگی، همراه، شناسه ورود فقط‌خواندنی، حوزه‌های عضویت، تغییر رمز استاندارد Frappe و مدیریت برنامه‌های متصل است.
- API ویرایش فقط User نشست جاری را تغییر می‌دهد؛ شناسه کاربر، ایمیل، نقش، فعال‌بودن و مجوزها از ورودی پذیرفته نمی‌شوند. نام مسئول در فهرست برنامه‌ها نیز پس از تغییر نام تازه می‌شود.
- مسیر تغییر رمز /update-password با دریافت رمز فعلی از کاربر و سازوکار استاندارد Frappe حفظ شد؛ تم و بازگشت به حساب اضافه شد. هیچ رمز عبوری توسط عامل وارد یا تغییر داده نشد.
- آزمون ویرایش پروفایل خود، حفظ ایمیل/نقش و منع مهمان موفق و rollback شد. لینک سربرگ، صفحه حساب و فرم استاندارد رمز در مرورگر بررسی شدند.

## 2026-10-16 — Administrative password reset
Added account management and admin hub entry for System/Portal administrators and HR to email native Frappe password reset links. Server enforces active users, excludes self and Administrator, and restricts HR from privileged accounts. POST rate limit, outgoing email prerequisite and audit comment included. Verified with mocked mail and transaction rollback, HR scope and Guest denial, JS syntax and template render; no real email sent or password changed.

## 2026-10-16 — Manual password reset link delivery
Account reset form now offers generate/copy link alongside email delivery; same server permissions and rate limit apply. Native Frappe token generated without email; token omitted from audit, cleared on user selection/page exit. Tested generation with mail forbidden and transaction rollback plus HR/Guest denial and JS syntax. No persistent real credential changes.

## 2026-10-16 — Practical training and sample data
Added /portal-training with twelve Persian lessons, complete task-to-decision scenario, live permission-scoped educational bar charts and employee counts. Linked from guide/admin hub. Explicit idempotent training.seed created 12 demo actions, 3 disabled sample templates, 3 clearly labelled sample metric definitions, 12 demo values, 6 demo records, 3 submitted demo reports and 3 demo decisions. No memberships, roles, existing business records or active schedules changed. Repeat created nothing; template render/count checks passed; employee scope test passed; live browser content and screenshot inspected. Explained gaps: no live Didar/Sepidar integration, no automatic record-to-metric calculation, no independent task completion approval or comprehensive weighted performance dashboard.

## 2026-10-17 — Staff leave/mission requests and independent activity reviews
Added Portal Staff Request and Portal Activity Review, /portal-reviews, and main header/admin hub links. Daily/hourly leave (annual/sick/unpaid/other) and mission requests with Jalali dates, employee/unit, destination and descriptions; edit/resubmit unapproved requests and cancellation with history. Durations are calendar days/minutes only; payroll integration deferred until Sepidar per user.
Independent pending/approved/returned review state covers actions with activity, operational records, metric values, submitted domain reports and staff requests. Default unit manager (director/admin fallback); authorized manager selects a per-item employee reviewer without granting broad domain permissions. Self-approval prohibited. Intermediate notes, mandatory final decision notes, version hashes, row locks, stale-version rejection, audit comments and automatic re-review after edits implemented. Native report status synchronized; direct report approval route blocked. Reassignment synchronizes review employee. Portal task rows show review state. Existing eligible source records backfilled into 34 review items without changing source contents or automatically approving anything; previously approved reports untouched.
Migration succeeded. Transactional test docker/test-staff-reviews.py covers hourly leave delegation/return/resubmit/approval/cancel, approved request immutability, action re-review, report delegated review outside unit without source read access, metric values, record changes, HR unauthorized delegation, stale decisions and Guest denial; all temporary data rolled back. JS and inline syntax passed. Live browser form and hourly mission fields verified; screenshot inspected. Guide: docs/STAFF_REVIEWS_FA.md.

## 2026-10-17 — Separate staff administration from activity reviews
Split /portal-staff (leave/mission requests and their own approval/history) from /portal-reviews (activity-only review). Dedicated staff_requests.py backend and staff-requests.js frontend; staff approval state/approver/note/actor/time now belong to Portal Staff Request. Removed staff from activity SOURCES, queues, endpoints and source hooks; legacy staff review rows inaccessible to activity operations. Header/admin hub now have two independent entries. Added idempotent legacy migration preserving status, assignee, notes and dated comments, retaining original audit rows. Live migration found no existing staff rows; simulated legacy migration passed with rollback. Updated guide/docs. Transactional tests passed for both independent lifecycles, no staff activity record/queue, delegation and scope, migration preservation/idempotency, stale decisions and Guest rejection. JS/inline syntax and live browser views verified. Payroll remains deferred as requested.

## 2026-10-17 — Self-service leave routing and shared calendar
Personal staff requests now hide unit selection and resolve unit server-side from oldest active Portal Assignment; supplied unit cannot override self-routing. No active assignment produces an actionable HR message. Multiple memberships use a stable earliest assignment; existing request routing stays unchanged. Manager submissions for other employees retain unit selection. Reused shared Jalali picker and added missing standalone dialog styling; clicking the date input opens it directly. Official holiday display verified for 22 Bahman in browser, along with self unit hidden and rounded calendar shell. Updated transactional test submits personal leave without domain and passes; no real requests created during verification.

## 2026-10-17 — Hourly leave form and explicit decision feedback
Hourly leave/mission now displays one date with start/end time; end-date input hidden and not required; backend accepts omitted hourly end date as same day and still rejects cross-day hours. Hourly history displays one date. Staff approval note optional both frontend/backend (activity review note rules unchanged). Added persistent per-request feedback and visible fixed status/error notice; all decision-card buttons disabled while pending, success retained after refresh. Errors parsed safely and refresh failures shown. Timestamp comparison now uses parsed datetimes. Approval actor shown even without note. Verified single-date hourly UI and optional note in live browser without changing existing user requests; rollback tests pass with omitted hourly end date and blank approval note; JS syntax passed.

## 2026-10-17 — Deduplicate staff confirmation messages
Replaced three simultaneous notifications with one active notice. Decision success/error appears only inside its request card; if filters remove that card, only the floating notice appears. Form results appear only beside the form. Refresh preserves the active notice without duplication. Node syntax and isolated DOM-state checks passed for card, filtered-out fallback, and form scenarios.

## 2026-10-17 — Single-row hourly request fields
Grouped the hourly date, start time and end time in one responsive three-column row, including narrow screens. Daily date fields retain their separate layout. Browser DOM geometry confirmed all three controls share the same row; JS syntax passed.

## 2026-10-19 — Git handoff to another computer
Prepared accumulated portal changes for origin/main. Updated README fresh-install instructions to avoid rerunning the legacy DocType generator and added code-versus-database transfer guidance. Local environment secrets, .local and Docker data remain ignored. Staged source and presentation XML scanned against local secret values and common token/private-key patterns with no matches. Current inline JS and transactional staff/activity review checks passed.
