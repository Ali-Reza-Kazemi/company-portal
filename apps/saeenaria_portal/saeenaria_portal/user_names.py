import frappe

def display_name(user):
    if not user:return "ثبت نشده"
    if user=="Administrator":return "مدیر سامانه"
    if user=="Guest":return "مهمان"
    return frappe.db.get_value("User",user,"full_name") or "کاربر بدون نام"

def configure_user_titles():
    from frappe.custom.doctype.property_setter.property_setter import make_property_setter
    if not frappe.get_meta("User").show_title_field_in_link:
        make_property_setter("User",None,"show_title_field_in_link",1,"Check",for_doctype=True)
