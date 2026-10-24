"""Actions services; authorization is enforced inside each operation."""

import csv
import io

import frappe
from frappe.utils import get_datetime, getdate, today

from saeenaria_portal.csv_safety import safe_csv_cell
from saeenaria_portal.permissions import (
    admin,
    managed_domains,
    roles,
)
from saeenaria_portal.user_names import display_name


def timing_status(row, date=None):
    date = getdate(date or today())
    if row.status == "Cancelled":
        return "Cancelled"
    if row.status == "Completed":
        if not row.completed_at or not row.completion_due_date:
            return "Unknown"
        return (
            "On Time" if getdate(row.completed_at) <= getdate(row.completion_due_date) else "Late"
        )
    due = getdate(row.due_date)
    return "Overdue" if due < date else "Due Today" if due == date else "Upcoming"


def dashboard(domain=None, start=None, end=None, is_demo=0, mine=None):
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("ورود لازم است", frappe.PermissionError)
    manager = admin(user) or "Company Director" in roles(user) or bool(managed_domains(user))
    mine = not manager if mine in (None, "") else bool(int(mine))
    filters = {"is_demo": int(is_demo or 0)}
    if mine:
        filters["responsible"] = user
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
    actions = frappe.get_list(
        "Portal Action",
        filters=filters,
        fields=[
            "name",
            "title",
            "description",
            "domain",
            "responsible",
            "priority",
            "start_date",
            "due_date",
            "status",
            "progress",
            "obstacle",
            "result",
            "is_demo",
            "modified",
            "completed_at",
            "completed_by",
            "completion_due_date",
            "schedule_key",
        ],
        order_by="due_date asc",
        limit_page_length=500,
    )
    from saeenaria_portal.automatic_work import automatic_source

    # Reuse documents for filtering and permission checks within this request.
    action_docs = {row.name: frappe.get_doc("Portal Action", row.name) for row in actions}
    actions = [row for row in actions if not automatic_source(action_docs[row.name])]
    reviews = (
        {
            row.source_name: row.status
            for row in frappe.get_all(
                "Portal Activity Review",
                filters={
                    "source_type": "Portal Action",
                    "source_name": ["in", [a.name for a in actions]],
                },
                fields=["source_name", "status"],
            )
        }
        if actions
        else {}
    )
    action_domains = {
        name: frappe.db.get_value("Portal Domain", name, "title")
        for name in {row.domain for row in actions}
    }
    user_ids = {value for row in actions for value in (row.responsible, row.completed_by) if value}
    user_names = (
        {
            row.name: row.full_name or "کاربر بدون نام"
            for row in frappe.get_all(
                "User",
                filters={"name": ["in", list(user_ids)]},
                fields=["name", "full_name"],
                limit_page_length=0,
            )
        }
        if user_ids
        else {}
    )
    user_names.update({"Administrator": "مدیر سامانه", "Guest": "مهمان"})
    for row in actions:
        row["review_status"] = reviews.get(row.name)
        row["responsible_name"] = (
            user_names.get(row.responsible, "کاربر بدون نام") if row.responsible else "ثبت نشده"
        )
        row["completed_by_name"] = (
            user_names.get(row.completed_by, "کاربر بدون نام") if row.completed_by else None
        )
        row["domain_title"] = action_domains.get(row.domain)
        row["timing_status"] = timing_status(row)
        row["can_update"] = bool(
            (admin(user) or row.responsible == user)
            and frappe.has_permission("Portal Action", "write", doc=action_docs[row.name])
        )
    return {
        "domains": frappe.get_list(
            "Portal Domain", fields=["name", "title"], limit_page_length=100
        ),
        "actions": actions,
        "user": user,
        "mine": mine,
        "today": today(),
    }


def update_progress(name, status, progress, result="", obstacle="", expected_modified=None):
    doc = frappe.get_doc("Portal Action", name)
    doc.check_permission("write")
    if not admin(frappe.session.user) and doc.responsible != frappe.session.user:
        frappe.throw("فقط مسئول اقدام می‌تواند پیشرفت آن را ثبت کند", frappe.PermissionError)
    if not expected_modified or get_datetime(expected_modified) != get_datetime(doc.modified):
        frappe.throw(
            "این اقدام تغییر کرده است؛ گزارش را تازه‌سازی و دوباره تلاش کنید",
            frappe.TimestampMismatchError,
        )
    if status not in ("Open", "In Progress", "Blocked", "Completed"):
        frappe.throw("وضعیت انتخاب‌شده مجاز نیست")
    doc.status, doc.progress, doc.result, doc.obstacle = (
        status,
        progress,
        result,
        obstacle,
    )
    doc.save()
    return {"name": doc.name, "timing_status": timing_status(doc)}


def save_action(data):
    data = frappe.parse_json(data)
    allowed = {
        "title",
        "description",
        "domain",
        "responsible",
        "priority",
        "start_date",
        "due_date",
        "status",
        "progress",
        "obstacle",
        "result",
        "is_demo",
        "allow_external_responsible",
    }
    values = {key: value for key, value in data.items() if key in allowed}
    if data.get("name"):
        doc = frappe.get_doc("Portal Action", data["name"])
        doc.check_permission("write")
        doc.update(values)
        doc.save()
    else:
        doc = frappe.get_doc({"doctype": "Portal Action", **values}).insert()
    return doc.name


def management(domain=None, is_demo=0):
    filters = {"is_demo": int(is_demo or 0)}
    if domain:
        filters["domain"] = domain
    result = {
        "reports": frappe.get_list(
            "Portal Report",
            filters={**filters, "inventory_snapshot": ["is", "not set"]},
            fields=[
                "name",
                "title",
                "domain",
                "status",
                "achievements",
                "obstacles",
                "management_comment",
                "next_plan",
                "period_start",
                "period_end",
                "is_demo",
            ],
            limit_page_length=100,
        ),
        "decisions": frappe.get_list(
            "Portal Decision",
            filters=filters,
            fields=[
                "name",
                "title",
                "domain",
                "request",
                "response",
                "status",
                "due_date",
                "responded_at",
                "responded_by",
                "is_demo",
            ],
            order_by="modified desc",
            limit_page_length=100,
        ),
    }
    for decision in result["decisions"]:
        decision["responded_by_name"] = (
            display_name(decision.responded_by) if decision.responded_by else None
        )
    return result


def calendar_holidays(start, end):
    if frappe.session.user == "Guest":
        frappe.throw("ورود لازم است", frappe.PermissionError)
    start, end = getdate(start), getdate(end)
    if end < start or (end - start).days > 400:
        frappe.throw("بازه تقویم نامعتبر است")
    return frappe.get_all(
        "Portal Holiday",
        filters={"enabled": 1, "date": ["between", [start, end]]},
        fields=["date", "title"],
        limit_page_length=400,
    )


def export_actions(names, domain=None, start=None, end=None, is_demo=0, mine=None):
    """Export only requested rows still visible under the caller's current scope."""
    names = frappe.parse_json(names) if isinstance(names, str) else names
    if (
        not isinstance(names, list)
        or len(names) > 500
        or any(not isinstance(name, str) for name in names)
    ):
        frappe.throw("فهرست اقدامات نامعتبر است")
    selected = set(names)
    result = dashboard(domain=domain, start=start, end=end, is_demo=is_demo, mine=mine)
    rows = [row for row in result["actions"] if row.name in selected]
    if {row.name for row in rows} != selected:
        frappe.throw(
            "دسترسی یا فیلتر اقدامات تغییر کرده است؛ گزارش را تازه کنید",
            frappe.PermissionError,
        )
    labels = {
        "Open": "شروع‌نشده",
        "In Progress": "در حال انجام",
        "Blocked": "دارای مانع",
        "Completed": "تکمیل‌شده",
        "Cancelled": "لغوشده",
    }
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(["عنوان", "شرح اقدام", "حوزه", "مسئول", "موعد", "وضعیت", "پیشرفت", "نوع داده"])
    for row in rows:
        writer.writerow(
            [
                safe_csv_cell(value)
                for value in (
                    row.title,
                    row.description,
                    row.domain_title,
                    row.responsible_name,
                    row.due_date,
                    labels.get(row.status, row.status),
                    row.progress,
                    "آزمایشی" if row.is_demo else "واقعی",
                )
            ]
        )
    frappe.local.response.update(
        {
            "type": "download",
            "filename": "portal-actions.csv",
            "filecontent": ("\ufeff" + stream.getvalue()).encode("utf-8"),
            "content_type": "text/csv; charset=utf-8",
        }
    )
