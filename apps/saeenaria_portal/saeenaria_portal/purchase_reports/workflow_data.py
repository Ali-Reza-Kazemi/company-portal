"""Source extraction and report calculation."""

import json
from decimal import Decimal

import frappe
from frappe.utils import get_datetime, getdate, today

from . import workflow_math as math
from . import workflow_sources as source
from .calculations import (
    calculate,
    convert_mapping,
    key,
    number,
    settings_values,
    shift_months,
    text,
)
from .service import read_snapshot


def settings_bundle():
    from .portal_inputs import read_inputs

    return read_inputs()


def operational_metrics(start, end):
    records = frappe.get_all(
        "Portal Record",
        filters={
            "domain": "inventory",
            "is_demo": 0,
            "record_type": ["in", ["Supply Request", "Stock Count"]],
        },
        fields=[
            "name",
            "record_type",
            "record_date",
            "item_code",
            "quantity",
            "planned_at",
            "actual_at",
            "baseline_snapshot",
            "creation",
        ],
        order_by="creation desc",
    )
    delays, counts, outstanding = [], {}, 0
    for r in records:
        try:
            info = json.loads(r.baseline_snapshot or "{}")
        except ValueError:
            continue
        if info.get("policy") != math.POLICY:
            continue
        if r.record_type == "Supply Request" and r.planned_at:
            if not r.actual_at:
                outstanding += 1
            elif start <= getdate(r.actual_at) <= end:
                days = (
                    Decimal((getdate(r.actual_at) - getdate(r.planned_at)).days)
                    if info.get("receipt_date_precision") == "day"
                    else Decimal(
                        str(
                            (get_datetime(r.actual_at) - get_datetime(r.planned_at)).total_seconds()
                        )
                    )
                    / 86400
                )
                if days >= 0:
                    delays.append({"record": r.name, "days": days})
        if (
            r.record_type == "Stock Count"
            and start <= getdate(r.record_date) <= end
            and "book" in info
        ):
            counts.setdefault(
                (r.item_code, str(info.get("stock"))),
                {
                    "record": r.name,
                    "difference": number(r.quantity) - number(info["book"]),
                },
            )
    lead = math.metric(
        "lead",
        "زمان آلارم اتمام کالا تا رسید",
        sum(r["days"] for r in delays) / len(delays) if delays else None,
        "روز",
        status="Provisional",
        note="میانگین آلارم‌های دارای پیوند صریح به رسید معتبر؛ رسید سپیدار دقت روز دارد، نه ساعت تحویل. آلارم باز جدا نمایش داده می‌شود.",
        samples=delays,
        outstanding=outstanding,
    )
    mismatches = sum(abs(r["difference"]) > Decimal("0.0001") for r in counts.values())
    variance = math.metric(
        "variance",
        "درصد مغایرت موجودی",
        Decimal(mismatches) * 100 / len(counts) if counts else None,
        "درصد",
        note="آخرین شمارش هر کالا و انبار در ماه؛ اقلام دارای اختلاف تقسیم بر اقلام شمارش‌شده، نه کل کاتالوگ.",
        numerator=mismatches,
        denominator=len(counts),
        samples=list(counts.values()),
    )
    return lead, variance


def weekly_payload(start, end, reconstructed=False):
    deals, metadata = source.crm_deals(start, end)
    deals.sort(key=lambda r: str(r["source_id"]))
    value = math.weekly_rate(deals, start, end)
    validation = read_snapshot("crm-validation")
    if validation.get("status") == "Mismatch":
        value["status"] = "Provisional"
        value["note"] += (
            " اختلاف تاریخ با خود دیدار گزارش شده است؛ تا اصلاح همگام‌سازی، درصد و هفته‌بندی موقت و نیازمند تطبیق‌اند."
        )
    return dict(
        kind="Weekly",
        start=start.isoformat(),
        end=end.isoformat(),
        policy=math.POLICY,
        basis="تعداد درخواست‌های تعیین‌تکلیف‌شده در نسخه فعلی دیتابیس دیدار",
        metrics=[value],
        source_metadata={
            "crm": metadata,
            "reconstructed": reconstructed,
            "validation": validation,
        },
        groups=[],
        urgency=[],
        evidence={"deals": deals},
    )


def build_payload(kind):
    from .workflow import existing_forecast, latest

    current = getdate(today())
    start, end = (
        math.previous_week(current)
        if kind == "Weekly"
        else math.previous_month(current)
        if kind == "Monthly"
        else (math.month_bounds(current)[0], current)
    )
    base = dict(
        kind=kind,
        start=start.isoformat(),
        end=end.isoformat(),
        policy=math.POLICY,
        basis=math.BASIS,
    )
    if kind == "Weekly":
        return weekly_payload(start, end)
    settings = settings_bundle()
    base["settings_revision"] = settings.get("portal_settings_revision")
    policy = settings_values(settings["GeneralSettings"])
    lookback = max(
        int(policy["دوره بررسی فروش"]),
        int(policy["پنجره تأیید بازگشت فروش"] + policy["آستانه تشخیص رسوب"]) + 1,
        12,
    )
    inventory, sales, monthly, items = source.load_inventory(end, shift_months(start, -lookback))
    inventory.sort(key=lambda r: (str(r["StockId"]), key(r["ItemCode"])))
    from . import product_catalog

    if product_catalog.active():
        product_catalog.sync_items(items)
        settings["ProductMapping"] = product_catalog.mapping_rows()
    mapping = convert_mapping(settings["ProductMapping"])
    reports = calculate(
        settings["ProductMapping"],
        settings["IncomingOrders"] if kind == "Cash" else [],
        settings["GeneralSettings"],
        inventory,
        sales,
        monthly,
        items,
        today=end,
    )
    for row in reports["orders"]:
        row["LeadMonths"] = policy["زمان تأمین"]
    sediment = [
        r
        for r in reports["orders"]
        if r.get("StockId") is not None
        and key(r["ItemCode"]) == key(r["EffectiveReference"])
        and number(r["ReferenceInventoryQty"]) > 0
        and r["SedimentReason"] != "عادی"
    ]
    values, groups, urgency = math.aggregate_finance(
        inventory, mapping, reports["orders"], sediment, end
    )
    if kind == "Monthly":
        values = values[:2]
        values.append(math.turnover(sales, monthly, end))
        lead, variance = operational_metrics(start, end)
        mapped = {key(r["ItemCode"]): r for r in mapping}
        actual = {k: Decimal(0) for k in math.GROUPS}
        refs = {key(r["ItemCode"]): r for r in mapping}
        for r in sales:
            if not start <= getdate(r["DocumentDate"]) <= end:
                continue
            item = mapped.get(key(r["ItemCode"]), {})
            ref = refs.get(key(item.get("EffectiveReference")), item)
            group = math.CATEGORIES.get(text(ref.get("Category")))
            if group:
                actual[group] += number(r["Quantity"])
        values += [
            lead,
            math.forecast_accuracy(existing_forecast(start, end), actual),
            variance,
        ]
        cash = latest("Cash")
        cash_data = json.loads(cash.payload) if cash else {}
        planner = next(
            (r for r in cash_data.get("metrics", []) if r["code"] == "urgency"),
            math.metric(
                "urgency",
                "اقلام نیازمند تصمیم خرید",
                None,
                "قلم",
                note="گزارش نقدینگی روز را دریافت کنید",
            ),
        )
        values.append(planner)
        urgency = cash_data.get("urgency", [])
        base["planner_asof"] = cash_data.get("end")
    else:
        missing_order_prices = sum(r["missing_order_prices"] for r in groups)
        need_value = (
            sum(r["need_rial"] for r in groups)
            if not urgency or missing_order_prices < len(urgency)
            else None
        )
        values.append(
            math.metric(
                "cash_need",
                "برآورد نیاز نقدینگی به قیمت رسمی فروش",
                need_value,
                "ریال",
                "Provisional" if missing_order_prices else "Valid",
                note=math.BASIS + "؛ این برآورد جای پیش‌فاکتور خرید تأمین‌کننده نیست",
                missing_prices=missing_order_prices,
            )
        )
        # Suggestions are a draft; a responsible person freezes the next-month forecast.
        suggestions = {k: Decimal(0) for k in math.GROUPS}
        for r in reports["orders"]:
            if r.get("StockId") is None and key(r["ItemCode"]) == key(r["EffectiveReference"]):
                group = math.CATEGORIES.get(text(r.get("Category")))
                if group:
                    suggestions[group] += max(Decimal(0), number(r["AverageMonthlyNetSales"])) * (
                        1 + policy["درصد رشد پیش‌بینی"] / 100
                    )
        base["forecast_suggestions"] = suggestions
        base["forecast_method"] = {
            "months": int(policy["دوره بررسی فروش"]),
            "growth_percent": float(policy["درصد رشد پیش‌بینی"]),
            "asof": end.isoformat(),
        }
    return {
        **base,
        "metrics": values,
        "groups": groups,
        "urgency": urgency,
        "source_metadata": {
            "settings": settings["metadata"],
            "inventory_rows": len(inventory),
            "sales_rows": len(sales),
            "sales_start": shift_months(start, -lookback).isoformat(),
            "historic_policy": "بازمحاسبه دوره گذشته با نگاشت و سیاست فعلی ثبت‌شده در این نسخه",
        },
        "evidence": {
            "inventory": inventory,
            "mapping": mapping,
            "settings": settings["GeneralSettings"],
            "incoming": settings["IncomingOrders"] if kind == "Cash" else [],
            "reference_stock": [
                {
                    "code": r["ItemCode"],
                    "quantity": r["ReferenceInventoryQty"],
                    "avg": r["AverageMonthlyNetSales"],
                }
                for r in reports["orders"]
                if r.get("StockId") is None and key(r["ItemCode"]) == key(r["EffectiveReference"])
            ],
            "sediment_keys": [[r["StockId"], r["ItemCode"]] for r in sediment],
        },
    }
