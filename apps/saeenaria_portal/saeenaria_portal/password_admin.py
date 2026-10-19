import frappe
from frappe.rate_limiter import rate_limit
from saeenaria_portal.permissions import admin, roles
from saeenaria_portal.user_names import display_name

PROTECTED = {"System Manager", "Portal Administrator", "Company Director", "Portal HR Manager"}

def allowed():
    user = frappe.session.user
    return user != "Guest" and (admin(user) or "Portal HR Manager" in roles(user))

def check_access():
    if not allowed():
        frappe.throw("بازنشانی رمز کاربران فقط برای مدیر سامانه و منابع انسانی مجاز است", frappe.PermissionError)

def eligible(user):
    return user not in ("Guest", "Administrator", frappe.session.user) and (admin(frappe.session.user) or not roles(user) & PROTECTED)

@frappe.whitelist()
def users():
    check_access()
    return [dict(value=u.name, label=display_name(u.name)) for u in frappe.get_all("User", filters={"enabled": 1, "user_type": "System User"}, fields=["name"]) if eligible(u.name)]

@frappe.whitelist(methods=["POST"])
@rate_limit(limit=10, seconds=3600)
def send_reset(user, delivery="email"):
    if delivery not in ("email", "link"):
        frappe.throw("روش بازنشانی نامعتبر است")
    check_access()
    doc = frappe.get_doc("User", user)
    if not doc.enabled or doc.user_type != "System User" or not eligible(user):
        frappe.throw("بازنشانی این حساب از این بخش مجاز نیست", frappe.PermissionError)
    if delivery == "email" and not frappe.db.exists("Email Account", {"enable_outgoing": 1, "default_outgoing": 1}):
        frappe.throw("ایمیل خروجی سامانه تنظیم نشده است. مدیر سامانه باید ابتدا حساب ایمیل خروجی پیش‌فرض را تنظیم کند.")
    doc.validate_reset_password()
    link = doc._reset_password(send_email=delivery == "email")
    if delivery == "link":
        doc.add_comment("Info", "دریافت لینک بازنشانی رمز برای تحویل به کاربر توسط " + display_name(frappe.session.user))
        return {"link": link, "message": "لینک برای " + display_name(user) + " ساخته شد. فقط برای همین کارمند ارسال کنید. ساخت لینک جدید، لینک قبلی را باطل می‌کند."}
    doc.add_comment("Info", "درخواست ارسال لینک بازنشانی رمز توسط " + display_name(frappe.session.user))
    return {"message": "درخواست ارسال لینک بازنشانی ثبت شد. کاربر ایمیل و پوشه هرزنامه خود را بررسی کند؛ رمز فعلی تا تعیین رمز جدید تغییر نمی‌کند."}
