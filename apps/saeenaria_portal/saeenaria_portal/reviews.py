import hashlib
import json

import frappe
from frappe.utils import cint, flt, get_datetime, get_time, getdate, now_datetime

from saeenaria_portal.permissions import admin, domains, managed_domains, roles
from saeenaria_portal.user_names import display_name

SOURCES = {
    "Portal Action": [
        "title",
        "description",
        "domain",
        "responsible",
        "status",
        "progress",
        "result",
        "obstacle",
        "due_date",
        "completed_at",
        "is_demo",
    ],
    "Portal Record": [
        "title",
        "domain",
        "responsible",
        "record_type",
        "record_date",
        "details",
        "quantity",
        "amount",
        "cost",
        "status",
        "channel",
        "item_code",
        "customer_code",
        "service",
        "planned_at",
        "ordered_at",
        "promised_at",
        "actual_at",
        "rating",
        "external_id",
        "period_start",
        "period_end",
        "baseline_snapshot",
        "locked",
        "is_demo",
    ],
    "Portal Metric Value": [
        "domain",
        "metric",
        "period_start",
        "period_end",
        "actual",
        "has_target",
        "target",
        "data_status",
        "source",
        "is_demo",
        "responsible",
    ],
    "Portal Report": [
        "title",
        "domain",
        "period_start",
        "period_end",
        "achievements",
        "obstacles",
        "next_plan",
        "is_demo",
        "inventory_snapshot",
    ],
}
LABELS = {
    "Portal Action": "اقدام کاری",
    "Portal Record": "ورودی عملیاتی",
    "Portal Metric Value": "مقدار شاخص",
    "Portal Report": "گزارش حوزه",
}


def signed_in():
    if frappe.session.user == "Guest":
        frappe.throw("ورود لازم است", frappe.PermissionError)


def leadership(user):
    return admin(user) or "Company Director" in roles(user)


def assignable(review, user):
    return leadership(user) or review.domain in managed_domains(user)


def delegated_reviewer(review):
    if review.source_type not in SOURCES:
        return None
    records = frappe.get_all(
        "Portal Review Delegation",
        filters={
            "domain": review.domain,
            "enabled": 1,
            "is_demo": cint(review.is_demo),
            "start_date": ["<=", frappe.utils.today()],
        },
        fields=["reviewer", "end_date", "scope", "selection_json"],
        order_by="creation desc",
    )
    for row in records:
        if row.end_date and getdate(row.end_date) < getdate(frappe.utils.today()):
            continue
        if not row.scope or row.scope == "Reports":
            if review.source_type != "Portal Report" or review.domain != "inventory":
                continue
        elif row.scope == "Series":
            if review_series(review) not in json.loads(row.selection_json or "[]"):
                continue
        if row.reviewer != review.employee and frappe.db.get_value("User", row.reviewer, "enabled"):
            return row.reviewer
    return None


def review_series(review):
    if review.source_type == "Portal Action":
        key = frappe.db.get_value("Portal Action", review.source_name, "schedule_key") or ""
        template = key.rsplit(":", 1)[0]
        if template and frappe.db.exists(
            "Portal Template", {"name": template, "domain": review.domain}
        ):
            return "template:" + template
    if review.source_type == "Portal Metric Value":
        return "metric:" + str(
            frappe.db.get_value("Portal Metric Value", review.source_name, "metric")
        )
    if review.source_type == "Portal Report":
        snapshot = frappe.db.get_value("Portal Report", review.source_name, "inventory_snapshot")
        if snapshot:
            return "report:" + str(
                frappe.db.get_value("Portal Inventory Snapshot", snapshot, "kind")
            )
    return "item:" + review.source_type + ":" + review.source_name


def can_review(review, user):
    from saeenaria_portal.automatic_work import automatic_review

    if review.source_type not in SOURCES or automatic_review(review):
        return False
    if user == "Guest" or user == review.employee:
        return False
    if leadership(user):
        return True
    if review.reviewer:
        return review.reviewer == user
    delegate = delegated_reviewer(review)
    if delegate:
        return delegate == user
    return leadership(user) or review.domain in managed_domains(user)


def can_view(review, user):
    return review.source_type in SOURCES and (
        user == review.employee
        or user == review.reviewer
        or assignable(review, user)
        or user == delegated_reviewer(review)
    )


def review_validate(doc, method=None):
    if not doc.flags.portal_review_internal:
        frappe.throw(
            "بررسی فقط از صفحه بررسی و تأیید فعالیت‌ها انجام می‌شود",
            frappe.PermissionError,
        )


def save_review(doc):
    doc.flags.portal_review_internal = True
    doc.save(ignore_permissions=True)


def snapshot(doc):
    values = {}
    for key in SOURCES[doc.doctype]:
        value = doc.get(key)
        field = doc.meta.get_field(key)
        kind = field.fieldtype if field else "Data"
        if kind in ("Check", "Int"):
            value = cint(value)
        elif kind in ("Float", "Currency", "Percent"):
            value = flt(value)
        elif value in (None, ""):
            value = None
        elif kind == "Date":
            value = getdate(value).isoformat()
        elif kind == "Datetime":
            value = get_datetime(value).isoformat()
        elif kind == "Time":
            value = str(get_time(value))
        values[key] = value
    values["evidence"] = doc.get("evidence") or None
    text = json.dumps(values, ensure_ascii=False, default=str, sort_keys=True)
    return text, hashlib.sha256(text.encode()).hexdigest()


def sync(doc, method=None):
    if doc.doctype not in SOURCES:
        return
    if getattr(frappe.local, "portal_review_decision", None) == (doc.doctype, doc.name):
        return
    from saeenaria_portal.automatic_work import automatic_source

    if automatic_source(doc):
        return
    text, digest = snapshot(doc)
    key = doc.doctype + ":" + doc.name
    name = frappe.db.get_value("Portal Activity Review", {"source_key": key}, "name")
    if not name:
        if (
            doc.doctype == "Portal Action"
            and doc.status != "Completed"
            and not doc.progress
            and not doc.result
        ):
            return
        if doc.doctype == "Portal Report" and doc.status != "Submitted":
            return
    if name:
        review = frappe.get_doc("Portal Activity Review", name)
        if review.source_hash == digest and not (
            doc.doctype == "Portal Report"
            and doc.status == "Submitted"
            and review.status == "Returned"
        ):
            return
    else:
        review = frappe.new_doc("Portal Activity Review")
        review.source_key = key
        review.source_type = doc.doctype
        review.source_name = doc.name
    review.title = doc.get("title") or (
        "مقدار شاخص: "
        + str(frappe.db.get_value("Portal Metric", doc.get("metric"), "title") or doc.name)
    )
    review.domain = doc.domain
    review.employee = doc.get("employee") or doc.get("responsible") or doc.owner
    if doc.doctype == "Portal Report" and doc.get("inventory_snapshot"):
        review.employee = (
            frappe.db.get_value("Portal Inventory Snapshot", doc.inventory_snapshot, "responsible")
            or review.employee
        )
    if review.reviewer == review.employee:
        review.reviewer = None
    review.snapshot = text
    review.source_hash = digest
    review.is_demo = doc.get("is_demo") or 0
    review.status = (
        "Cancelled" if doc.get("cancelled") or doc.get("status") == "Cancelled" else "Pending"
    )
    review.review_note = None
    review.reviewed_at = None
    review.reviewed_by = None
    save_review(review)


@frappe.whitelist()
def overview(is_demo=0):
    signed_in()
    user = frappe.session.user
    filters = {"is_demo": cint(is_demo)}
    rows = frappe.get_all(
        "Portal Activity Review",
        filters=filters,
        fields=["*"],
        order_by="modified desc",
        limit_page_length=0,
    )
    output = []
    for row in rows:
        from saeenaria_portal.automatic_work import automatic_review

        if automatic_review(row) or not can_view(row, user):
            continue
        row["employee_name"] = display_name(row.employee)
        reviewer = row.reviewer or delegated_reviewer(row)
        row["reviewer_name"] = display_name(reviewer) if reviewer else "مدیر واحد"
        row["reviewed_by_name"] = display_name(row.reviewed_by) if row.reviewed_by else ""
        row["kind"] = LABELS[row.source_type]
        row["can_review"] = can_review(row, user)
        row["can_assign"] = assignable(row, user) and row.status not in (
            "Approved",
            "Cancelled",
        )
        row["series_key"] = review_series(row)
        row.pop("source_key", None)
        row.pop("source_hash", None)
        output.append(row)
    return {"reviews": output, "user": user}


def locked_review(name):
    frappe.db.get_value("Portal Activity Review", name, "name", for_update=True)
    doc = frappe.get_doc("Portal Activity Review", name)
    from saeenaria_portal.automatic_work import automatic_review

    if automatic_review(doc):
        frappe.throw("خروجی خودکار به بررسی یا تأیید انسانی نیاز ندارد", frappe.PermissionError)
    if doc.source_type not in SOURCES:
        frappe.throw(
            "این مورد مربوط به فعالیت‌ها نیست؛ به بخش مرخصی و مأموریت مراجعه کنید",
            frappe.PermissionError,
        )
    return doc


@frappe.whitelist(methods=["POST"])
def assign_reviewer(name, reviewer, expected_modified):
    signed_in()
    doc = locked_review(name)
    if not assignable(doc, frappe.session.user):
        frappe.throw("تعیین بررسی‌کننده فقط برای مدیر مجاز است", frappe.PermissionError)
    if str(doc.modified) != str(expected_modified):
        frappe.throw("اطلاعات تغییر کرده؛ صفحه را تازه کنید")
    if doc.status == "Cancelled":
        frappe.throw("درخواست لغو شده است")
    if doc.status == "Approved":
        frappe.throw("مورد تأییدشده به بررسی دوباره نیاز ندارد؛ برای تغییر محتوا اصلاحیه ثبت کنید")
    if reviewer and (
        reviewer == doc.employee
        or not frappe.db.exists(
            "User", {"name": reviewer, "enabled": 1, "user_type": "System User"}
        )
    ):
        frappe.throw("بررسی‌کننده باید کاربر فعال و غیر از صاحب فعالیت باشد")
    doc.reviewer = reviewer or None
    doc.status = "Pending"
    doc.review_note = None
    doc.reviewed_at = None
    doc.reviewed_by = None
    save_review(doc)
    doc.add_comment(
        "Info",
        "تعیین بررسی‌کننده توسط "
        + display_name(frappe.session.user)
        + ": "
        + (display_name(reviewer) if reviewer else "مدیر واحد"),
    )
    return "بررسی‌کننده تعیین شد؛ این اختیار فقط برای همین مورد است."


@frappe.whitelist(methods=["POST"])
def decide(name, status, note, expected_modified):
    signed_in()
    doc = locked_review(name)
    if not can_review(doc, frappe.session.user):
        frappe.throw(
            "شما بررسی‌کننده این مورد نیستید یا صاحب فعالیت هستید",
            frappe.PermissionError,
        )
    if doc.status != "Pending" or str(doc.modified) != str(expected_modified):
        frappe.throw("نسخه مورد بررسی تغییر کرده؛ صفحه را تازه کنید")
    if status not in ("Approved", "Returned"):
        frappe.throw("نتیجه بررسی نامعتبر است")
    if not (note or "").strip():
        frappe.throw("نظر بررسی‌کننده الزامی است")
    frappe.db.get_value(doc.source_type, doc.source_name, "name", for_update=True)
    source = frappe.get_doc(doc.source_type, doc.source_name)
    if snapshot(source)[1] != doc.source_hash:
        frappe.throw("محتوای فعالیت تغییر کرده است؛ نسخه جدید باید بررسی شود")
    if source.doctype == "Portal Action" and status == "Approved" and source.status != "Completed":
        frappe.throw(
            "تأیید نهایی اقدام فقط پس از ثبت انجام کامل ممکن است؛ برای بررسی میانی نظر ثبت کنید"
        )
    doc.status = status
    doc.review_note = note.strip()
    doc.reviewed_by = frappe.session.user
    doc.reviewed_at = now_datetime()
    if source.doctype == "Portal Report":
        source.status = "Approved" if status == "Approved" else "Needs Revision"
        source.management_comment = doc.review_note
        frappe.local.portal_review_decision = (source.doctype, source.name)
        try:
            source.save(ignore_permissions=True)
        finally:
            frappe.local.portal_review_decision = None
    save_review(doc)
    doc.add_comment(
        "Info",
        ("تأیید" if status == "Approved" else "برگشت برای اصلاح")
        + " توسط "
        + display_name(frappe.session.user)
        + ": "
        + frappe.utils.escape_html(doc.review_note),
    )
    return "نتیجه بررسی ثبت شد."


@frappe.whitelist(methods=["POST"])
def comment(name, note):
    signed_in()
    doc = locked_review(name)
    if not can_review(doc, frappe.session.user):
        frappe.throw("اجازه بررسی ندارید", frappe.PermissionError)
    if doc.status != "Pending":
        frappe.throw("بررسی این مورد پایان یافته است")
    if not (note or "").strip():
        frappe.throw("نظر را بنویسید")
    doc.add_comment(
        "Info",
        "نظر بررسی توسط "
        + display_name(frappe.session.user)
        + ": "
        + frappe.utils.escape_html(note.strip()),
    )
    doc.review_note = note.strip()
    save_review(doc)
    return "نظر بررسی ثبت شد؛ این کار به معنی تأیید نهایی نیست."


@frappe.whitelist()
def history(name):
    signed_in()
    doc = frappe.get_doc("Portal Activity Review", name)
    if not can_view(doc, frappe.session.user):
        frappe.throw("اجازه مشاهده ندارید", frappe.PermissionError)
    from frappe.utils import strip_html

    return [
        strip_html(row.content)
        for row in frappe.get_all(
            "Comment",
            filters={
                "reference_doctype": doc.doctype,
                "reference_name": doc.name,
                "comment_type": "Info",
            },
            fields=["content"],
            order_by="creation asc",
            limit_page_length=100,
        )
    ]


def backfill():
    if not admin(frappe.session.user):
        frappe.throw("فقط مدیر سامانه", frappe.PermissionError)
    count = 0
    for doctype in SOURCES:
        for name in frappe.get_all(doctype, pluck="name", limit_page_length=0):
            if not frappe.db.exists("Portal Activity Review", {"source_key": doctype + ":" + name}):
                sync(frappe.get_doc(doctype, name))
                count += 1
    return {
        "examined": count,
        "review_count": frappe.db.count("Portal Activity Review"),
    }


@frappe.whitelist()
def options():
    signed_in()
    user = frappe.session.user
    units = frappe.get_all("Portal Domain", fields=["name", "title"], limit_page_length=0)
    if not leadership(user):
        units = [d for d in units if d.name in domains(user) or d.name in managed_domains(user)]
    can_assign = leadership(user) or bool(managed_domains(user))
    users = (
        frappe.get_all(
            "User",
            filters={"enabled": 1, "user_type": "System User", "name": ["!=", "Guest"]},
            fields=["name", "full_name"],
            limit_page_length=0,
        )
        if can_assign
        else []
    )
    for row in users:
        row["full_name"] = display_name(row.name)
    can_delegate = leadership(user) or "inventory" in managed_domains(user)
    assign_domains = [d.name for d in units if leadership(user) or d.name in managed_domains(user)]
    delegations = (
        frappe.get_all(
            "Portal Review Delegation",
            filters={"domain": ["in", assign_domains]},
            fields=[
                "name",
                "domain",
                "scope",
                "selection_json",
                "reviewer",
                "start_date",
                "end_date",
                "enabled",
                "modified",
                "is_demo",
            ],
            order_by="creation desc",
            limit_page_length=0,
        )
        if assign_domains
        else []
    )
    for row in delegations:
        row["reviewer_name"] = display_name(row.reviewer)
    series = []
    if assign_domains:
        for t in frappe.get_all(
            "Portal Template",
            filters={"domain": ["in", assign_domains], "enabled": 1},
            fields=["name", "title", "domain"],
            limit_page_length=0,
        ):
            series.append(
                dict(
                    key="template:" + t.name,
                    title="برنامه تکرارشونده: " + t.title,
                    domain=t.domain,
                    is_demo=0,
                )
            )
        for m in frappe.get_all(
            "Portal Metric",
            filters={"domain": ["in", assign_domains]},
            fields=["name", "title", "domain"],
            limit_page_length=0,
        ):
            if m.name.startswith("INV-M-"):
                continue
            series.append(
                dict(
                    key="metric:" + m.name,
                    title="بررسی مقادیر شاخص: " + m.title,
                    domain=m.domain,
                    is_demo=0,
                )
            )
        for review in frappe.get_all(
            "Portal Activity Review",
            filters={
                "domain": ["in", assign_domains],
                "is_demo": 0,
                "status": "Pending",
                "source_type": ["in", list(SOURCES)],
            },
            fields=["name", "source_type", "source_name", "domain", "title"],
            limit_page_length=0,
        ):
            key = review_series(review)
            if key.startswith("item:"):
                series.append(dict(key=key, title=review.title, domain=review.domain, is_demo=0))
    return {
        "domains": units,
        "users": users,
        "self": user,
        "self_name": display_name(user),
        "can_bulk_assign": can_assign,
        "assign_domains": assign_domains,
        "series": series,
        "can_delegate_inventory": can_delegate,
        "delegations": delegations,
    }


@frappe.whitelist(methods=["POST"])
def delegate_domain(domain, reviewer, scope="Domain", keys=None, is_demo=0):
    signed_in()
    user = frappe.session.user
    if not domain or not (leadership(user) or domain in managed_domains(user)):
        frappe.throw("اجازه واگذاری این حوزه را ندارید", frappe.PermissionError)
    if scope not in ("Domain", "Series"):
        frappe.throw("دامنه واگذاری نامعتبر است")
    if not frappe.db.exists("User", {"name": reviewer, "enabled": 1, "user_type": "System User"}):
        frappe.throw("بررسی‌کننده فعال را انتخاب کنید")
    keys = frappe.parse_json(keys) or []
    if not isinstance(keys, list):
        frappe.throw("انتخاب فعالیت نامعتبر است")
    allowed = {
        s["key"]
        for s in options()["series"]
        if s["domain"] == domain and s["is_demo"] == cint(is_demo)
    }
    if scope == "Series" and (not keys or any(k not in allowed for k in keys)):
        frappe.throw("برنامه‌ها و شاخص‌های مجاز همان حوزه را انتخاب کنید")
    frappe.db.get_value("Portal Domain", domain, "name", for_update=True)
    # Keep a single current routing rule per domain and data type; prior rules remain in audit history.
    for row in frappe.get_all(
        "Portal Review Delegation",
        filters={"domain": domain, "enabled": 1, "is_demo": cint(is_demo)},
        pluck="name",
    ):
        old = frappe.get_doc("Portal Review Delegation", row)
        old.enabled = 0
        old.flags.portal_delegation_internal = True
        old.save(ignore_permissions=True)
        old.add_comment("Info", "جایگزینی با تنفیذ جدید توسط " + display_name(user))
    doc = frappe.get_doc(
        dict(
            doctype="Portal Review Delegation",
            domain=domain,
            reviewer=reviewer,
            scope=scope,
            selection_json=json.dumps(sorted(set(keys)) if scope == "Series" else []),
            is_demo=cint(is_demo),
            enabled=1,
            start_date=frappe.utils.today(),
        )
    )
    doc.flags.portal_delegation_internal = True
    doc.insert(ignore_permissions=True)
    doc.add_comment(
        "Info",
        "تنفیذ بررسی تا لغو یا تنفیذ مجدد توسط "
        + display_name(user)
        + " به "
        + display_name(reviewer),
    )
    for row in frappe.get_all(
        "Portal Activity Review",
        filters={
            "domain": domain,
            "is_demo": cint(is_demo),
            "status": "Pending",
            "source_type": ["in", list(SOURCES)],
        },
        fields=["name"],
    ):
        review = locked_review(row.name)
        if review.employee != reviewer and (scope == "Domain" or review_series(review) in keys):
            review.reviewer = None
            save_review(review)
            review.add_comment(
                "Info",
                "مسیر بررسی به تنفیذ جدید حوزه سپرده شد: " + display_name(reviewer),
            )
    return "تنفیذ ثبت شد؛ موارد فعلی و نوبت‌های آینده تا لغو یا تنفیذ مجدد پوشش داده می‌شوند. تأییدهای قبلی محفوظ‌اند."


@frappe.whitelist(methods=["POST"])
def preview_bulk_reviewer(domain, reviewer, names, is_demo=0):
    signed_in()
    user = frappe.session.user
    if not domain or not (leadership(user) or domain in managed_domains(user)):
        frappe.throw("حوزه مجاز را انتخاب کنید", frappe.PermissionError)
    if not frappe.db.exists("User", {"name": reviewer, "enabled": 1, "user_type": "System User"}):
        frappe.throw("بررسی‌کننده فعال را انتخاب کنید")
    names = frappe.parse_json(names)
    if not isinstance(names, list) or not names or len(names) > 500:
        frappe.throw("بین یک تا ۵۰۰ مورد انتخاب کنید")
    items = []
    skipped = []
    for name in sorted(set(names)):
        doc = frappe.get_doc("Portal Activity Review", name)
        if (
            doc.domain != domain
            or not assignable(doc, user)
            or doc.source_type not in SOURCES
            or cint(doc.is_demo) != cint(is_demo)
        ):
            frappe.throw(
                "انتخاب‌ها باید فقط از حوزه و نوع داده انتخاب‌شده باشند",
                frappe.PermissionError,
            )
        reason = "" if doc.status == "Pending" else "در انتظار بررسی نیست"
        if doc.employee == reviewer:
            reason = "بررسی‌کننده صاحب فعالیت است"
        if doc.reviewer == reviewer:
            reason = "قبلاً به همین شخص سپرده شده"
        if not review_series(doc).startswith("item:"):
            reason = "برای فعالیت دوره‌ای از تنفیذ مستمر استفاده کنید"
        row = dict(
            name=doc.name,
            title=doc.title,
            employee_name=display_name(doc.employee),
            modified=str(doc.modified),
        )
        if reason:
            skipped.append({**row, "reason": reason})
        else:
            items.append(row)
    return {"items": items, "skipped": skipped, "reviewer_name": display_name(reviewer)}


@frappe.whitelist(methods=["POST"])
def bulk_assign_reviewer(domain, reviewer, items, is_demo=0):
    signed_in()
    items = frappe.parse_json(items)
    if not isinstance(items, list) or not items:
        frappe.throw("ابتدا پیش‌نمایش را بررسی کنید")
    if any(
        not isinstance(row, dict) or not row.get("name") or not row.get("modified") for row in items
    ):
        frappe.throw("انتخاب نامعتبر است")
    preview = preview_bulk_reviewer(domain, reviewer, [r["name"] for r in items], is_demo)
    if preview["skipped"] or len(preview["items"]) != len(items):
        frappe.throw("انتخاب‌ها تغییر کرده‌اند؛ پیش‌نمایش تازه بگیرید")
    documents = []
    for row in sorted(items, key=lambda r: r["name"]):
        doc = locked_review(row["name"])
        if (
            str(doc.modified) != str(row["modified"])
            or doc.status != "Pending"
            or doc.domain != domain
            or doc.employee == reviewer
        ):
            frappe.throw("یکی از موارد تغییر کرده است؛ هیچ واگذاری انجام نشد. پیش‌نمایش تازه بگیرید")
        documents.append(doc)
    for doc in documents:
        doc.reviewer = reviewer
        save_review(doc)
        doc.add_comment(
            "Info",
            "واگذاری گروهی بررسی توسط "
            + display_name(frappe.session.user)
            + " به "
            + display_name(reviewer),
        )
    return {
        "count": len(documents),
        "message": "بررسی موارد انتخاب‌شده واگذار شد؛ مسئول انجام کار و تأییدهای قبلی تغییر نکردند.",
    }


def delegation_validate(doc, method=None):
    if not doc.flags.portal_delegation_internal:
        frappe.throw("واگذاری فقط از صفحه بررسی فعالیت‌ها مجاز است", frappe.PermissionError)


@frappe.whitelist(methods=["POST"])
def delegate_inventory(reviewer, start_date, end_date=None):
    signed_in()
    user = frappe.session.user
    if not (leadership(user) or "inventory" in managed_domains(user)):
        frappe.throw("فقط مدیر مجاز می‌تواند واگذار کند", frappe.PermissionError)
    if not frappe.db.exists("User", {"name": reviewer, "enabled": 1, "user_type": "System User"}):
        frappe.throw("بررسی‌کننده فعال را انتخاب کنید")
    start = getdate(start_date)
    end = getdate(end_date) if end_date else None
    if end and end < start:
        frappe.throw("پایان واگذاری قبل از شروع است")
    frappe.db.get_value("Portal Domain", "inventory", "name", for_update=True)
    for row in frappe.get_all(
        "Portal Review Delegation",
        filters={"domain": "inventory", "enabled": 1},
        fields=["name", "start_date", "end_date"],
    ):
        if (not row.end_date or start <= getdate(row.end_date)) and (
            not end or getdate(row.start_date) <= end
        ):
            frappe.throw("برای این بازه واگذاری فعال وجود دارد؛ ابتدا آن را پایان دهید")
    doc = frappe.get_doc(
        dict(
            doctype="Portal Review Delegation",
            domain="inventory",
            reviewer=reviewer,
            start_date=start,
            end_date=end,
            enabled=1,
        )
    )
    doc.flags.portal_delegation_internal = True
    doc.insert(ignore_permissions=True)
    doc.add_comment(
        "Info",
        "واگذاری بررسی گزارش‌های کنترل انبار توسط "
        + display_name(user)
        + " به "
        + display_name(reviewer),
    )
    return "واگذاری ثبت شد؛ گزارش‌های موجود و آینده در بازه تعیین‌شده پوشش داده می‌شوند. تأییدهای قبلی حفظ شدند."


@frappe.whitelist(methods=["POST"])
def revoke_delegation(name, expected_modified):
    signed_in()
    user = frappe.session.user
    doc = frappe.get_doc("Portal Review Delegation", name)
    if not (leadership(user) or doc.domain in managed_domains(user)):
        frappe.throw("اجازه پایان واگذاری ندارید", frappe.PermissionError)
    frappe.db.get_value("Portal Domain", doc.domain, "name", for_update=True)
    doc.reload()
    if str(doc.modified) != str(expected_modified):
        frappe.throw("اطلاعات تغییر کرده؛ صفحه را تازه کنید")
    doc.enabled = 0
    doc.flags.portal_delegation_internal = True
    doc.save(ignore_permissions=True)
    doc.add_comment("Info", "پایان واگذاری توسط " + display_name(user))
    return "واگذاری پایان یافت؛ تأییدها و سوابق حفظ شدند."
