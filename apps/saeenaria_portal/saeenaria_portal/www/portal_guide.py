import frappe
no_cache=1

def get_context(context):
    from saeenaria_portal.account_header import add_context
    add_context(context)
    if frappe.session.user=="Guest":
        frappe.local.flags.redirect_location="/login?redirect-to=/portal-guide"
        raise frappe.Redirect
    from saeenaria_portal.api import environment_navigation
    context.no_cache=1
    context.links=environment_navigation()["links"]
