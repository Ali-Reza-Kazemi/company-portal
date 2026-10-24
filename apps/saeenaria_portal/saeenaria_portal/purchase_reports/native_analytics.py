"""Inventory/customer reports calculated from Sepidar facts and portal policy only."""

from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from .calculations import (
    convert_mapping,
    day,
    is_service_item,
    key,
    number,
    settings_values,
    shift_months,
    text,
)


def months_between(older, newer):
    return (
        None
        if older is None
        else max(0, (newer.year - older.year) * 12 + newer.month - older.month)
    )


def saturday(value):
    return value - timedelta(days=(value.weekday() - 5) % 7)


def build_reports(mapping_rows, settings_rows, inventory, sales, calculated, today, weeks=12):
    mapping = {key(row["ItemCode"]): row for row in convert_mapping(mapping_rows)}
    service_codes = {
        key(row.get("ItemCode"))
        for row in [*inventory, *sales]
        if is_service_item(row.get("ItemTitle"))
    }
    service_codes.update(
        code for code, row in mapping.items() if is_service_item(row.get("ItemTitle"))
    )
    by_reference = defaultdict(list)
    for row in sales:
        code = key(row.get("ItemCode"))
        if code in service_codes or code not in mapping or day(row["DocumentDate"]) > today:
            continue
        by_reference[key(mapping[code]["EffectiveReference"])].append(row)
    prices = {}
    for row in inventory:
        if row.get("UnitPrice") is not None and number(row["UnitPrice"]) > 0:
            code = key(row["ItemCode"])
            prices[code] = max(prices.get(code, Decimal(0)), number(row["UnitPrice"]))
    policy = settings_values(settings_rows)
    cutoff = shift_months(today, -int(policy["پنجره تأیید بازگشت فروش"]))
    sediment = []
    for row in calculated["orders"]:
        ref = key(row["ItemCode"])
        if (
            row.get("StockId") is None
            or ref != key(row["EffectiveReference"])
            or ref in service_codes
            or number(row["ReferenceInventoryQty"]) <= 0
            or row["SedimentReason"] == "عادی"
        ):
            continue
        previous = max(
            (
                sale
                for sale in by_reference[ref]
                if str(sale.get("StockId")) == str(row["StockId"])
                and day(sale["DocumentDate"]) < cutoff
                and number(sale["Quantity"]) > 0
            ),
            key=lambda sale: day(sale["DocumentDate"]),
            default=None,
        )
        previous_date = day(previous["DocumentDate"]) if previous else None
        quantity, average = (
            number(row["ReferenceInventoryQty"]),
            number(row["AverageMonthlyNetSales"]),
        )
        excess = max(Decimal(0), quantity - max(Decimal(0), average) * policy["حداکثر پوشش مجاز"])
        price = prices.get(ref)
        sediment.append(
            dict(
                StockId=row["StockId"],
                StockTitle=row["StockTitle"],
                ItemCode=row["ItemCode"],
                ItemTitle=row["ItemTitle"],
                Category=row["Category"],
                CurrentStock=quantity,
                AverageMonthlySales=average,
                CoverageMonths=row["CoverageMonths"],
                MaxAllowedCoverage=policy["حداکثر پوشش مجاز"],
                ActiveMonthsRecent=row["ActiveMonthsRecent"],
                SedimentReason=row["SedimentReason"],
                DormancyMonths=months_between(previous_date, today),
                PreviousSaleJalali=text(previous.get("JalaliDate")) or None if previous else None,
                OfficialUnitPriceRial=price,
                ExcessInventoryQty=excess,
                ExcessInventoryValueRial=excess * price if price is not None else None,
                OrderControl=row["OrderControl"],
            )
        )

    # Target customers use the full net purchase history of a reference across stocks.
    history = {}
    for ref in {key(row["ItemCode"]) for row in sediment}:
        grouped = {}
        for sale in by_reference[ref]:
            customer = sale.get("CustomerId")
            if not customer:
                continue
            group = grouped.setdefault(
                str(customer),
                dict(
                    customer=customer,
                    quantity=Decimal(0),
                    value=Decimal(0),
                    missing_value=False,
                    invoices=set(),
                    last=None,
                    items=set(),
                    name="",
                    expert="",
                    metadata_date=None,
                ),
            )
            quantity = number(sale["Quantity"])
            stamp = day(sale["DocumentDate"])
            group["quantity"] += quantity
            if sale.get("NetPrice") is None:
                group["missing_value"] = True
            else:
                group["value"] += number(sale["NetPrice"])
            if group["metadata_date"] is None or stamp >= group["metadata_date"]:
                group["name"] = " ".join(
                    filter(
                        None, [text(sale.get("CustomerName")), text(sale.get("CustomerLastName"))]
                    )
                )
                group["expert"] = (
                    text(sale.get("CustomerGroupTitle")) or "بدون کارشناس/نیازمند تعیین گروه"
                )
                group["metadata_date"] = stamp
            if sale.get("DocumentType") == "Sale":
                group["invoices"].add(sale["DocumentId"])
            if quantity > 0:
                group["last"] = max(group["last"] or stamp, stamp)
                group["items"].add(text(sale["ItemCode"]) + " - " + text(sale.get("ItemTitle")))
        history[ref] = grouped
    targets = []
    for item in sediment:
        for group in history[key(item["ItemCode"])].values():
            if group["quantity"] <= 0:
                continue
            age = months_between(group["last"], today)
            temperature = (
                "نامشخص"
                if age is None
                else "گرم"
                if age <= 6
                else "قابل‌بازگشت"
                if age <= 18
                else "قدیمی/اتفاقی"
            )
            targets.append(
                dict(
                    StockId=item["StockId"],
                    StockTitle=item["StockTitle"],
                    Category=item["Category"],
                    ReferenceCode=item["ItemCode"],
                    ReferenceTitle=item["ItemTitle"],
                    CurrentStock=item["CurrentStock"],
                    ExcessValueRial=item["ExcessInventoryValueRial"],
                    DormancyMonths=item["DormancyMonths"],
                    SedimentReason=item["SedimentReason"],
                    CustomerId=group["customer"],
                    CustomerName=group["name"],
                    ExpertGroup=group["expert"],
                    CustomerTemperature=temperature,
                    PurchasedItems=" | ".join(sorted(group["items"])),
                    HistoricalNetQty=group["quantity"],
                    HistoricalNetSalesRial=None if group["missing_value"] else group["value"],
                    InvoiceCount=len(group["invoices"]),
                    LastPurchaseDate=group["last"],
                )
            )

    first, end = saturday(today) - timedelta(weeks=weeks), saturday(today)
    weekly = {}
    for item in sediment:
        ref = key(item["ItemCode"])
        for sale in by_reference[ref]:
            stamp = day(sale["DocumentDate"])
            if not first <= stamp < end or str(sale.get("StockId")) != str(item["StockId"]):
                continue
            expert = text(sale.get("CustomerGroupTitle")) or "بدون کارشناس/نیازمند تعیین گروه"
            ident = (
                saturday(stamp),
                str(item["StockId"]),
                ref,
                str(sale.get("CustomerId") or 0),
                expert,
            )
            row = weekly.setdefault(
                ident,
                dict(
                    WeekStart=saturday(stamp),
                    StockId=item["StockId"],
                    StockTitle=item["StockTitle"],
                    Category=item["Category"],
                    ReferenceCode=item["ItemCode"],
                    ReferenceTitle=item["ItemTitle"],
                    CustomerId=sale.get("CustomerId") or 0,
                    CustomerName=" ".join(
                        filter(
                            None,
                            [text(sale.get("CustomerName")), text(sale.get("CustomerLastName"))],
                        )
                    ),
                    ExpertGroup=expert,
                    NetQty=Decimal(0),
                    NetSalesRial=Decimal(0),
                ),
            )
            row["NetQty"] += number(sale["Quantity"])
            if row["NetSalesRial"] is not None:
                row["NetSalesRial"] = (
                    None
                    if sale.get("NetPrice") is None
                    else row["NetSalesRial"] + number(sale["NetPrice"])
                )
    return {"sediment": sediment, "targets": targets, "weekly": list(weekly.values())}
