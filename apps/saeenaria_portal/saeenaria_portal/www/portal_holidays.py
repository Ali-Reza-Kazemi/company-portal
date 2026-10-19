import frappe
from saeenaria_portal.permissions import admin, roles
from saeenaria_portal.holidays import current_year, SOURCE

no_cache=1

def get_context(context):
    if frappe.session.user=="Guest":
        frappe.local.flags.redirect_location="/login?redirect-to=/portal-holidays"
        raise frappe.Redirect
    if not (admin(frappe.session.user) or "Company Director" in roles(frappe.session.user)):
        frappe.throw("دسترسی فقط برای مدیر مجاز است",frappe.PermissionError)
    context.no_cache=1
    context.csrf_token=frappe.sessions.get_csrf_token()
    context.year=current_year()
    context.status=frappe.get_single("Portal Calendar Sync")
    context.source=SOURCE
