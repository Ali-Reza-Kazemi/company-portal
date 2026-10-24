"""Recurring inventory responsibilities, immutable evidence and period dashboards."""

import hashlib
import json
import uuid
from datetime import timedelta

import frappe
from frappe.utils import get_datetime, getdate, now_datetime, today

from . import workflow_data, workflow_storage
from . import workflow_math as math
from . import workflow_sources as source
from .calculations import (
    key,
    number,
    text,
)
from .service import allowed, read_snapshot, require_access, storage, write_snapshot
from .sources import json_default

KINDS = {"Weekly": "هفتگی", "Monthly": "ماهانه", "Cash": "نیاز نقدینگی"}


def metric_name(code, policy=None):
    return "INV-M-" + hashlib.sha256((policy or math.POLICY).encode()).hexdigest()[:8] + "-" + code


PLAN = {
    "cancel": (
        "Weekly",
        "بررسی و تأیید درصد کنسلی ناشی از نبود کالا",
        "تعداد درخواست‌های تعیین‌تکلیف‌شده و کنسل‌شده دیدار به علت دقیق نبود کالا را بررسی و گزارش هفته قبل را ارسال کنید.",
    ),
    "capital": (
        "Monthly",
        "بررسی نقدینگی حبس‌شده در موجودی",
        "ارزش موجودی پایان ماه قبل به قیمت رسمی فروش، پوشش قیمت و موجودی منفی را کنترل و تأیید کنید.",
    ),
    "slow": (
        "Monthly",
        "بررسی ارزش ریالی کالاهای راکد و کندگردش",
        "کل ارزش موجودی مشمول قواعد رسوب را بررسی کنید؛ این مبلغ با ارزش مازاد پوشش متفاوت است.",
    ),
    "turnover": (
        "Monthly",
        "بررسی گردش سالانه موجودی",
        "گردش تعدادی ۱۲ماهه و متوسط ۱۲ موجودی پایان ماه شمسی را بررسی کنید.",
    ),
    "forecast": (
        "Monthly",
        "ثبت پیش‌بینی فروش ماه آینده",
        "دقت پیش‌بینی قفل‌شده پیش از ماه را بررسی و پیش‌بینی شش گروه برای ماه آینده را پیش از شروع آن ثبت کنید.",
    ),
    "variance": (
        "Semiannual",
        "ثبت نتیجه شمارش واقعی انبار",
        "شمارش واقعی را در کنار موجودی دفتری ثبت‌شده هنگام شمارش ثبت کنید؛ درصد فقط از اقلام واقعاً شمارش‌شده محاسبه می‌شود.",
    ),
    "urgency": (
        "Monthly",
        "تصمیم و اقدام خرید اقلام نیازمند تأمین",
        "پیشنهاد زمان سفارش، پوشش موجودی، زمان تأمین، موجودی در راه و اقلام فوری را در گزارش نقدینگی بررسی کنید.",
    ),
    "cash": (
        "Monthly",
        "بررسی نقدینگی شش گروه کالا و کل موجودی راکد",
        "گروه‌های مته و گردبر، انواع دریل، پخ‌زن دستی، پخ‌زن اتومات، قطعات یدکی دریل و پخ‌زن؛ برآورد به قیمت رسمی فروش و واحد تومان است.",
    ),
}


def owner():
    configured = frappe.conf.get("inventory_reporting_owner")
    if configured:
        if configured != "Guest" and frappe.db.exists(
            "User", {"name": configured, "enabled": 1, "user_type": "System User"}
        ):
            return configured
        frappe.throw("مسئول پایش تنظیم‌شده باید کاربر فعال سامانه باشد")
    # Compatibility for existing sites: infer only from the established plan,
    # never from a person's display name or an arbitrary unit member.
    matches = set(
        frappe.get_all(
            "Portal Template",
            filters={
                "name": [
                    "in",
                    ["INVPLAN-forecast", "INVPLAN-variance", "INVPLAN-urgency"],
                ],
                "domain": "inventory",
            },
            pluck="responsible",
        )
    ) - {None, "", "Guest"}
    matches = [
        user
        for user in matches
        if frappe.db.exists("User", {"name": user, "enabled": 1, "user_type": "System User"})
    ]
    if len(matches) != 1:
        frappe.throw("مسئول پایش موجودی باید در تنظیمات سایت مشخص شود")
    return matches[0]


def can_input():
    from saeenaria_portal.permissions import admin

    return frappe.session.user != "Guest" and (
        admin(frappe.session.user) or frappe.session.user == owner()
    )


def require_input():
    require_access()
    if not can_input():
        frappe.throw(
            "ثبت و ارسال این برنامه فقط برای مسئول تعیین‌شده و مدیریت مجاز است",
            frappe.PermissionError,
        )


def snapshot_permission(doc, user=None, permission_type=None):
    return (
        permission_type in (None, "read", "select", "print", "export")
        and doc.domain == "inventory"
        and allowed(user)
    )


def snapshot_query(user=None):
    return "`tabPortal Inventory Snapshot`.`domain`='inventory'" if allowed(user) else "1=0"


def settings_bundle():
    return workflow_data.settings_bundle()


def existing_forecast(start, end):
    records = frappe.get_all(
        "Portal Record",
        filters={
            "domain": "inventory",
            "record_type": "Demand Forecast",
            "period_start": start,
            "period_end": end,
            "locked": 1,
            "is_demo": 0,
        },
        fields=["name", "creation", "quantity", "baseline_snapshot"],
        order_by="creation desc",
    )
    batches = {}
    for r in records:
        if getdate(r.creation) >= start:
            continue
        try:
            info = json.loads(r.baseline_snapshot or "{}")
        except ValueError:
            continue
        if info.get("policy") != math.POLICY or info.get("group") not in math.GROUPS:
            continue
        batches.setdefault(info["batch"], {})[info["group"]] = number(r.quantity)
    return next((v for v in batches.values() if set(v) == set(math.GROUPS)), {})


def operational_metrics(start, end):
    return workflow_data.operational_metrics(start=start, end=end)


def weekly_payload(start, end, reconstructed=False):
    return workflow_data.weekly_payload(start=start, end=end, reconstructed=reconstructed)


def capture_weekly_history(weeks=12):
    """Reconstruct missing complete weeks from current CRM; never rewrite frozen versions."""
    start, end = math.previous_week(getdate(today()))
    for offset in range(1, weeks):
        first, last = start - timedelta(weeks=offset), end - timedelta(weeks=offset)
        if not frappe.db.exists(
            "Portal Inventory Snapshot",
            {
                "kind": "Weekly",
                "period_start": first,
                "period_end": last,
                "policy": math.POLICY,
            },
        ):
            save_payload(weekly_payload(first, last, reconstructed=True))


def build_payload(kind):
    return workflow_data.build_payload(kind=kind)


def latest(kind):
    return workflow_storage.latest(kind=kind)


def save_payload(payload):
    return workflow_storage.save_payload(payload=payload)


def publish_values(snapshot):
    return workflow_storage.publish_values(snapshot=snapshot)


def capture_all(wait=False):
    """Job entry; each kind commits separately and has its own failure indicator."""
    from filelock import FileLock, Timeout

    folder = storage()
    folder.mkdir(parents=True, exist_ok=True)
    try:
        with FileLock(str(folder / "workflow.lock"), timeout=1800 if wait else 0):
            original = frappe.session.user
            frappe.set_user("Administrator")
            status = {"running": True, "started_at": str(now_datetime()), "errors": {}}
            write_snapshot("workflow-state", status)
            try:
                for kind in ("Weekly", "Cash", "Monthly"):
                    try:
                        snapshot = save_payload(build_payload(kind))
                        publish_values(snapshot)
                        if kind == "Weekly":
                            capture_weekly_history()
                        if kind == "Cash":
                            detect_stockout(snapshot)
                        frappe.db.commit()
                        status[kind] = snapshot.name
                    except Exception as exc:
                        frappe.db.rollback()
                        status["errors"][kind] = type(exc).__name__
                    write_snapshot("workflow-state", status)
            finally:
                status["running"] = False
                status["finished_at"] = str(now_datetime())
                write_snapshot("workflow-state", status)
                frappe.set_user(original)
    except Timeout:
        return


def enqueue_daily():
    if frappe.db.exists("Portal Template", "INVPLAN-cancel"):
        frappe.enqueue(
            "saeenaria_portal.purchase_reports.workflow.capture_all",
            queue="long",
            timeout=1800,
            job_id="inventory-workflow:" + frappe.local.site,
            deduplicate=True,
        )


@frappe.whitelist(methods=["POST"])
def refresh():
    require_access()
    if not frappe.db.exists("Portal Template", "INVPLAN-cancel"):
        frappe.throw("برنامه پایش هنوز راه‌اندازی نشده است")
    enqueue_daily()
    return {"queued": True}


@frappe.whitelist()
def status():
    require_access()
    return read_snapshot("workflow-state")


def public_snapshot(doc):
    return workflow_storage.public_snapshot(doc=doc)


def detect_stockout(snapshot):
    payload = json.loads(snapshot.payload)
    previous = read_snapshot("workflow-stock-baseline")
    current = {r["code"]: r for r in payload["evidence"].get("reference_stock", [])}
    mapping = payload["evidence"]["mapping"]
    for code, value in current.items():
        old = previous.get("values", {}).get(code)
        if (
            not old
            or number(old["quantity"]) <= 0
            or number(value["quantity"]) > 0
            or number(value["avg"]) <= 0
        ):
            continue
        if frappe.db.exists(
            "Portal Record",
            {
                "domain": "inventory",
                "channel": "inventory-monitoring",
                "record_type": "Supply Request",
                "item_code": code,
                "status": "Open",
            },
        ):
            continue
        accepted = [r["ItemCode"] for r in mapping if key(r["EffectiveReference"]) == key(code)]
        info = {
            "policy": math.POLICY,
            "observed_transition": True,
            "prior_snapshot": previous.get("snapshot"),
            "snapshot": snapshot.name,
            "acceptable_codes": accepted,
        }
        external = (
            "inventory-auto-alarm:" + hashlib.sha256((snapshot.name + code).encode()).hexdigest()
        )
        if frappe.db.exists("Portal Record", {"external_id": external}):
            continue
        frappe.get_doc(
            dict(
                doctype="Portal Record",
                domain="inventory",
                title="آلارم خودکار اتمام موجودی گروه: " + code,
                record_type="Supply Request",
                external_id=external,
                record_date=today(),
                responsible=owner(),
                channel="inventory-monitoring",
                item_code=code,
                planned_at=now_datetime(),
                status="Open",
                quantity=0,
                baseline_snapshot=json.dumps(info),
                is_demo=0,
            )
        ).insert(ignore_permissions=True)
    # Private observation state is a cache; immutable evidence remains in the DB.
    frappe.db.after_commit.add(
        lambda: write_snapshot(
            "workflow-stock-baseline", {"snapshot": snapshot.name, "values": current}
        )
    )


@frappe.whitelist()
def overview(kind="Weekly", snapshot=None):
    require_access()
    if kind not in KINDS:
        frappe.throw("نوع گزارش نامعتبر است")
    if snapshot:
        doc = frappe.get_doc("Portal Inventory Snapshot", snapshot)
        if doc.kind != kind or doc.domain != "inventory":
            frappe.throw("نسخه نامعتبر است")
    else:
        doc = latest(kind)
    history = frappe.get_all(
        "Portal Inventory Snapshot",
        filters={"kind": kind, "policy": math.POLICY},
        fields=[
            "name",
            "period_start",
            "period_end",
            "revision",
            "captured_at",
            "metrics_json",
        ],
        order_by="period_end desc,captured_at desc",
        limit_page_length=200,
    )
    series = []
    seen = set()
    for h in history:
        period = (str(h.period_start), str(h.period_end))
        if period in seen:
            continue
        seen.add(period)
        values = json.loads(h.metrics_json or "[]")
        series.append(
            {
                "period": h.period_end,
                "policy": math.POLICY,
                "values": [
                    {
                        "code": v["code"],
                        "value": v["value"],
                        "unit": v["unit"],
                        "status": v["status"],
                    }
                    for v in values
                ],
            }
        )
    for h in history:
        h.pop("metrics_json", None)
    cash = latest("Cash")
    cash_payload = json.loads(cash.payload) if cash else {}
    next_start, next_end = math.month_bounds(
        math.month_bounds(getdate(today()))[1] + timedelta(days=1)
    )
    stocks = {
        str(r["StockId"]): r["StockTitle"]
        for r in cash_payload.get("evidence", {}).get("inventory", [])
    }
    return {
        "snapshot": public_snapshot(doc),
        "history": history,
        "series": list(reversed(series)),
        "state": read_snapshot("workflow-state"),
        "can_input": can_input(),
        "groups": math.GROUPS,
        "stocks": stocks,
        "forecast": {
            "start": next_start,
            "end": next_end,
            "suggestions": cash_payload.get("forecast_suggestions", {}),
            "saved": existing_forecast(next_start, next_end),
            "method": cash_payload.get("forecast_method", {}),
            "locked": bool(existing_forecast(next_start, next_end)),
        },
        "events": frappe.get_all(
            "Portal Record",
            filters={
                "domain": "inventory",
                "channel": "inventory-monitoring",
                "is_demo": 0,
            },
            fields=[
                "name",
                "title",
                "record_type",
                "item_code",
                "quantity",
                "planned_at",
                "actual_at",
                "status",
                "modified",
                "baseline_snapshot",
            ],
            order_by="creation desc",
            limit_page_length=100,
        ),
    }


@frappe.whitelist(methods=["POST"])
def freeze_forecast(values):
    require_input()
    values = frappe.parse_json(values)
    if not isinstance(values, dict) or set(values) != set(math.GROUPS):
        frappe.throw("پیش‌بینی هر شش گروه لازم است")
    if any(v in (None, "") for v in values.values()):
        frappe.throw("برای همه گروه‌ها مقدار مشخص وارد کنید؛ صفر مجاز است")
    start, end = math.month_bounds(math.month_bounds(getdate(today()))[1] + timedelta(days=1))
    numbers = {k: number(v) for k, v in values.items()}
    if any(not v.is_finite() or v < 0 for v in numbers.values()):
        frappe.throw("پیش‌بینی باید عدد نامنفی باشد")
    batch = uuid.uuid4().hex
    for group, value in numbers.items():
        frappe.get_doc(
            dict(
                doctype="Portal Record",
                domain="inventory",
                title="پیش‌بینی " + math.GROUPS[group],
                record_type="Demand Forecast",
                external_id="inventory-forecast:" + batch + ":" + group,
                record_date=today(),
                period_start=start,
                period_end=end,
                responsible=owner(),
                channel="inventory-monitoring",
                item_code=group,
                quantity=float(value),
                baseline_snapshot=json.dumps(
                    {"policy": math.POLICY, "batch": batch, "group": group}
                ),
                is_demo=0,
            )
        ).insert(ignore_permissions=True)
    action_name = frappe.db.get_value(
        "Portal Action",
        {
            "responsible": owner(),
            "schedule_key": "INVPLAN-forecast:" + start.isoformat(),
            "status": ["not in", ["Completed", "Cancelled"]],
        },
        "name",
    )
    if action_name:
        action = frappe.get_doc("Portal Action", action_name)
        action.status = "Completed"
        action.progress = 100
        action.result = "نسخه کامل پیش‌بینی شش گروه پیش از شروع دوره ثبت و قفل شد"
        action.save(ignore_permissions=True)
    return {"locked": True, "start": start, "end": end}


@frappe.whitelist(methods=["POST"])
def save_event(kind, item_code, stock=None, quantity=None, alarm_at=None):
    require_input()
    item_code = text(item_code)
    if not item_code or len(item_code) > 100:
        frappe.throw("کد کالا لازم است")
    info = {"policy": math.POLICY}
    data = dict(
        doctype="Portal Record",
        domain="inventory",
        external_id="inventory-event:" + uuid.uuid4().hex,
        record_date=today(),
        responsible=owner(),
        channel="inventory-monitoring",
        item_code=item_code,
        is_demo=0,
    )
    if kind == "alarm":
        if not source.item_exists(item_code):
            frappe.throw("کد کالا در سپیدار یافت نشد")
        stamp = get_datetime(alarm_at or now_datetime())
        if stamp > now_datetime():
            frappe.throw("زمان آلارم نمی‌تواند در آینده باشد")
        data.update(
            title="آلارم اتمام کالا: " + item_code,
            record_type="Supply Request",
            planned_at=stamp,
            status="Open",
            quantity=0,
        )
    elif kind == "count":
        counted = number(quantity)
        if not counted.is_finite() or counted < 0 or not stock:
            frappe.throw("انبار و تعداد شمارش معتبر لازم است")
        book = source.current_book(item_code, int(stock))
        if not book or book[0]["quantity"] is None:
            frappe.throw("موجودی دفتری برای این کالا و انبار یافت نشد")
        info.update(
            stock=int(stock),
            book=str(book[0]["quantity"]),
            book_captured_at=str(now_datetime()),
        )
        data.update(
            title="شمارش موجودی: " + item_code,
            record_type="Stock Count",
            quantity=float(counted),
            locked=1,
            status="Counted",
        )
    else:
        frappe.throw("نوع رویداد نامعتبر است")
    data["baseline_snapshot"] = json.dumps(info)
    doc = frappe.get_doc(data).insert(ignore_permissions=True)
    return {"name": doc.name}


@frappe.whitelist()
def receipts(record):
    require_input()
    doc = frappe.get_doc("Portal Record", record)
    if (
        doc.domain != "inventory"
        or doc.channel != "inventory-monitoring"
        or doc.record_type != "Supply Request"
    ):
        frappe.throw("آلارم نامعتبر است")
    info = json.loads(doc.baseline_snapshot or "{}")
    return source.receipt_options(info.get("acceptable_codes") or doc.item_code, doc.planned_at)


@frappe.whitelist(methods=["POST"])
def link_receipt(record, receipt_item, expected_modified):
    require_input()
    doc = frappe.get_doc("Portal Record", record)
    if get_datetime(doc.modified) != get_datetime(expected_modified):
        frappe.throw("رویداد تغییر کرده است؛ صفحه را تازه کنید", frappe.TimestampMismatchError)
    options = receipts(record)
    match = next((r for r in options if str(r["receipt_item"]) == str(receipt_item)), None)
    if not match:
        frappe.throw("رسید معتبر و منطبق با کالا و زمان آلارم یافت نشد")
    info = json.loads(doc.baseline_snapshot or "{}")
    info["receipt"] = match
    info["receipt_date_precision"] = "day"
    doc.actual_at = match["receipt_date"]
    doc.status = "Received"
    doc.locked = 1
    doc.baseline_snapshot = json.dumps(info, default=json_default)
    doc.save(ignore_permissions=True)
    return {"name": doc.name}


def report_metric_snapshot(name):
    return workflow_storage.report_metric_snapshot(name=name)


@frappe.whitelist()
def evidence(snapshot, page=1, search="", scope="all"):
    require_access()
    doc = frappe.get_doc("Portal Inventory Snapshot", snapshot)
    if doc.domain != "inventory":
        frappe.throw("نسخه نامعتبر است")
    data = json.loads(doc.payload).get("evidence", {})
    records = data.get("deals", []) if doc.kind == "Weekly" else data.get("inventory", [])
    if doc.kind == "Weekly":
        records = [
            r for r in records if int(r["state"]) == 2 and text(r.get("reason")) == "نبود کالا"
        ]
    query = text(search).casefold()
    records = [
        r for r in records if not query or query in " ".join(text(v) for v in r.values()).casefold()
    ]
    page = max(1, frappe.utils.cint(page))
    return {
        "rows": records[(page - 1) * 50 : page * 50],
        "total": len(records),
        "weekly": doc.kind == "Weekly",
    }


@frappe.whitelist(methods=["POST"])
def submit(snapshot, note=""):
    require_access()
    frappe.throw("گزارش‌های این صفحه خودکارند و به ارسال، بررسی یا تأیید انسانی نیاز ندارند")
