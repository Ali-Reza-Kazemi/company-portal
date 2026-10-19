import frappe

DOMAINS = [
    ("inventory", "برنامه‌ریزی و کنترل موجودی"),
    ("marketing", "بازاریابی و پشتیبانی مهندسی فروش"),
    ("it-data", "فناوری اطلاعات و مدیریت داده"),
]

def after_install():
    for role in ("Portal Administrator", "Company Director", "Domain Officer", "Portal Contributor", "Portal HR Manager"):
        if not frappe.db.exists("Role", role):
            frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(ignore_permissions=True)
    for name, title in DOMAINS:
        if not frappe.db.exists("Portal Domain", name):
            frappe.get_doc({"doctype": "Portal Domain", "domain_code": name, "title": title}).insert(ignore_permissions=True)
    settings = frappe.get_single("System Settings")
    settings.language = "fa"
    settings.time_zone = "Asia/Tehran"
    settings.save(ignore_permissions=True)


def ensure_people_roles():
    if not frappe.db.exists("Role", "Portal HR Manager"):
        frappe.get_doc({"doctype": "Role", "role_name": "Portal HR Manager", "desk_access": 1}).insert(ignore_permissions=True)


def refresh_template_labels():
    if not frappe.db.has_column("Portal Template","responsible_name"):
        return
    for row in frappe.get_all("Portal Template",fields=["name","responsible","description"],limit_page_length=0):
        words=(row.description or "").split()
        frappe.db.set_value("Portal Template",row.name,{"responsible_name":frappe.db.get_value("User",row.responsible,"full_name") if row.responsible else "","description_preview":(" ".join(words[:12])+("…" if len(words)>12 else ""))[:140]},update_modified=False)
