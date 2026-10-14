import frappe

DOMAINS = [
    ("inventory", "برنامه‌ریزی و کنترل موجودی"),
    ("marketing", "بازاریابی و پشتیبانی مهندسی فروش"),
    ("it-data", "فناوری اطلاعات و مدیریت داده"),
]

def after_install():
    for role in ("Portal Administrator", "Company Director", "Domain Officer", "Portal Contributor"):
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(ignore_permissions=True)
    for name, title in DOMAINS:
        if not frappe.db.exists("Portal Domain", name):
            frappe.get_doc({"doctype": "Portal Domain", "domain_code": name, "title": title}).insert(ignore_permissions=True)
    settings = frappe.get_single("System Settings")
    settings.language = "fa"
    settings.time_zone = "Asia/Tehran"
    settings.save(ignore_permissions=True)
