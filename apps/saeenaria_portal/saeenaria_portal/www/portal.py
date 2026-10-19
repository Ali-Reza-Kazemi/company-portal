import frappe

no_cache = 1

def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/portal"
        raise frappe.Redirect
    context.no_cache = 1
    context.csrf_token = frappe.sessions.get_csrf_token()

    from saeenaria_portal.permissions import admin, roles, managed_domains
    context.portal_user_name = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user
    context.portal_role = ("مدیر سامانه" if admin(frappe.session.user) else "مدیر شرکت" if "Company Director" in roles(frappe.session.user) else "مسئول منابع انسانی" if "Portal HR Manager" in roles(frappe.session.user) else "مدیر واحد" if managed_domains(frappe.session.user) else "کارمند")

    from saeenaria_portal.permissions import manage_people
    context.can_manage_people = manage_people(frappe.session.user)

    from saeenaria_portal.permissions import can_manage_desk
    context.can_manage_desk = can_manage_desk(frappe.session.user)
