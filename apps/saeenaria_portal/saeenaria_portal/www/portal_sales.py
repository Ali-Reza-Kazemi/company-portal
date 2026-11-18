import frappe

no_cache = 1


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/portal-sales"
        raise frappe.Redirect
    from saeenaria_portal.account_header import add_context
    from saeenaria_portal.sales_reports.service import require_access

    require_access()
    add_context(context)
    context.no_cache = 1
    context.csrf_token = frappe.sessions.get_csrf_token()
