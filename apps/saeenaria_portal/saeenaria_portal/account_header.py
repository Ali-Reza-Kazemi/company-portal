import frappe
from frappe.sessions import get_csrf_token
from saeenaria_portal.permissions import admin, roles, managed_domains
from saeenaria_portal.user_names import display_name

def add_context(context):
    user=frappe.session.user
    if user=='Guest':return
    context.no_cache=1
    context.shared_account_name=display_name(user)
    context.shared_account_role=('مدیر سامانه' if admin(user) else 'مدیر شرکت' if 'Company Director' in roles(user) else 'مسئول منابع انسانی' if 'Portal HR Manager' in roles(user) else 'مدیر واحد' if managed_domains(user) else 'کارمند')
    context.csrf_token=get_csrf_token()
