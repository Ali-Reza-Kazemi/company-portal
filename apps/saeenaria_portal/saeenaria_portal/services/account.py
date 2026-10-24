"""Account services; authorization is enforced inside each operation."""

import frappe

from saeenaria_portal.permissions import (
    roles,
)
from saeenaria_portal.user_names import display_name


def environment_navigation():
    user = frappe.session.user
    if user == "Guest":
        return {"links": []}
    from saeenaria_portal.permissions import can_manage_desk
    from saeenaria_portal.purchase_reports.service import allowed as purchase_allowed

    if not can_manage_desk(user) and not purchase_allowed(user):
        return {"links": []}
    links = [dict(label="پورتال روزانه", url="/portal", kind="portal")]
    if purchase_allowed(user):
        links.append(dict(label="گزارش‌های خرید و موجودی", url="/portal-purchase", kind="reports"))
        links.append(dict(label="پایش و سوابق موجودی", url="/portal-inventory", kind="reports"))
        links.append(dict(label="تکمیل اطلاعات کالاها", url="/portal-products", kind="products"))
    if can_manage_desk(user):
        links += [
            dict(label="میزکار مدیریت", url="/portal-admin", kind="hub"),
            dict(
                label="فرم‌ها و فهرست‌ها",
                url="/desk/saeenaria-portal/portal-domain",
                kind="records",
            ),
        ]
    elif purchase_allowed(user):
        links.append(dict(label="میزکار مدیریت", url="/portal-admin", kind="hub"))
    if user == "Administrator" or "System Manager" in roles(user):
        links.append(dict(label="ساخت و تنظیمات فنی", url="/desk/build", kind="build"))
    links.append(dict(label="راهنمای محیط‌ها", url="/portal-guide", kind="guide"))
    return {"links": links}


def my_account():
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("ورود لازم است", frappe.PermissionError)
    doc = frappe.get_doc("User", user)
    return {
        "name": display_name(user),
        "login": user,
        "first_name": doc.first_name,
        "last_name": doc.last_name,
        "mobile_no": doc.mobile_no,
        "domains": frappe.get_all(
            "Portal Domain",
            filters={
                "name": [
                    "in",
                    frappe.get_all(
                        "Portal Assignment",
                        filters={"user": user, "enabled": 1},
                        pluck="domain",
                    ),
                ]
            },
            fields=["title"],
        ),
    }


def update_my_profile(first_name, last_name="", mobile_no=""):
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("ورود لازم است", frappe.PermissionError)
    first_name = str(first_name or "").strip()
    last_name = str(last_name or "").strip()
    mobile_no = str(mobile_no or "").strip()
    if not first_name or len(first_name) > 100 or len(last_name) > 100 or len(mobile_no) > 30:
        frappe.throw("نام و شماره تماس معتبر وارد کنید")
    doc = frappe.get_doc("User", user)
    # No user id, email, roles, permissions or enabled flag is accepted from the client.
    doc.first_name, doc.last_name, doc.mobile_no = first_name, last_name, mobile_no
    doc.save(ignore_permissions=True)
    frappe.db.set_value(
        "Portal Template",
        {"responsible": user},
        "responsible_name",
        doc.full_name,
        update_modified=False,
    )
    frappe.clear_cache(user=user)
    return {"name": display_name(user)}
