import frappe
from saeenaria_portal.reassignment import allowed_domains
no_cache=1

def get_context(context):
    from saeenaria_portal.account_header import add_context
    add_context(context)
    if frappe.session.user=="Guest":
        frappe.local.flags.redirect_location="/login?redirect-to=/portal-reassign"
        raise frappe.Redirect
    allowed_domains()
    context.no_cache=1
    context.csrf_token=frappe.sessions.get_csrf_token()
