"""Native report boundaries, aliases, returns, customers and missing prices."""

from datetime import date, timedelta

import frappe
from saeenaria_portal.purchase_reports.calculations import calculate
from saeenaria_portal.purchase_reports.native_analytics import build_reports, saturday, weekly_sales
from test_support import init_site

init_site()

try:
    today = date(2026, 10, 24)  # Saturday: exclude the partial current week.
    mapping = [
        {"کد کالا": "A", "نام کالا": "مرجع", "وضعیت بررسی": "تأیید شده"},
        {"کد کالا": "B", "کد مرجع دستی": "A"},
        {"کد کالا": "S", "نام کالا": "خدمات (KH)"},
        {"کد کالا": "P", "CatalogPlanned": True},
    ]
    inventory = [
        dict(ItemCode="A", StockId=1, StockTitle="مرکزی", Quantity=100, UnitPrice=10),
        dict(ItemCode="B", StockId=1, StockTitle="مرکزی", Quantity=2, UnitPrice=999),
        dict(ItemCode="S", ItemTitle="خدمات (KH)", StockId=1, Quantity=10),
    ]

    def sale(stamp, qty, code="B", stock=1, customer=1, document=1, price=20):
        return dict(
            ItemCode=code,
            StockId=stock,
            Quantity=qty,
            DocumentDate=stamp,
            JalaliYear=1405,
            JalaliMonthNumber=7,
            DocumentType="Sale" if qty > 0 else "Return",
            DocumentId=document,
            CustomerId=customer,
            CustomerName="مشتری",
            CustomerLastName="آزمون",
            CustomerGroupTitle="فروش",
            NetPrice=price,
            JalaliDate="1405/07/01",
        )

    sales = [
        sale(today - timedelta(days=7), 5),
        sale(today - timedelta(days=7), 2),
        sale(today - timedelta(days=6), -2, price=-8),
        sale(date(2020, 1, 1), 8, stock=2, document=2),
        sale(today - timedelta(days=2), -2, customer=2, price=-8),
        sale(today, 3, customer=3),
        sale(today + timedelta(days=1), 1000, customer=4),
        sale(today - timedelta(days=7), 50, code="S", customer=5),
    ]

    def reports(policy=(), inv=None):
        inv = inventory if inv is None else inv
        calculated = calculate(
            mapping, [], policy, inv, sales, [], [{"ItemCode": c} for c in ("A", "B", "S")], today
        )
        return calculated, build_reports(mapping, policy, inv, sales, calculated, today)

    calculated, result = reports()
    assert all(r["ItemCode"] != "P" for r in calculated["reconcile"])
    assert len(result["sediment"]) == 1
    sediment = result["sediment"][0]
    assert sediment["CurrentStock"] == 102 and sediment["OfficialUnitPriceRial"] == 10
    assert sediment["ExcessInventoryValueRial"] == sediment["ExcessInventoryQty"] * 10
    target = next(r for r in result["targets"] if r["CustomerId"] == 1)
    assert target["HistoricalNetQty"] == 13 and target["InvoiceCount"] == 2
    assert target["HistoricalNetSalesRial"] == 52 and target[
        "LastPurchaseDate"
    ] == today - timedelta(days=7)
    assert {r["CustomerId"] for r in result["targets"]} == {1, 3}
    weekly = [r for r in result["weekly"] if r["CustomerId"] == 1]
    assert {r["DocumentDate"]: (r["NetQty"], r["NetSalesRial"]) for r in weekly} == {
        date(2026, 10, 17): (7, 40),
        date(2026, 10, 18): (-2, -8),
    }
    assert all(r["WeekStart"] == date(2026, 10, 17) for r in weekly)
    assert all(today - timedelta(weeks=12) <= r["WeekStart"] < today for r in result["weekly"])
    assert saturday(date(2026, 10, 23)) == date(2026, 10, 17)
    # Start midweek: exclude the previous day's sales but keep the return on
    # the first day and the sale on the last day, even in the current week.
    custom = weekly_sales(result["sediment_sales_daily"], today - timedelta(days=6), today)
    assert {row["CustomerId"]: row["NetQty"] for row in custom} == {1: -2, 2: -2, 3: 3}
    assert sum(row["NetSalesRial"] for row in custom) == 4
    missing = [{**r, "UnitPrice": None} for r in inventory]
    assert reports(inv=missing)[1]["sediment"][0]["ExcessInventoryValueRial"] is None
    _, changed = reports(
        [
            {"پارامتر": "حداکثر پوشش مجاز", "مقدار": 10000},
            {"پارامتر": "حداقل ماه فعال برای خروج از رسوب", "مقدار": 0},
        ]
    )
    assert changed["sediment"] == [] and changed["weekly"] == []
    print(
        "PASS native analytics: aliases, per-stock sediment, full-history net customers, distinct invoices, signed returns, Saturday weeks, future/service exclusions, local policy, planned references and missing prices"
    )
finally:
    frappe.db.rollback()
    frappe.destroy()
