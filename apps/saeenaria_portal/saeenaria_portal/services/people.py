"""People services; authorization is enforced inside each operation."""

import frappe
from frappe.utils import get_datetime

from saeenaria_portal.permissions import (
    admin,
    can_assign,
    manage_people,
    roles,
)


def responsible_users(domain, all_users=0):
    """Return enabled members of an accessible domain, without exposing other users."""
    user = frappe.session.user
    if user == "Guest" or not frappe.has_permission(
        "Portal Domain", "read", doc=frappe.get_doc("Portal Domain", domain)
    ):
        frappe.throw("اجازه مشاهده این حوزه را ندارید", frappe.PermissionError)
    if int(all_users):
        if not can_assign(user, domain):
            frappe.throw(
                "انتخاب کاربران سایر حوزه‌ها فقط برای مدیر مجاز است",
                frappe.PermissionError,
            )
        return frappe.get_all(
            "User",
            filters={
                "enabled": 1,
                "user_type": "System User",
                "name": ["not in", ["Guest", "Administrator"]],
            },
            fields=["name", "full_name"],
            order_by="full_name asc",
            limit_page_length=0,
        )
    members = frappe.get_all(
        "Portal Assignment", filters={"domain": domain, "enabled": 1}, pluck="user"
    )
    if not can_assign(user, domain):
        members = [member for member in members if member == user]
    if not members:
        return []
    return frappe.get_all(
        "User",
        filters={"enabled": 1, "name": ["in", list(set(members) - {"Guest"})]},
        fields=["name", "full_name"],
        order_by="full_name asc",
        limit_page_length=0,
    )


def people_overview():
    if not manage_people(frappe.session.user):
        frappe.throw("فقط مدیر ارشد یا مسئول منابع انسانی دسترسی دارد", frappe.PermissionError)
    users = frappe.get_all(
        "User",
        filters={
            "name": ["not in", ["Guest", "Administrator"]],
            "user_type": "System User",
        },
        fields=["name", "full_name", "enabled"],
        order_by="full_name asc",
        limit_page_length=0,
    )
    return {
        "users": users,
        "domains": frappe.get_all("Portal Domain", fields=["name", "title"]),
        "assignments": frappe.get_all(
            "Portal Assignment",
            fields=["name", "domain", "user", "enabled", "is_manager", "modified"],
            limit_page_length=0,
        ),
        "hr_users": frappe.get_all(
            "Has Role",
            filters={"parenttype": "User", "role": "Portal HR Manager"},
            pluck="parent",
        ),
        "can_set_hr": admin(frappe.session.user)
        or "Company Director" in roles(frappe.session.user),
    }


def set_unit_member(user, domain, is_manager=0, enabled=1, expected_modified=None):
    if not manage_people(frappe.session.user):
        frappe.throw(
            "فقط مدیر ارشد یا مسئول منابع انسانی می‌تواند نقش واحد را تغییر دهد",
            frappe.PermissionError,
        )
    if user in ("Guest", "Administrator") or not frappe.db.get_value("User", user, "enabled"):
        frappe.throw("کاربر فعال معتبر را انتخاب کنید")
    if not frappe.db.exists("Portal Domain", domain):
        frappe.throw("حوزه معتبر را انتخاب کنید")
    names = frappe.get_all(
        "Portal Assignment", filters={"user": user, "domain": domain}, pluck="name"
    )
    if len(names) > 1:
        frappe.throw("عضویت تکراری وجود دارد؛ مدیر سامانه باید آن را اصلاح کند")
    doc = (
        frappe.get_doc("Portal Assignment", names[0])
        if names
        else frappe.new_doc("Portal Assignment")
    )
    if names and (
        not expected_modified or get_datetime(expected_modified) != get_datetime(doc.modified)
    ):
        frappe.throw(
            "عضویت تغییر کرده است؛ فهرست را تازه‌سازی کنید",
            frappe.TimestampMismatchError,
        )
    doc.update(
        {
            "user": user,
            "domain": domain,
            "is_manager": int(bool(int(is_manager))),
            "enabled": int(bool(int(enabled))),
        }
    )
    doc.save(ignore_permissions=True)
    # Membership needs a base portal role; never grant an administrative role here.
    if doc.enabled and not (
        roles(user)
        & {
            "Domain Officer",
            "Portal Contributor",
            "Company Director",
            "System Manager",
            "Portal Administrator",
        }
    ):
        member = frappe.get_doc("User", user)
        member.append("roles", {"role": "Portal Contributor"})
        member.save(ignore_permissions=True)
    frappe.clear_cache(user=user)
    return {"name": doc.name, "modified": doc.modified}


def delete_unit_member(name, expected_modified):
    if not manage_people(frappe.session.user):
        frappe.throw(
            "فقط مدیر مجاز یا منابع انسانی می‌تواند عضویت اشتباه را حذف کند",
            frappe.PermissionError,
        )
    frappe.db.get_value("Portal Assignment", name, "name", for_update=True)
    doc = frappe.get_doc("Portal Assignment", name)
    if not expected_modified or get_datetime(expected_modified) != get_datetime(doc.modified):
        frappe.throw(
            "عضویت تغییر کرده است؛ فهرست را تازه‌سازی کنید",
            frappe.TimestampMismatchError,
        )
    if doc.user in ("Guest", "Administrator"):
        frappe.throw("حذف این عضویت مجاز نیست")
    user = doc.user
    frappe.delete_doc("Portal Assignment", doc.name, ignore_permissions=True)
    frappe.clear_cache(user=user)
    return "عضویت اشتباه حذف شد؛ حساب کاربر و سوابق فعالیت‌ها حفظ شدند."


def set_hr_manager(user, enabled):
    if not (admin(frappe.session.user) or "Company Director" in roles(frappe.session.user)):
        frappe.throw(
            "تعیین مسئول منابع انسانی فقط در اختیار مدیر ارشد است",
            frappe.PermissionError,
        )
    if user in ("Guest", "Administrator") or not frappe.db.get_value("User", user, "enabled"):
        frappe.throw("کاربر فعال معتبر را انتخاب کنید")
    member = frappe.get_doc("User", user)
    if int(enabled):
        if "Portal HR Manager" not in roles(user):
            member.append("roles", {"role": "Portal HR Manager"})
        if not (
            roles(user)
            & {
                "Domain Officer",
                "Portal Contributor",
                "Company Director",
                "System Manager",
                "Portal Administrator",
            }
        ):
            member.append("roles", {"role": "Portal Contributor"})
    else:
        member.set("roles", [row for row in member.roles if row.role != "Portal HR Manager"])
    member.save(ignore_permissions=True)
    frappe.clear_cache(user=user)
    return {"user": user}


def template_responsibles(doctype, txt, searchfield, start, page_len, filters):
    filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
    domain = filters.get("domain")
    from saeenaria_portal.permissions import can_domain

    user = frappe.session.user
    if user == "Guest" or not domain or not can_domain(user, domain):
        frappe.throw("ابتدا حوزه مجاز را انتخاب کنید", frappe.PermissionError)
    if int(filters.get("all_users") or 0):
        if not can_assign(user, domain):
            frappe.throw(
                "انتخاب مسئول سایر حوزه‌ها فقط برای مدیر مجاز است",
                frappe.PermissionError,
            )
        members = frappe.get_all(
            "User", filters={"enabled": 1, "user_type": "System User"}, pluck="name"
        )
    else:
        members = [row.name for row in responsible_users(domain)]
    if not members:
        return []
    rows = frappe.get_all(
        "User",
        filters={
            "enabled": 1,
            "name": ["in", list(set(members) - {"Guest", "Administrator"})],
        },
        or_filters={
            "name": ["like", "%" + txt + "%"],
            "full_name": ["like", "%" + txt + "%"],
        },
        fields=["name", "full_name"],
        order_by="full_name asc",
        start=int(start),
        limit_page_length=min(int(page_len), 50),
    )
    return [[row.name, row.full_name] for row in rows]


def template_assignment_access(domain):
    from saeenaria_portal.permissions import can_domain

    if frappe.session.user == "Guest" or not can_domain(frappe.session.user, domain):
        frappe.throw("حوزه مجاز نیست", frappe.PermissionError)
    return can_assign(frappe.session.user, domain)


def template_responsible_options(domain, all_users=0, template=None):
    from saeenaria_portal.permissions import can_domain

    user = frappe.session.user
    if user == "Guest" or not can_domain(user, domain):
        frappe.throw("حوزه مجاز نیست", frappe.PermissionError)
    if int(all_users):
        if not can_assign(user, domain):
            frappe.throw("نمایش همه کاربران فقط برای مدیر مجاز است", frappe.PermissionError)
        users = frappe.get_all(
            "User",
            filters={
                "enabled": 1,
                "user_type": "System User",
                "name": ["not in", ["Guest", "Administrator"]],
            },
            fields=["name", "full_name"],
            order_by="full_name asc",
            limit_page_length=0,
        )
    else:
        users = responsible_users(domain)
    current = None
    if template and frappe.db.exists("Portal Template", template):
        doc = frappe.get_doc("Portal Template", template)
        doc.check_permission("read")
        if doc.responsible:
            current = frappe.db.get_value(
                "User", doc.responsible, ["name", "full_name"], as_dict=True
            )
    return {"users": users, "current": current}
