"""PurchaseOrder model calculations, with no database or Frappe dependency.

Quantities and values retain the source units (money is rial). Missing prices and
undefined ratios stay None. Defaults below bootstrap the native portal policy.
"""
from calendar import monthrange
from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_CEILING
import re


DEFAULTS = {
    "دوره بررسی فروش": 36, "زمان تأمین": 3, "پوشش هدف": 4,
    "ذخیره اطمینان": 0, "درصد رشد پیش‌بینی": 0, "حداقل سفارش": 1,
    "ضریب بسته‌بندی": 1, "پنجره تأیید بازگشت فروش": 6,
    "حداقل ماه فعال برای خروج از رسوب": 2, "آستانه تشخیص رسوب": 12,
    "حداکثر پوشش مجاز": 12,
}


def text(value):
    return str(value or "").strip().translate(str.maketrans({"ك": "ک", "ي": "ی", "ى": "ی"}))


def is_service_item(title):
    title=text(title)
    return bool(re.search(r"[（(]\s*KH\s*[)）]|سیم[\s\u200c]*پیچی", title, re.IGNORECASE))


def key(value):
    return text(value).casefold()


def number(value):
    return Decimal(str(value or 0))


def day(value):
    return date.fromisoformat(str(value)[:10])


def shift_months(value, months):
    year, month = divmod(value.year * 12 + value.month - 1 + months, 12)
    return date(year, month + 1, min(value.day, monthrange(year, month + 1)[1]))


def ratio(a, b):
    return a / b if b else None


def total(rows, field):
    values = [number(r[field]) for r in rows if r.get(field) is not None]
    return sum(values, Decimal(0)) if values else None


def settings_values(rows):
    settings = {name: number(value) for name, value in DEFAULTS.items()}
    seen = set()
    for row in rows:
        name = text(row.get("پارامتر"))
        if name and name in seen:
            raise ValueError("پارامتر تکراری در تنظیمات")
        seen.add(name)
        if name in settings and row.get("مقدار") not in (None, ""):
            settings[name] = number(row["مقدار"])
    for name in ("دوره بررسی فروش", "پنجره تأیید بازگشت فروش", "آستانه تشخیص رسوب", "حداقل ماه فعال برای خروج از رسوب"):
        if settings[name] < 0 or settings[name] != int(settings[name]):
            raise ValueError("پارامتر ماه نامعتبر است: " + name)
    if settings["دوره بررسی فروش"] == 0:
        raise ValueError("دوره بررسی فروش باید مثبت باشد")
    return settings


def convert_mapping(rows):
    result = []
    seen = set()
    for row in rows:
        code = text(row.get("کد کالا"))
        if not code:
            continue
        if key(code) in seen:
            raise ValueError("کد کالای تکراری در تنظیمات")
        seen.add(key(code))
        # An empty manual reference means the item is its own reference.
        reference = text(row.get("کد مرجع دستی")) or code
        result.append(dict(ItemCode=code, ItemTitle=text(row.get("نام کالا")),
                           EffectiveReference=reference,
                           Category=text(row.get("دسته‌بندی اختصاصی")) or "بدون دسته‌بندی",
                           ReviewStatus=text(row.get("وضعیت بررسی")),
                           CatalogPending=bool(row.get("CatalogPending")),
                           CatalogPlanned=bool(row.get("CatalogPlanned")),
                           OrderControl=text(row.get("کنترل سفارش")) or "خودکار"))
    return result


def calculate(mapping_rows, incoming, settings_rows, inventory, sales, monthly, items, today=None):
    """Build order/budget/turnover/reconciliation rows for each stock and all stocks.

    Order totals across stocks must be recalculated, rather than summing rounded
    stock-level orders or duplicating the unallocated incoming quantity.
    """
    today = today or date.today()
    settings = settings_values(settings_rows)
    mapping = convert_mapping(mapping_rows)
    service_codes={key(r.get("ItemCode")) for r in [*mapping,*items,*inventory] if is_service_item(r.get("ItemTitle"))}
    by_code = {key(r["ItemCode"]): r for r in mapping}
    refs = [r for r in mapping if key(r["ItemCode"]) == key(r["EffectiveReference"])]
    stock_titles = {}
    for row in inventory + sales:
        if row.get("StockId") is not None:
            stock_titles[str(row["StockId"])] = text(row.get("StockTitle"))
    inv_index, sale_index, month_index = defaultdict(list), defaultdict(list), defaultdict(list)
    for rows, index in ((inventory, inv_index), (sales, sale_index), (monthly, month_index)):
        for row in rows:
            if key(row.get("ItemCode")) in service_codes or (index is sale_index and day(row["DocumentDate"])>today):
                continue
            mapped = by_code.get(key(row.get("ItemCode")))
            if not mapped:
                continue
            ref = key(mapped["EffectiveReference"])
            index[(str(row.get("StockId")), ref)].append(row)
            index[(None, ref)].append(row)
    incoming_index = defaultdict(Decimal)
    for row in incoming:
        if text(row.get("وضعیت")) == "فعال":
            incoming_index[key(row.get("کد مرجع"))] += number(row.get("تعداد در راه"))
    lookback = shift_months(today, -int(settings["دوره بررسی فروش"]))
    cutoff = shift_months(today, -int(settings["پنجره تأیید بازگشت فروش"]))
    turnover_start = shift_months(today.replace(day=1), -11)
    orders, budgets, turnovers = [], [], []
    for stock in [None, *sorted(stock_titles)]:
        for mapped in refs:
            ref = key(mapped["ItemCode"])
            inv = inv_index[(stock, ref)]
            sale = sale_index[(stock, ref)]
            stock_qty = total(inv, "Quantity") or Decimal(0)
            net = sum((number(r.get("Quantity")) for r in sale if day(r["DocumentDate"]) >= lookback), Decimal(0))
            avg = net / settings["دوره بررسی فروش"]
            active = defaultdict(Decimal)
            for r in sale:
                if day(r["DocumentDate"]) >= cutoff:
                    active[(r.get("JalaliYear"), r.get("JalaliMonthNumber"))] += number(r.get("Quantity"))
            active_months = sum(v > 0 for v in active.values())
            previous = max((day(r["DocumentDate"]) for r in sale if day(r["DocumentDate"]) < cutoff and number(r.get("Quantity")) > 0), default=None)
            gap = None if previous is None else (cutoff.year - previous.year) * 12 + cutoff.month - previous.month
            dormant = (gap is None or gap >= settings["آستانه تشخیص رسوب"]) and active_months < settings["حداقل ماه فعال برای خروج از رسوب"]
            coverage = Decimal(0) if stock_qty <= 0 else ratio(stock_qty, avg) if avg > 0 else None
            excess = stock_qty > 0 and (avg <= 0 or coverage > settings["حداکثر پوشش مجاز"])
            reason = ("رکود/فروش موردی و پوشش بیش از حد" if dormant and excess else
                      "پوشش بیش از حد/کندگردش" if excess else "رکود/فروش موردی" if dormant else "عادی")
            control = mapped["OrderControl"]
            eligible = ("نیازمند تکمیل اطلاعات" if mapped["CatalogPending"] else "کالای خدماتی" if ref in service_codes else "ممنوع دستی" if control == "ممنوع دستی" else "مجاز" if control == "مجاز دستی" else
                        "فروش موردی/رسوبی" if dormant or excess else "مجاز")
            target = avg * (settings["زمان تأمین"] + settings["پوشش هدف"] + settings["ذخیره اطمینان"]) * (1 + settings["درصد رشد پیش‌بینی"] / 100)
            incoming_qty = incoming_index[ref]
            raw = max(Decimal(0), target - stock_qty - incoming_qty)
            pack = max(Decimal(1), settings["ضریب بسته‌بندی"])
            ordered = (max(raw, settings["حداقل سفارش"]) / pack).to_integral_value(rounding=ROUND_CEILING) * pack if raw > 0 and eligible == "مجاز" else Decimal(0)
            prices = [number(r["UnitPrice"]) for r in inv if key(r.get("ItemCode")) == ref and r.get("UnitPrice") is not None]
            price = max(prices, default=None)
            ideal = target.to_integral_value(rounding=ROUND_CEILING) if mapped["ReviewStatus"] == "تأیید شده" and eligible == "مجاز" and target > 0 else None
            row = {**mapped, "StockId": stock, "StockTitle": stock_titles.get(stock, "همه انبارها"),
                   "CurrentItemStock": sum((number(r.get("Quantity")) for r in inv if key(r.get("ItemCode"))==ref),Decimal(0)),
                   "AverageMonthlyNetSales": avg, "ReferenceInventoryQty": stock_qty,
                   "ReferenceIncomingQty": incoming_qty, "ActiveMonthsRecent": active_months,
                   "OrderEligibility": eligible, "SuggestedOrderQty": ordered,
                   "OfficialPriceRial": price, "SuggestedOrderValueRial": ordered * price if price is not None else None,
                   "CoverageMonths": coverage, "MaxAllowedCoverage": settings["حداکثر پوشش مجاز"],
                   "SedimentReason": reason, "IdealQty": ideal,
                   "IdealValueRial": ideal * price if ideal is not None and price is not None and price > 0 else None}
            if ref not in service_codes:orders.append(row)
            if stock is None:
                continue
            if ideal is not None:
                budgets.append(dict(row))
            monthly_by_date = defaultdict(Decimal)
            for r in month_index[(stock, ref)]:
                monthly_by_date[str(r["SnapshotDate"])[:10]] += number(r.get("ClosingQty"))
            avg_inv = ratio(sum(monthly_by_date.values(), Decimal(0)), len(monthly_by_date))
            sales12 = sum((number(r.get("Quantity")) for r in sale if turnover_start <= day(r["DocumentDate"]) <= today), Decimal(0))
            rate = ratio(max(Decimal(0), sales12), avg_inv) if avg_inv is not None and avg_inv > 0 else None
            if not sales12 and not avg_inv:
                continue
            status = ("نیازمند بررسی موجودی منفی" if avg_inv is not None and avg_inv < 0 else
                      "فاقد موجودی متوسط" if not avg_inv and sales12 > 0 else
                      "سریع‌گردش" if rate is not None and rate >= 6 else "عادی" if rate is not None and rate >= 3 else
                      "کندگردش" if rate is not None and rate >= 1 else "بسیار کندگردش" if rate else "بدون گردش")
            turnovers.append({**row, "NetSalesQty12M": sales12, "AverageInventoryQty12M": avg_inv,
                              "TurnoverRate": rate, "InventoryDays": ratio(Decimal(365), rate), "TurnoverStatus": status})
    order_lookup = {(r["StockId"], key(r["ItemCode"])): r for r in orders}
    for stock in [None, *sorted(stock_titles)]:
        for mapped in mapping:
            if key(mapped["ItemCode"]) in service_codes:
                continue
            if key(mapped["ItemCode"]) == key(mapped["EffectiveReference"]):
                continue
            reference = order_lookup.get((stock, key(mapped["EffectiveReference"])))
            if reference:
                orders.append({**reference, **mapped, "OrderEligibility": "فقط کالای مشابه",
                               "SuggestedOrderQty": Decimal(0), "SuggestedOrderValueRial": Decimal(0),
                               "IdealQty": None, "IdealValueRial": None})
    sepidar = {key(r["ItemCode"]): r for r in items}
    mismatch = [{**r, "MismatchSide": "فقط در پورتال"} for r in mapping if key(r["ItemCode"]) not in sepidar and not r.get("CatalogPlanned")]
    mismatch += [{**r, "MismatchSide": "فقط در سپیدار"} for k, r in sepidar.items() if k not in by_code]
    mismatch += [{**r, "MismatchSide": "نیازمند تکمیل اطلاعات"} for r in mapping if r.get("CatalogPending") and key(r["ItemCode"]) in sepidar]
    return {"orders": orders, "budget": budgets, "ideal": budgets, "turnover": turnovers, "reconcile": mismatch}
