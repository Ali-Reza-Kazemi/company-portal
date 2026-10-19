import frappe
no_cache=1

def get_context(context):
    if frappe.session.user=="Guest":
        frappe.local.flags.redirect_location="/login?redirect-to=/portal-account"
        raise frappe.Redirect
    context.no_cache=1
    context.csrf_token=frappe.sessions.get_csrf_token()

    from saeenaria_portal.password_admin import allowed
    context.can_reset_passwords=allowed()
