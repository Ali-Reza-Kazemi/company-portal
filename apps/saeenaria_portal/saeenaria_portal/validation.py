import frappe
from frappe.utils import getdate, now_datetime
from saeenaria_portal.permissions import admin, can_domain, roles, can_assign

def validate_action(doc, method=None):
    user = frappe.session.user
    previous = doc.get_doc_before_save()
    external_self = bool(previous and previous.responsible==user and doc.responsible==user and previous.domain==doc.domain)
    if external_self and not can_domain(user,doc.domain,write=True):
        for key in ("domain","responsible","title","description","due_date","start_date","priority","is_demo","schedule_key","allow_external_responsible"):
            if doc.get(key)!=previous.get(key):
                frappe.throw("در کار محول‌شده از واحد دیگر فقط پیشرفت، نتیجه و مانع را تغییر دهید",frappe.PermissionError)
    if not external_self and not can_domain(user, doc.domain, write=True) and not (doc.is_new() and "Company Director" in roles(user)):
        frappe.throw("اجازه ویرایش این حوزه را ندارید", frappe.PermissionError)
    previous = doc.get_doc_before_save()
    if not can_assign(user, doc.domain) and doc.responsible != user:
        frappe.throw("فقط مدیر واحد یا مدیر شرکت می‌تواند کار را به شخص دیگر محول کند", frappe.PermissionError)
    if previous and not admin(user) and previous.responsible != user and not can_assign(user, previous.domain):
        frappe.throw("اجازه تغییر کار شخص دیگر را ندارید", frappe.PermissionError)
    if previous and previous.domain != doc.domain and not can_assign(user, previous.domain):
        frappe.throw("اجازه انتقال کار از این حوزه را ندارید", frappe.PermissionError)
    if previous and not external_self and not can_domain(user, previous.domain, write=True):
        frappe.throw("اجازه انتقال این رکورد را ندارید", frappe.PermissionError)
    old_external=bool(previous and previous.allow_external_responsible)
    if bool(doc.allow_external_responsible)!=old_external and not can_assign(user,doc.domain):
        frappe.throw("اجازه تغییر واگذاری بین‌واحدی را ندارید",frappe.PermissionError)
    explicit_external=bool(doc.allow_external_responsible and can_assign(user,doc.domain) and frappe.db.get_value("User",doc.responsible,"user_type")=="System User")
    external_template=False
    if doc.is_new() and doc.schedule_key and can_assign(user,doc.domain):
        template=frappe.db.get_value("Portal Template",doc.schedule_key.split(":")[0],["domain","responsible","enabled","allow_external_responsible"],as_dict=True)
        external_template=bool(template and template.enabled and template.allow_external_responsible and template.domain==doc.domain and template.responsible==doc.responsible)
    previous_assignment=bool(previous and previous.responsible==doc.responsible and previous.domain==doc.domain)
    if not frappe.db.get_value("User", doc.responsible, "enabled") or not (can_domain(doc.responsible, doc.domain, write=True) or explicit_external or external_template or previous_assignment):
        frappe.throw("مسئول باید مجوز ثبت در حوزه انتخاب‌شده داشته باشد")
    if doc.start_date and getdate(doc.due_date) < getdate(doc.start_date):
        frappe.throw("موعد پیش از تاریخ شروع است")
    if not 0 <= doc.progress <= 100:
        frappe.throw("پیشرفت باید بین صفر تا صد باشد")
    if doc.status == "Completed" and (doc.progress != 100 or not doc.result):
        frappe.throw("برای تکمیل، پیشرفت صد و نتیجه الزامی است")
    from saeenaria_portal.rules import private_evidence
    private_evidence(doc)

    if doc.status == "Completed":
        if previous and previous.status == "Completed":
            doc.completed_at = previous.completed_at
            doc.completed_by = previous.completed_by
            doc.completion_due_date = previous.completion_due_date
        else:
            doc.completed_at = now_datetime()
            doc.completed_by = user
            doc.completion_due_date = doc.due_date
    else:
        doc.completed_at = None
        doc.completed_by = None
        doc.completion_due_date = None
