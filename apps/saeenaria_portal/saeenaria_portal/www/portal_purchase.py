import frappe

no_cache = 1


def get_context(context):
    from saeenaria_portal.account_header import add_context
    add_context(context)
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/portal-purchase"
        raise frappe.Redirect
    from saeenaria_portal.purchase_reports.service import require_access
    require_access()
    context.no_cache = 1
    context.csrf_token = frappe.sessions.get_csrf_token()
