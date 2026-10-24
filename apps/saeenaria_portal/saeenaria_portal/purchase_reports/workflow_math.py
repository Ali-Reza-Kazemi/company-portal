"""Versioned inventory performance policy. Money uses official sale prices v1."""
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal
import math
import jdatetime
from .calculations import number, text, key, ratio, shift_months

POLICY = "inventory-official-sale-v1"
BASIS = "قیمت فروش رسمی؛ برآورد مدیریتی و نه بهای تمام‌شده"
GROUPS = {
    "bits": "مته و گردبر", "drills": "انواع دریل", "manual": "پخ‌زن دستی",
    "automatic": "پخ‌زن اتومات", "drill_parts": "قطعات یدکی دریل", "bevel_parts": "قطعات یدکی پخ‌زن",
}
CATEGORIES = {"انواع مته": "bits", "گردبر": "bits", "مته و گردبر": "bits",
              **{v: k for k, v in GROUPS.items() if k != "bits"}}


def month_bounds(value):
    j = jdatetime.date.fromgregorian(date=value)
    start = jdatetime.date(j.year, j.month, 1).togregorian()
    next_j = jdatetime.date(j.year + (j.month == 12), j.month % 12 + 1, 1)
    return start, next_j.togregorian() - timedelta(days=1)


def previous_month(value):
    start, _ = month_bounds(value)
    return month_bounds(start - timedelta(days=1))


def previous_week(value):
    saturday = value - timedelta(days=(value.weekday() - 5) % 7)
    return saturday - timedelta(days=7), saturday - timedelta(days=1)


def month_ends(end, count=12):
    values = []
    cursor = end
    for _ in range(count):
        _, last = month_bounds(cursor)
        values.append(min(last, cursor))
        first, _ = month_bounds(cursor)
        cursor = first - timedelta(days=1)
    return sorted(values)


def metric(code, title, value, unit, status="Valid", note="", **evidence):
    return dict(code=code, title=title, value=value, unit=unit,
                status="Missing" if value is None else status, note=note, evidence=evidence)


def weekly_rate(deals, start, end):
    resolved, lost = set(), set()
    for row in deals:
        state = int(row["state"])
        if state not in (1, 2):
            continue
        stamp = row["won_at"] if state == 1 else row["lost_at"]
        if not stamp or not start <= date.fromisoformat(str(stamp)[:10]) <= end:
            continue
        resolved.add(str(row["source_id"]))
        if state == 2 and text(row.get("reason")) == "نبود کالا":
            lost.add(str(row["source_id"]))
    return metric("cancel", "درخواست‌های کنسل‌شده به علت نبود کالا", ratio(Decimal(len(lost)) * 100, len(resolved)), "درصد",
                  note="تعداد معاملات یکتای ناموفق با علت دقیق «نبود کالا» تقسیم بر معاملات موفق و ناموفق تعیین‌تکلیف‌شده همان هفته؛ معامله نماینده درخواست است.",
                  numerator=len(lost), denominator=len(resolved), numerator_ids=sorted(lost), denominator_ids=sorted(resolved))


def aggregate_finance(inventory, mapping, orders, sediment, asof):
    mapping_by_code = {key(r["ItemCode"]): r for r in mapping}
    ref_category = {key(r["ItemCode"]): text(r.get("Category")) for r in mapping}
    table = {k: dict(code=k, title=v, inventory_rial=Decimal(0), need_rial=Decimal(0), stagnant_rial=Decimal(0),
                     missing_inventory_prices=0, missing_order_prices=0, item_count=0) for k, v in {**GROUPS, "other": "سایر / بدون نگاشت"}.items()}
    stagnant = {(str(r.get("StockId")), key(r["ItemCode"])) for r in sediment}
    missing = 0
    stagnant_count = 0
    missing_stagnant = 0
    for row in inventory:
        qty = number(row.get("Quantity"))
        if qty <= 0:
            continue
        mapped = mapping_by_code.get(key(row["ItemCode"]), {})
        ref = key(mapped.get("EffectiveReference") or row["ItemCode"])
        category = ref_category.get(ref) or mapped.get("Category") or "بدون دسته‌بندی"
        group = table[CATEGORIES.get(text(category), "other")]
        group["item_count"] += 1
        is_stagnant=(str(row.get("StockId")), ref) in stagnant
        if is_stagnant:stagnant_count+=1
        price = row.get("UnitPrice")
        if price is None or number(price) <= 0:
            group["missing_inventory_prices"] += 1
            missing += 1
            if is_stagnant:missing_stagnant+=1
            continue
        value = qty * number(price)
        group["inventory_rial"] += value
        if is_stagnant:
            group["stagnant_rial"] += value
    urgency = []
    for row in orders:
        if row.get("StockId") is not None or key(row["ItemCode"]) != key(row["EffectiveReference"]):
            continue
        qty = number(row.get("SuggestedOrderQty"))
        if qty <= 0:
            continue
        group = table[CATEGORIES.get(text(row.get("Category")), "other")]
        price = row.get("OfficialPriceRial")
        if price is None or number(price) <= 0:
            group["missing_order_prices"] += 1
        else:
            group["need_rial"] += qty * number(price)
        avg = number(row.get("AverageMonthlyNetSales"))
        coverage_days = number(row.get("ReferenceInventoryQty")) / avg * 30 if avg > 0 else None
        lead_days = number(row.get("LeadMonths", 3)) * 30
        wait_days = max(0, math.floor(coverage_days - lead_days)) if coverage_days is not None else None
        priority = "فوری" if number(row.get("ReferenceInventoryQty")) <= 0 else "ضروری" if coverage_days is not None and coverage_days <= lead_days else "برنامه‌ریزی‌شده"
        urgency.append(dict(code=row["ItemCode"], title=row["ItemTitle"], category=row.get("Category"),
                            priority=priority, quantity=qty, coverage_days=coverage_days, lead_days=lead_days,
                            order_date=(asof + timedelta(days=wait_days)).isoformat() if wait_days is not None else None,
                            value_rial=qty * number(price) if price is not None and number(price)>0 else None))
    urgency.sort(key=lambda r: ({"فوری": 0, "ضروری": 1, "برنامه‌ریزی‌شده": 2}[r["priority"]], r["order_date"] or "9999", r["code"]))
    all_rows = list(table.values())
    status = "Provisional" if missing else "Valid"
    positive_count=sum(r["item_count"] for r in all_rows)
    capital_value=sum(r["inventory_rial"] for r in all_rows) if not positive_count or missing<positive_count else None
    stagnant_value=sum(r["stagnant_rial"] for r in all_rows) if not stagnant_count or missing_stagnant<stagnant_count else None
    values = [metric("capital", "ارزش موجودی مثبت به قیمت فروش رسمی", capital_value, "ریال", status,
                     note=BASIS + "؛ موجودی منفی جداگانه نیازمند بررسی است؛ اقلام بدون قیمت در جمع مبلغ نیستند.", missing_prices=missing,
                     negative_stock_rows=sum(number(r.get("Quantity"))<0 for r in inventory)),
              metric("slow", "ارزش کل کالای راکد و کندگردش", stagnant_value, "ریال", "Provisional" if missing_stagnant else "Valid",
                     note="کل موجودی مثبت کالای مشمول قاعده رسوب، نه فقط مقدار مازاد پوشش؛ " + BASIS, missing_prices=missing_stagnant),
              metric("urgency", "اقلام نیازمند تصمیم خرید", len(urgency), "قلم", note="زمان سفارش پیشنهادی از پوشش موجودی منهای زمان تأمین تنظیمات؛ تبدیل ماه به روز با قرارداد ۳۰ روزه، نه تعهد تأمین‌کننده.")]
    for r in all_rows:
        for f in ("inventory", "need", "stagnant"):
            r[f + "_toman"] = r[f + "_rial"] / 10
    return values, all_rows, urgency


def turnover(sales, monthly, end):
    dates = month_ends(end)
    start = month_bounds(dates[0])[0]
    net = sum((number(r.get("Quantity")) for r in sales if start <= date.fromisoformat(str(r["DocumentDate"])[:10]) <= end), Decimal(0))
    grouped = defaultdict(Decimal)
    for row in monthly:
        grouped[str(row["SnapshotDate"])[:10]] += number(row["ClosingQty"])
    avg = sum(grouped.values(), Decimal(0)) / len(dates) if grouped and set(grouped) == {d.isoformat() for d in dates} else None
    return metric("turnover", "گردش تعدادی سالانه موجودی", ratio(max(Decimal(0), net), avg) if avg is not None and avg>0 else None,
                  "مرتبه", note="فروش خالص ۱۲ماهه تقسیم بر متوسط موجودی ۱۲ پایان ماه شمسی؛ تعریف تعدادی مستقل از گردش مبتنی بر بهای تمام‌شده است.", numerator=net, denominator=avg, snapshot_dates=[d.isoformat() for d in dates])


def forecast_accuracy(forecast, actual):
    if set(forecast) != set(GROUPS):
        return metric("forecast", "دقت پیش‌بینی تقاضا", None, "درصد", note="پیش‌بینی هر شش گروه باید پیش از شروع ماه ثبت و قفل شده باشد؛ پیش‌بینی گذشته ساخته نمی‌شود.")
    total_actual = sum((max(Decimal(0), number(actual.get(k))) for k in GROUPS), Decimal(0))
    absolute_error = sum((abs(number(forecast[k])-max(Decimal(0), number(actual.get(k)))) for k in GROUPS), Decimal(0))
    accuracy = max(Decimal(0), 100 - absolute_error/total_actual*100) if total_actual>0 else None
    return metric("forecast", "دقت پیش‌بینی تقاضا", accuracy, "درصد", note="۱۰۰ منهای WAPE، با کف صفر؛ دامنه شش گروه و جمع قدرمطلق خطا، فروش خالص منفی در تقاضا صفر محسوب می‌شود.", numerator=absolute_error, denominator=total_actual, forecast=forecast, actual=actual)
