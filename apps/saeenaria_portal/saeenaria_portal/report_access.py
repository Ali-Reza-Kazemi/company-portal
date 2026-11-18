"""Revocable report editing access; never grants account administration."""
import frappe
from frappe.utils import cint
from saeenaria_portal.permissions import admin
DT = 'Portal Report Access'
def shared(user=None):
    user = user or frappe.session.user
    return bool(user != 'Guest' and frappe.db.get_value('User',user,'enabled')
                and cint(frappe.db.get_single_value(DT,'enabled')))
def require_admin():
    if not admin(frappe.session.user):
        frappe.throw('مدیریت دسترسی فقط برای مدیر سامانه مجاز است',frappe.PermissionError)
@frappe.whitelist()
def status():
    require_admin()
    return {'enabled':cint(frappe.db.get_single_value(DT,'enabled'))}
@frappe.whitelist(methods=['POST'])
def configure(enabled):
    require_admin()
    if str(enabled) not in ('0','1'):
        frappe.throw('وضعیت نامعتبر است')
    doc=frappe.get_single(DT)
    doc.enabled=cint(enabled)
    doc.save(ignore_permissions=True)
    doc.add_comment('Info','دسترسی موقت عمومی '+('فعال' if doc.enabled else 'غیرفعال')+' شد؛ توسط '+frappe.session.user)
    return {'enabled':doc.enabled}
