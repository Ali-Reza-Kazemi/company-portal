"""Permission-scoped report snapshots, filters, aggregate metrics and CSV export."""
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
import csv
import io
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import urlencode

import frappe
from frappe.rate_limiter import rate_limit
from saeenaria_portal.csv_safety import safe_csv_cell
from .calculations import calculate, number, ratio, text, total, is_service_item
from .catalog import LABELS, METRICS, REPORTS
from .sources import credentials, extract_sqlserver, json_default


def allowed(user=None):
    from saeenaria_portal.permissions import admin, roles, managed_domains
    user = user or frappe.session.user
    if user == "Guest":
        return False
    domain = frappe.conf.get("purchase_order_domain") or "inventory"
    viewers = frappe.conf.get("purchase_order_viewers") or []
    explicit_viewer = isinstance(viewers, list) and user in viewers
    return explicit_viewer or admin(user) or "Company Director" in roles(user) or domain in managed_domains(user)


def require_access():
    if not allowed():
        frappe.throw("گزارش‌های خرید و موجودی فقط برای مدیر شرکت و مدیر مجاز برنامه‌ریزی و کنترل موجودی در دسترس است", frappe.PermissionError)


def storage():
    return Path(frappe.get_site_path("private", "purchase_reports"))


def read_snapshot(name):
    path = storage() / (name + ".json")
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def write_snapshot(name, content):
    folder = storage()
    folder.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=folder, prefix=".snapshot-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(content, stream, ensure_ascii=False, default=json_default)
        os.replace(temp, folder / (name + ".json"))
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    if name == "combined" and "reports" in content:
        write_snapshot(name + "-meta", {k: v for k, v in content.items() if k != "reports"} | {
            "report_counts": {report: len(rows) for report, rows in content["reports"].items()}})


def refresh_data(wait=False):
    """Internal worker entry point, never whitelisted. Preserve prior data on failure."""
    from filelock import FileLock, Timeout
    folder = storage()
    folder.mkdir(parents=True, exist_ok=True)
    try:
        with FileLock(str(folder / "refresh.lock"), timeout=1800 if wait else 0):
            now = datetime.now(timezone.utc).isoformat()
            state = {"running": True, "started_at": now, "errors": {}}
            write_snapshot("state", state)
            try:
                from . import general_settings, product_catalog
                from .native_analytics import build_reports
                from .portal_inputs import read_inputs
                config = credentials()
                sql = extract_sqlserver(config)
                if product_catalog.active():
                    product_catalog.sync_items(sql["SepidarItems"])
                else:
                    product_catalog.initialize(sql["SepidarItems"])
                if not general_settings.active():
                    general_settings.initialize()
                frappe.db.commit()
                inputs = read_inputs()
                asof=frappe.utils.getdate(frappe.utils.today())
                reports = calculate(inputs["ProductMapping"],inputs["IncomingOrders"],inputs["GeneralSettings"],
                    sql["FactInventory"],sql["FactSales"],sql["FactMonthlyInventory"],sql["SepidarItems"],today=asof)
                reports.update(build_reports(inputs["ProductMapping"],inputs["GeneralSettings"],
                    sql["FactInventory"],sql["FactSales"],reports,asof))
                finished=datetime.now(timezone.utc).isoformat()
                write_snapshot("combined",{"updated_at":now,"reports":reports,"settings_at":inputs["metadata"],
                    "processor":"portal-native-v2","source_run":[{"processor":"portal-native-v2","finished_at":finished,"run_status":"succeeded"}]})
            except Exception as exc:
                frappe.db.rollback()
                # Never publish partial reports or credentials from driver exceptions.
                state["errors"]["portal"] = type(exc).__name__
            finally:
                state["running"] = False
                state["finished_at"] = datetime.now(timezone.utc).isoformat()
                write_snapshot("state", state)
    except Timeout:
        return
    finally:
        # Covers failures before the state finalizer.
        if "state" in locals() and state.get("running"):
            state["running"] = False
            state["finished_at"] = datetime.now(timezone.utc).isoformat()
            write_snapshot("state", state)


def auto_refresh():
    if frappe.conf.get("purchase_order_auto_refresh") and Path(frappe.get_site_path("private", "purchase-order-connections.json")).exists():
        _enqueue()


def _enqueue():
    frappe.enqueue("saeenaria_portal.purchase_reports.service.refresh_data", queue="long", timeout=1800,
                   job_id="purchase-reports:" + frappe.local.site, deduplicate=True)


@frappe.whitelist(methods=["POST"])
@rate_limit(limit=3, seconds=60)
def refresh():
    require_access()
    if not credentials().get("sqlserver"):
        frappe.throw("اطلاعات اتصال منابع هنوز روی سایت تنظیم نشده است")
    _enqueue()
    return {"queued": True}


@frappe.whitelist()
def overview():
    require_access()
    result = []
    families = {}
    for name, report in REPORTS.items():
        if name == "reconcile":
            continue
        family = "combined"
        if family not in families:
            families[family] = read_snapshot(family + "-meta") or read_snapshot(family)
        snapshot = families[family]
        result.append({"name": name, "title": report["title"], "available": name in snapshot.get("report_counts", snapshot.get("reports", {})),
                       "updated_at": snapshot.get("updated_at")})
    return {"reports": result, "configured": bool(credentials().get("sqlserver")), "state": read_snapshot("state")}


def parse_filters(filters):
    filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
    if not isinstance(filters, dict):
        frappe.throw("فیلتر نامعتبر است")
    return {k: text(v) for k, v in filters.items() if k in (
        "StockTitle", "Category", "ExpertGroup", "CustomerTemperature", "MismatchSide", "WeekStart", "search") and v not in (None, "")}


def filtered_rows(name, filters):
    if name not in REPORTS:
        frappe.throw("گزارش نامعتبر است")
    filters = parse_filters(filters)
    snapshot = read_snapshot("combined")
    if name not in snapshot.get("reports", {}):
        return [], snapshot, {}, False
    source = snapshot["reports"][name]
    if name == "weekly":
        source = [row for row in source if "قطعات یدکی" not in " ".join(text(row.get("Category")).replace("\u200c", " ").split())]
    options = {f: sorted({str(r[f]) for r in source if r.get(f) not in (None, "")}) for f in (
        "StockTitle", "Category", "ExpertGroup", "CustomerTemperature", "MismatchSide", "WeekStart") if any(f in r for r in source)}
    result = []
    for row in source:
        if name == "orders" and is_service_item(row.get("ItemTitle")):
            continue
        if name == "orders" and number(row.get("SuggestedOrderQty")) == 0:
            continue
        if name == "orders" and row.get("StockTitle") != filters.get("StockTitle", "همه انبارها"):
            continue
        if any(str(row.get(f, "")) != v for f, v in filters.items() if f != "search"):
            continue
        query = filters.get("search", "").casefold()
        if query and query not in " ".join(text(row.get(f)) for f in REPORTS[name]["fields"]).casefold():
            continue
        result.append(row)
    return result, snapshot, options, True


def metrics(name, rows):
    result = []
    for ident, label, operation, field in METRICS[name]:
        if operation == "count": value = len(rows)
        elif operation == "references": value = sum(text(r.get("ItemCode")).casefold() == text(r.get("EffectiveReference")).casefold() for r in rows)
        elif operation == "sum": value = total(rows, field)
        elif operation == "positive": value = sum(number(r.get(field)) > 0 for r in rows)
        elif operation == "missing": value = sum(r.get(field) is None or number(r.get(field)) <= 0 for r in rows)
        elif operation == "distinct": value = len({r[field] for r in rows if r.get(field) is not None})
        elif operation == "side": value = sum(r.get("MismatchSide") == field for r in rows)
        elif operation == "excess":
            unique = {}
            for r in rows:
                k = (r.get("StockId"), r.get("ReferenceCode"))
                if r.get(field) is not None:
                    unique[k] = max(unique.get(k, Decimal(0)), number(r[field]))
            value = sum(unique.values(), Decimal(0)) if unique else None
        else:
            rate = ratio(total(rows, "NetSalesQty12M") or Decimal(0), total(rows, "AverageInventoryQty12M"))
            value = ratio(Decimal(365), rate) if operation == "days" else rate
        result.append({"name": ident, "label": label, "value": value})
    return result


def groups(name, rows):
    dimension = "ExpertGroup" if name == "weekly" else "MismatchSide" if name == "reconcile" else "Category"
    buckets = defaultdict(list)
    for row in rows:
        buckets[text(row.get(dimension)) or "بدون دسته‌بندی"].append(row)
    return [{"label": label, "metrics": metrics(name, subset)} for label, subset in sorted(buckets.items())]


def catalog_search_context(name, filters, snapshot):
    """Explain a known catalog item missing from these deliberately limited reports."""
    query = parse_filters(filters).get("search", "")[:100]
    if name not in ("ideal", "reconcile") or len(query) < 2 or name not in snapshot.get("reports",{}):
        return []
    from .product_catalog import DT
    items = frappe.get_all(DT,
        or_filters={"item_code":["like","%"+query+"%"], "item_title":["like","%"+query+"%"]},
        fields=["item_code","item_title","reference_code","needs_completion","source_conflict","source_present"],
        order_by="item_code", limit_page_length=5)
    result = []
    for item in items:
        if name == "reconcile" and item.source_present and not (item.needs_completion or item.source_conflict):
            reason = "کالا در سپیدار موجود است و اطلاعات تکمیلی آن کامل است؛ این گزارش فقط موارد مغایرت یا نیازمند تکمیل را نشان می‌دهد."
        elif name == "ideal":
            reason = "این گزارش فقط اقلام دارای موجودی ایده‌آل محاسبه‌شده را نشان می‌دهد."
            reference = text(item.reference_code) or item.item_code
            if reference.casefold() != item.item_code.casefold():
                reason += " محاسبه برای کالای مرجع " + reference + " انجام می‌شود."
            else:
                basis = next((row for row in snapshot.get("reports",{}).get("orders",[])
                    if text(row.get("ItemCode")).casefold() == item.item_code.casefold()
                    and row.get("StockId") is None), None)
                if basis and basis.get("OrderEligibility"):
                    reason += " وضعیت محاسبه در آخرین گزارش: " + text(basis["OrderEligibility"]) + "."
        else:
            reason = "کالا در کاتالوگ موجود است؛ با فیلترهای فعلی در نتیجه این گزارش نمایش داده نمی‌شود."
        result.append({"code":item.item_code, "title":text(item.item_title) or "نام کالا ثبت نشده", "reason":reason,
            "url":"/portal-products?"+urlencode({"search":item.item_code,"status":"all"})})
    return result


@frappe.whitelist()
def search_suggestions(name, query="", filters=None):
    require_access()
    query=text(query)[:200].casefold()
    if len(query)<2:return []
    filters=parse_filters(filters);filters.pop("search",None)
    records,snapshot,_,_=filtered_rows(name,filters)
    fields=REPORTS[name]["fields"];found={}
    for row in records:
        code=text(row.get("ItemCode") or row.get("ReferenceCode"))
        title=text(row.get("ItemTitle") or row.get("ReferenceTitle"))
        candidates=[]
        if code or title:candidates.append((code or title," — ".join(v for v in (code,title) if v)))
        if "CustomerName" in fields and row.get("CustomerName"):candidates.append((text(row["CustomerName"]),"مشتری: "+text(row["CustomerName"])))
        for value,label in candidates:
            if query in text(label).casefold():found.setdefault(value,label)
    if not found:
        for item in catalog_search_context(name,{"search":query},snapshot):
            found[item["code"]] = item["code"] + " — " + item["title"] + " — موجود در کاتالوگ کالاها"
    return [{"value":value,"label":label} for value,label in sorted(found.items(),key=lambda pair:(not text(pair[0]).casefold().startswith(query),pair[1]))[:15]]


@frappe.whitelist()
def report(name, filters=None, page=1, page_size=50, sort_by=None, descending="0"):
    require_access()
    rows, snapshot, options, available = filtered_rows(name, filters)
    page, page_size = max(1, frappe.utils.cint(page)), min(200, max(10, frappe.utils.cint(page_size)))
    fields = REPORTS[name]["fields"]
    if sort_by in fields:
        def sorter(row):
            value = row.get(sort_by)
            try: return (value is None, 0, number(value))
            except Exception: return (value is None, 1, text(value).casefold())
        rows = sorted(rows, key=sorter, reverse=str(descending) == "1")
    return {"title": REPORTS[name]["title"], "available": available, "updated_at": snapshot.get("updated_at"),
            "settings_at": snapshot.get("settings_at"), "source_run": snapshot.get("source_run"),
            "columns": [{"field": f, "label": LABELS[f]} for f in fields], "options": options,
            "metrics": metrics(name, rows) if available else [], "groups": groups(name, rows) if available else [],
            "total": len(rows), "page": page, "page_size": page_size,
            "rows": rows[(page - 1) * page_size:page * page_size], "state": read_snapshot("state"),
            "catalog_matches": catalog_search_context(name,filters,snapshot) if not rows else []}


@frappe.whitelist()
def export_csv(name, filters=None):
    require_access()
    rows, _, _, available = filtered_rows(name, filters)
    if not available:
        frappe.throw("هنوز داده‌ای از منابع دریافت نشده است")
    stream = io.StringIO()
    writer = csv.writer(stream)
    fields = REPORTS[name]["fields"]
    writer.writerow([LABELS[f] for f in fields])
    for row in rows:
        writer.writerow([safe_csv_cell(row.get(f)) for f in fields])
    frappe.local.response.update({"type": "download", "filename": "purchase-" + name + ".csv",
                                  "filecontent": ("\ufeff" + stream.getvalue()).encode("utf-8"),
                                  "content_type": "text/csv; charset=utf-8"})
