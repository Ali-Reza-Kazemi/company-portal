"""Native incoming orders; fixtures roll back and no real recalculation is queued."""

from unittest.mock import patch
from uuid import uuid4

import frappe
from saeenaria_portal.purchase_reports import incoming_orders as incoming
from saeenaria_portal.purchase_reports import product_catalog, sources, workflow
from test_support import init_site

init_site()

try:
    reference = frappe.get_all(
        product_catalog.DT,
        filters={"needs_completion": 0, "source_conflict": 0},
        fields=["item_code", "reference_code"],
        limit_page_length=0,
    )
    reference = next(r.item_code for r in reference if r.item_code == r.reference_code)
    data = dict(
        order_number="test-" + uuid4().hex,
        reference_code=reference,
        quantity="2.5",
        status="Active",
    )
    with patch.object(frappe, "enqueue") as queue:
        saved = incoming.save(data)
        assert saved["name"].startswith("IN-")
        assert queue.call_args.kwargs["enqueue_after_commit"]
        assert incoming.overview(search=data["order_number"])["total"] == 1
        assert incoming.rows() and any(
            r["کد مرجع"] == reference and r["تعداد در راه"] == 2.5 for r in incoming.rows()
        )
        for value in (True, "NaN", "Infinity", "-1", "0", "0.0000000001", "1000000001"):
            try:
                incoming.save({**data, "quantity": value})
            except frappe.ValidationError:
                pass
            else:
                raise AssertionError("Invalid quantity accepted: " + str(value))
        try:
            incoming.save({**data, "name": saved["name"], "quantity": 3}, "2000-01-01")
        except frappe.TimestampMismatchError:
            pass
        else:
            raise AssertionError("Stale edit accepted")
        modified = incoming.save(
            {"name": saved["name"], "quantity": 0, "status": "Received"}, saved["modified"]
        )
        assert incoming.overview(search=data["order_number"])["total"] == 0
        assert (
            incoming.overview(search=data["order_number"], status="all")["rows"][0].status
            == "Received"
        )
        with patch.object(
            sources, "connection", side_effect=AssertionError("External policy read")
        ):
            assert workflow.settings_bundle()["IncomingOrders"] == incoming.rows()
        for user in ("Guest",):
            frappe.set_user(user)
            for fn, args in ((incoming.overview, {}), (incoming.save, {"data": data})):
                try:
                    fn(**args)
                except frappe.PermissionError:
                    pass
                else:
                    raise AssertionError("Unauthorized native order access")
    print(
        "PASS native incoming orders: validated quantities, active-only policy, versioned updates, after-commit refresh, shared local inputs and permissions"
    )
finally:
    frappe.db.rollback()
    frappe.destroy()
