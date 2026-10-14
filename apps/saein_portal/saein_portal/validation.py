import frappe
from frappe.utils import getdate
from saein_portal.permissions import admin, can_domain

def validate_action(doc, method=None):
    user = frappe.session.user
    if not can_domain(user, doc.domain, write=True):
        frappe.throw("اجازه ویرایش این حوزه را ندارید", frappe.PermissionError)
    previous = doc.get_doc_before_save()
    if previous and not can_domain(user, previous.domain, write=True):
        frappe.throw("اجازه انتقال این رکورد را ندارید", frappe.PermissionError)
    if not can_domain(doc.responsible, doc.domain, write=True):
        frappe.throw("مسئول باید مجوز ثبت در حوزه انتخاب‌شده داشته باشد")
    if doc.start_date and getdate(doc.due_date) < getdate(doc.start_date):
        frappe.throw("موعد پیش از تاریخ شروع است")
    if not 0 <= doc.progress <= 100:
        frappe.throw("پیشرفت باید بین صفر تا صد باشد")
    if doc.status == "Completed" and (doc.progress != 100 or not doc.result):
        frappe.throw("برای تکمیل، پیشرفت صد و نتیجه الزامی است")
    from saein_portal.rules import private_evidence
    private_evidence(doc)
