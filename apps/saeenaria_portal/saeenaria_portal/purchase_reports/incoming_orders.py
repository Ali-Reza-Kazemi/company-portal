"""Portal-owned remaining incoming quantities; all writes are authorized and audited."""

from decimal import Decimal, InvalidOperation
from uuid import uuid4

import frappe
from frappe.utils import cint, get_datetime, getdate

from .product_catalog import DT as CATALOG
from .product_catalog import can_edit, require_edit
from .service import require_access

DT = "Portal Incoming Order"
FIELDS = [
    "name",
    "order_key",
    "order_number",
    "reference_code",
    "quantity",
    "status",
    "expected_date",
    "supplier",
    "notes",
    "modified",
]
EDITABLE = set(FIELDS) - {"name", "modified", "order_key"}


def ensure_order_key(doc):
    if not doc.order_key:
        doc.order_key = "IN-" + uuid4().hex


def validate_document(doc):
    require_edit()
    ensure_order_key(doc)
    previous = doc.get_doc_before_save()
    if previous and doc.order_key != previous.order_key:
        frappe.throw("شناسه ردیف سفارش قابل تغییر نیست")
    for field, limit in (
        ("order_key", 140),
        ("order_number", 140),
        ("supplier", 140),
        ("notes", 2000),
    ):
        value = str(doc.get(field) or "").strip()
        if len(value) > limit or (field == "order_key" and not value):
            frappe.throw("شناسه و مشخصات سفارش معتبر لازم است")
        doc.set(field, value)
    if doc.status not in ("Active", "Received", "Cancelled"):
        frappe.throw("وضعیت سفارش نامعتبر است")
    try:
        if isinstance(doc.quantity, bool):
            raise ValueError()
        quantity = Decimal(str(doc.quantity))
        if (
            not quantity.is_finite()
            or quantity < 0
            or quantity > 1_000_000_000
            or quantity.as_tuple().exponent < -9
        ):
            raise ValueError()
        if doc.status == "Active" and quantity == 0:
            raise ValueError()
    except (ValueError, InvalidOperation, TypeError):
        frappe.throw("تعداد باقی‌مانده سفارش فعال باید عدد مثبت و معتبر باشد")
    ref = frappe.db.get_value(
        CATALOG,
        doc.reference_code,
        ["item_code", "reference_code", "needs_completion", "source_conflict"],
        as_dict=True,
    )
    if (
        not ref
        or ref.item_code != ref.reference_code
        or ref.needs_completion
        or ref.source_conflict
    ):
        frappe.throw("یک کالای مرجع تکمیل‌شده و بدون تعارض انتخاب کنید")
    doc.reference_code = ref.item_code
    if doc.expected_date:
        doc.expected_date = getdate(doc.expected_date)


def rows():
    if not frappe.db.exists("DocType", DT):
        frappe.throw("ساختار سفارش‌های در راه نصب نشده است؛ ارتقای پورتال را اجرا کنید")
    return [
        {"کد مرجع": row.reference_code, "تعداد در راه": row.quantity, "وضعیت": "فعال"}
        for row in frappe.get_all(
            DT,
            filters={"status": "Active"},
            fields=["reference_code", "quantity"],
            limit_page_length=0,
        )
    ]


@frappe.whitelist()
def overview(search="", status="Active", page=1):
    require_access()
    if status not in ("all", "Active", "Received", "Cancelled"):
        frappe.throw("وضعیت سفارش نامعتبر است")
    filters = {} if status == "all" else {"status": status}
    search = str(search or "").strip()[:140]
    or_filters = (
        {
            field: ["like", "%" + search + "%"]
            for field in ("order_key", "order_number", "reference_code", "supplier")
        }
        if search
        else None
    )
    total = frappe.get_all(
        DT, filters=filters, or_filters=or_filters, fields=[{"COUNT": "name", "as": "matches"}]
    )[0].matches
    pages = max(1, (total + 49) // 50)
    page = min(max(1, cint(page)), pages)
    records = frappe.get_all(
        DT,
        filters=filters,
        or_filters=or_filters,
        fields=FIELDS,
        order_by="modified desc,name",
        start=(page - 1) * 50,
        limit_page_length=50,
    )
    return {"rows": records, "total": total, "page": page, "pages": pages, "can_edit": can_edit()}


@frappe.whitelist(methods=["POST"])
def save(data, expected_modified=None):
    require_edit()
    data = frappe.parse_json(data)
    if isinstance(data, dict) and "expected_date_jalali" in data:
        from .incoming_excel import jalali_date

        data = dict(data)
        data["expected_date"] = jalali_date(data.pop("expected_date_jalali"))
    if not isinstance(data, dict) or set(data) - EDITABLE - {"name"}:
        frappe.throw("اطلاعات سفارش نامعتبر است")
    if "quantity" in data:
        try:
            quantity = Decimal(str(data["quantity"]))
            if (
                isinstance(data["quantity"], bool)
                or not quantity.is_finite()
                or quantity < 0
                or quantity > 1_000_000_000
                or quantity.as_tuple().exponent < -9
            ):
                raise ValueError()
        except (ValueError, InvalidOperation, TypeError):
            frappe.throw("تعداد سفارش نامعتبر است")
    if data.get("name"):
        frappe.db.get_value(DT, data["name"], "name", for_update=True)
        doc = frappe.get_doc(DT, data["name"])
        if not expected_modified or get_datetime(expected_modified) != get_datetime(doc.modified):
            frappe.throw("سفارش تغییر کرده است؛ فهرست را تازه کنید", frappe.TimestampMismatchError)
    else:
        doc = frappe.new_doc(DT)
    doc.update({key: value for key, value in data.items() if key in EDITABLE})
    doc.save(ignore_permissions=True)
    enqueue_recalculation()
    return {"name": doc.name, "modified": doc.modified}


def enqueue_recalculation():
    frappe.enqueue(
        "saeenaria_portal.purchase_reports.general_settings.recalculate",
        queue="long",
        timeout=5400,
        job_id="purchase-incoming:" + frappe.local.site + ":" + uuid4().hex,
        deduplicate=True,
        enqueue_after_commit=True,
        revision=None,
    )


@frappe.whitelist(methods=["POST"])
def bulk_status(selections, status):
    require_edit()
    selections = frappe.parse_json(selections)
    if (
        status not in ("Active", "Received", "Cancelled")
        or not isinstance(selections, list)
        or not 1 <= len(selections) <= 1000
    ):
        frappe.throw("ردیف‌ها و وضعیت معتبر را انتخاب کنید")
    if any(
        not isinstance(row, dict)
        or set(row) != {"name", "modified"}
        or not isinstance(row["name"], str)
        or not row["name"]
        or not row["modified"]
        for row in selections
    ):
        frappe.throw("انتخاب سفارش نامعتبر است")
    if len({row["name"] for row in selections}) != len(selections):
        frappe.throw("سفارش تکراری انتخاب شده است")
    frappe.db.savepoint("incoming_bulk")
    try:
        docs = []
        for row in sorted(selections, key=lambda row: row["name"]):
            frappe.db.get_value(DT, row["name"], "name", for_update=True)
            doc = frappe.get_doc(DT, row["name"])
            if get_datetime(row["modified"]) != get_datetime(doc.modified):
                frappe.throw(
                    "یکی از سفارش‌ها تغییر کرده است؛ فهرست را تازه کنید",
                    frappe.TimestampMismatchError,
                )
            docs.append(doc)
        changed = 0
        for doc in docs:
            if doc.status != status:
                doc.status = status
                doc.save(ignore_permissions=True)
                changed += 1
        if changed:
            enqueue_recalculation()
        return {"updated": changed}
    except Exception:
        frappe.db.rollback(save_point="incoming_bulk")
        raise
