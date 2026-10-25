"""Regression fixtures for formulas translated from PurchaseOrder, without real data."""
from datetime import date
from decimal import Decimal
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "saeenaria_portal"))
from saeenaria_portal.purchase_reports.calculations import calculate, shift_months


class PurchaseCalculations(unittest.TestCase):
    def setUp(self):
        self.mapping = [{"کد کالا": "A", "نام کالا": "مرجع", "وضعیت بررسی": "تأیید شده", "کنترل سفارش": "مجاز دستی"},
                        {"کد کالا": "B", "نام کالا": "مشابه", "کد مرجع دستی": "A"}]
        self.inventory = [dict(ItemCode="A", StockId=1, StockTitle="مرکزی", Quantity=10, UnitPrice=100),
                          dict(ItemCode="B", StockId=1, StockTitle="مرکزی", Quantity=5, UnitPrice=999)]
        self.sales = [dict(ItemCode="B", StockId=1, StockTitle="مرکزی", Quantity=360,
                           DocumentDate="2026-09-20", JalaliYear=1405, JalaliMonthNumber=6)]
        self.today = date(2026, 10, 19)

    def run_model(self, **changes):
        values = dict(mapping_rows=self.mapping, incoming=[], settings_rows=[], inventory=self.inventory,
                      sales=self.sales, monthly=[], items=[dict(ItemCode="A"), dict(ItemCode="C")], today=self.today)
        values.update(changes)
        return calculate(**values)

    def test_reference_aggregation_and_price(self):
        row = self.run_model()["orders"][0]
        self.assertEqual(row["ReferenceInventoryQty"], 15)
        self.assertEqual(row["AverageMonthlyNetSales"], 10)
        self.assertEqual(row["OfficialPriceRial"], 100)  # similar-item price must not replace reference price
        self.assertEqual(row["SuggestedOrderQty"], 55)
        self.assertEqual(row["SuggestedOrderValueRial"], 5500)

    def test_incoming_minimum_and_pack_rounding(self):
        incoming = [{"کد مرجع": "A", "وضعیت": "فعال", "تعداد در راه": 50},
                    {"کد مرجع": "A", "وضعیت": "لغو", "تعداد در راه": 1000}]
        row = self.run_model(incoming=incoming, settings_rows=[{"پارامتر": "حداقل سفارش", "مقدار": 7}, {"پارامتر": "ضریب بسته‌بندی", "مقدار": 4}])["orders"][0]
        self.assertEqual(row["SuggestedOrderQty"], 8)

    def test_zero_shortage_does_not_create_minimum_order(self):
        row = self.run_model(incoming=[{"کد مرجع": "A", "وضعیت": "فعال", "تعداد در راه": 100}])["orders"][0]
        self.assertEqual(row["SuggestedOrderQty"], 0)

    def test_manual_forbidden_and_unapproved_ideal(self):
        self.mapping[0]["کنترل سفارش"] = "ممنوع دستی"
        result = self.run_model()
        self.assertEqual(result["orders"][0]["SuggestedOrderQty"], 0)
        self.assertEqual(result["budget"], [])
        self.mapping[0]["کنترل سفارش"] = "مجاز دستی"
        self.mapping[0]["وضعیت بررسی"] = "بررسی نشده"
        self.assertEqual(self.run_model()["budget"], [])

    def test_missing_price_is_not_zero(self):
        self.inventory[0]["UnitPrice"] = None
        result = self.run_model()
        self.assertIsNone(result["orders"][0]["SuggestedOrderValueRial"])
        self.assertIsNone(result["budget"][0]["IdealValueRial"])

    def test_all_stocks_recalculate_incoming_once(self):
        self.inventory += [dict(ItemCode="A", StockId=2, StockTitle="دوم", Quantity=5, UnitPrice=100)]
        self.sales += [dict(self.sales[0], StockId=2, StockTitle="دوم")]
        result = self.run_model(incoming=[{"کد مرجع": "A", "وضعیت": "فعال", "تعداد در راه": 10}])
        all_stocks = next(r for r in result["orders"] if r["StockId"] is None)
        self.assertEqual(all_stocks["SuggestedOrderQty"], 110)
        self.assertNotEqual(all_stocks["SuggestedOrderQty"], sum(r["SuggestedOrderQty"] for r in result["orders"] if r["StockId"] is not None))

    def test_turnover_averages_snapshots_after_grouping_similar_items(self):
        monthly = [dict(ItemCode="A", StockId=1, SnapshotDate="2026-09-30", ClosingQty=10),
                   dict(ItemCode="B", StockId=1, SnapshotDate="2026-09-30", ClosingQty=10),
                   dict(ItemCode="A", StockId=1, SnapshotDate="2026-10-19", ClosingQty=40)]
        row = self.run_model(monthly=monthly)["turnover"][0]
        self.assertEqual(row["AverageInventoryQty12M"], 30)
        self.assertEqual(row["TurnoverRate"], 12)
        self.assertEqual(row["InventoryDays"], Decimal(365) / 12)

    def test_turnover_keeps_all_order_controls_without_history(self):
        for control in ("خودکار", "مجاز دستی", "ممنوع دستی"):
            with self.subTest(control=control):
                self.mapping[0]["کنترل سفارش"] = control
                rows = self.run_model(sales=[], monthly=[])["turnover"]
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["OrderControl"], control)
                self.assertEqual(rows[0]["CurrentItemStock"], 10)
                self.assertIsNone(rows[0]["TurnoverRate"])

    def test_returns_reduce_net_sales(self):
        self.sales += [dict(self.sales[0], Quantity=-72)]
        self.assertEqual(self.run_model()["orders"][0]["AverageMonthlyNetSales"], 8)

    def test_reconciliation_uses_codes_not_titles(self):
        result = self.run_model()["reconcile"]
        self.assertEqual({(r["ItemCode"], r["MismatchSide"]) for r in result}, {("B", "فقط در پورتال"), ("C", "فقط در سپیدار")})

    def test_invalid_or_duplicate_settings_rejected(self):
        with self.assertRaises(ValueError):
            self.run_model(settings_rows=[{"پارامتر": "دوره بررسی فروش", "مقدار": 0}])
        with self.assertRaises(ValueError):
            self.run_model(mapping_rows=[self.mapping[0], self.mapping[0]])

    def test_edate_leap_boundary(self):
        self.assertEqual(shift_months(date(2024, 3, 31), -1), date(2024, 2, 29))


if __name__ == "__main__":
    unittest.main()
