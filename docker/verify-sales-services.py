"""Read-only reconciliation of the live sales and after-sales classification."""

from decimal import Decimal
from test_support import init_site

init_site()

import frappe
from saeenaria_portal.sales_reports import service

try:
    view = service.report()
    snapshot = view["snapshot"]
    assert snapshot and snapshot["crm_metadata"]["available"]
    invoices = [r for r in snapshot["invoices"] if view["start"] <= r["date"] <= view["end"] and not r.get('excluded')]
    repairs = [r for r in invoices if r.get("is_repair")]
    mapped = [r for r in invoices if not r.get("is_repair") and r.get("mapped")]
    unmapped = [r for r in invoices if not r.get("is_repair") and not r.get("mapped")]
    assert len(repairs) + len(mapped) + len(unmapped) == len(invoices)
    assert all(r["channel"] == "after_sales" and r.get("repair_reason") for r in repairs)
    assert not ({r["key"] for r in repairs} & set(snapshot.get("suggestions", {})))
    financial = sum(Decimal(str(r.get("actual") or 0)) for r in snapshot["rows"])
    accounted = sum(Decimal(str(r["amount"])) for r in mapped)
    assert abs(financial - accounted) < Decimal("0.01"), (financial, accounted)
    assert all(r["channel"] in ("consumer", "reseller") for r in snapshot["rows"])
    print({"month": view["month"], "total_documents": len(invoices), "assigned_sales": len(mapped), "unassigned_sales": len(unmapped), "after_sales": len(repairs), "financial_reconciliation": "passed"})
finally:
    frappe.db.rollback()
    frappe.destroy()
