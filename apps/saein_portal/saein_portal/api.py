import frappe
from frappe.utils import getdate

@frappe.whitelist()
def dashboard(domain=None, start=None, end=None, is_demo=0):
    if frappe.session.user == "Guest":
        frappe.throw("ورود لازم است", frappe.PermissionError)
    filters = {"is_demo": int(is_demo or 0)}
    if domain:
        filters["domain"] = domain
    if start and end:
        if getdate(start) > getdate(end):
            frappe.throw("بازه تاریخ نادرست است")
        filters["due_date"] = ["between", [getdate(start), getdate(end)]]
    elif start:
        filters["due_date"] = [">=", getdate(start)]
    elif end:
        filters["due_date"] = ["<=", getdate(end)]
    return {
        "domains": frappe.get_list("Portal Domain", fields=["name", "title"], limit_page_length=100),
        "actions": frappe.get_list("Portal Action", filters=filters,
            fields=["name", "title", "domain", "responsible", "priority", "start_date", "due_date", "status", "progress", "obstacle", "result", "is_demo"],
            order_by="due_date asc", limit_page_length=500),
        "user": frappe.session.user,
    }

@frappe.whitelist(methods=["POST"])
def save_action(data):
    data = frappe.parse_json(data)
    allowed = {"title", "domain", "responsible", "priority", "start_date", "due_date", "status", "progress", "obstacle", "result", "is_demo"}
    values = {key: value for key, value in data.items() if key in allowed}
    if data.get("name"):
        doc = frappe.get_doc("Portal Action", data["name"])
        doc.check_permission("write")
        doc.update(values)
        doc.save()
    else:
        doc = frappe.get_doc({"doctype": "Portal Action", **values}).insert()
    return doc.name

@frappe.whitelist()
def management(domain=None, is_demo=0):
    filters = {"is_demo":int(is_demo or 0)}
    if domain: filters["domain"]=domain
    return {
        "reports":frappe.get_list("Portal Report",filters=filters,fields=["name","title","domain","status","achievements","obstacles","management_comment"],limit_page_length=100),
        "decisions":frappe.get_list("Portal Decision",filters=filters,fields=["name","title","domain","request","response","status"],limit_page_length=100),
    }
