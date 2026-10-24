import frappe
from saeenaria_portal.permissions import can_manage_desk, manage_people, admin, roles

no_cache = 1

def get_context(context):
    from saeenaria_portal.account_header import add_context
    add_context(context)
    user = frappe.session.user
    from saeenaria_portal.purchase_reports.service import allowed as purchase_allowed
    if user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/portal-admin"
        raise frappe.Redirect
    if not can_manage_desk(user) and not purchase_allowed(user):
        frappe.throw("میزکار مدیریت فقط برای مدیران و منابع انسانی در دسترس است", frappe.PermissionError)
    context.no_cache = 1
    context.user_name = "حساب مدیریت" if user == "Administrator" else frappe.db.get_value("User", user, "full_name") or user
    groups = []
    if purchase_allowed(user):
        groups.append(dict(title="خرید و کنترل موجودی", links=[dict(
            title="گزارش‌های خرید و موجودی", description="پیشنهاد سفارش، بودجه، رسوب، مشتریان هدف و گردش موجودی",
            url="/portal-purchase"), dict(title="پایش دوره‌ای و سوابق موجودی",description="کنسلی هفتگی، عملکرد ماهانه، نیاز نقدینگی و نمودار تاریخچه",url="/portal-inventory")]))
    if not can_manage_desk(user):
        context.groups = groups
        return
    def group(title, entries):
        links = [dict(title=label, description=description, url=url) for dt,label,description,url in entries if frappe.has_permission(dt, "read")]
        if links:
            groups.append(dict(title=title, links=links))
    group("برنامه‌ریزی و کارها", [
        ("Portal Action", "اقدامات کاری", "مشاهده کارها، مسئول، موعد و وضعیت اجرا", "/app/portal-action"),
        ("Portal Template", "برنامه‌های تکرارشونده", "بررسی الگوهای روزانه، هفتگی و ماهانه", "/app/portal-template"),
        ("Portal Record", "ورودی‌های عملیاتی", "مشاهده و ثبت داده‌های عملیاتی حوزه", "/app/portal-record")])
    groups.append(dict(title="واگذاری وظایف",links=[dict(title="انتقال گروهی وظایف",description="انتقال برنامه‌ها و کارهای باز کارکنان با پیش‌نمایش",url="/portal-reassign")]))
    group("گزارش و ارزیابی", [
        ("Portal Report", "گزارش‌های حوزه", "بررسی گزارش‌ها و گردش تأیید", "/app/portal-report"),
        ("Portal Decision", "تصمیم‌های مدیریت", "پیگیری درخواست‌ها و پاسخ‌های مدیریت", "/app/portal-decision"),
        ("Portal Metric", "شناسنامه شاخص‌ها", "مشاهده تعریف، واحد و روش محاسبه شاخص‌ها", "/app/portal-metric"),
        ("Portal Metric Value", "مقادیر شاخص‌ها", "ثبت و بررسی مقادیر واقعی هر دوره", "/app/portal-metric-value")])
    if manage_people(user):
        groups.append(dict(title="اعضا و نقش‌ها", links=[dict(title="کاربران و عضویت واحدها", description="تعیین مدیر واحد، کارمند و وضعیت عضویت", url="/portal#people-card")]))
    if admin(user) or "Company Director" in roles(user):
        groups.append(dict(title="تقویم کاری", links=[dict(title="به‌روزرسانی تعطیلات رسمی", description="دریافت تقویم سال جاری و بررسی آخرین به‌روزرسانی", url="/portal-holidays")]))
    if admin(user):
        group("تنظیمات سامانه", [
            ("User", "حساب‌های کاربری", "ساخت و مدیریت حساب ورود کارکنان", "/app/user"),
            ("Portal Domain", "واحدها و حوزه‌ها", "مدیریت ساختار واحدهای شرکت", "/app/portal-domain"),
            ("Portal Holiday", "تعطیلات کاری", "ثبت تعطیلات برای تقویم و برنامه‌ریزی", "/app/portal-holiday"),
            ("Portal Policy", "قواعد پورتال", "بررسی سیاست‌ها و قواعد سامانه", "/app/portal-policy")])
    from saeenaria_portal.password_admin import allowed
    if allowed():
        groups.append(dict(title="امنیت حساب‌ها", links=[dict(title="بازنشانی رمز کاربران", description="ارسال لینک تعیین رمز جدید به ایمیل کارکنان", url="/portal-account#reset-users")]))
    groups.append(dict(title="آموزش",links=[dict(title="آموزش کاربردی با مثال و نمودار",description="مسیر کامل از واگذاری کار تا گزارش و تصمیم",url="/portal-training")]))
    groups.append(dict(title="امور کارکنان",links=[dict(title="مرخصی و مأموریت",description="ثبت، پیگیری و تأیید درخواست‌های کارکنان",url="/portal-staff")]))
    groups.append(dict(title="کنترل فعالیت‌ها",links=[dict(title="بررسی و تأیید فعالیت‌ها",description="بررسی خروجی کارها، ورودی‌های عملیاتی و گزارش‌ها",url="/portal-reviews")]))
    context.groups = groups
