"""Rollback-only permissions, encrypted credentials, settings revision, and month boundaries."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import frappe
from saeenaria_portal.sales_reports import service
from test_support import init_site

init_site()

try:
    assert service.bounds("۱۴۰۵-۰۸")[1].isoformat() == "2026-10-23"
    assert service.bounds("1405-01")[3].isoformat() == "2026-02-20"
    assert frappe.db.exists("Portal Domain", "sales")
    initial = service.report("1405-08")
    service.save(
        "target",
        dict(
            month="1405-08",
            seller="fixture-user",
            channel="consumer",
            target=1000,
            discount_limit=5,
        ),
        initial["revision"],
    )
    after = service.report("1405-08")
    assert any(t["seller"] == "fixture-user" for t in after["targets"])
    invoice = next(
        row
        for row in after["snapshot"]["invoices"]
        if row.get("customer_id") and not row.get("mapped") and not row.get("is_repair") and row.get('quotation_status') not in ('missing','unresolved')
    )
    seller = next(iter(after["directory"]["seller_choices"]))
    service.save("invoice", dict(month="1405-08",key=invoice["key"],seller=seller,channel="consumer"), after["revision"])
    remembered = service.report("1405-08")
    assert remembered["customer_references"][invoice["customer_id"]]["seller"] == seller
    from saeenaria_portal.sales_reports.calculations import assignment_for
    assert assignment_for(dict(DocumentType="Sale",DocumentId="future-test",CustomerId=invoice["customer_id"],DocumentDate="2027-01-01"),service.settings())["seller"] == seller
    # Keep subsequent date-rule assertions independent of the manual override.
    current = service.settings()
    current["invoices"].pop(invoice["key"])
    service.save_config(current)
    after = service.report("1405-08")
    rule_values = dict(
        month="1405-08",
        customer_id=invoice["customer_id"],
        from_date="1405-07-01",
        seller=seller,
        channel="consumer",
    )
    service.save("customer_rule", rule_values, after["revision"])
    with_rule = service.report("1405-08")
    assert any(
        rule["customer_id"] == invoice["customer_id"]
        for rule in with_rule["customer_rules"]
    )
    assert next(
        row for row in with_rule["snapshot"]["invoices"] if row["key"] == invoice["key"]
    )["seller"] == seller
    service.save(
        "customer_rule", {**rule_values, "channel": "reseller"}, with_rule["revision"]
    )
    corrected = service.report("1405-08")
    assert any(
        rule["customer_id"] == invoice["customer_id"] and rule["channel"] == "reseller"
        for rule in corrected["customer_rules"]
    )
    assert next(
        row for row in corrected["snapshot"]["invoices"] if row["key"] == invoice["key"]
    )["channel"] == "reseller"
    rule_id = next(
        rule["id"] for rule in corrected["customer_rules"]
        if rule["customer_id"] == invoice["customer_id"] and rule["from_jalali"] == "1405-07-01"
    )
    moved_values = {**rule_values, "rule_id": rule_id, "from_date": "1405-07-02"}
    service.save("customer_rule", moved_values, corrected["revision"])
    moved = service.report("1405-08")
    assert len([rule for rule in moved["customer_rules"] if rule["id"] == rule_id]) == 1
    assert next(rule for rule in moved["customer_rules"] if rule["id"] == rule_id)["from_jalali"] == "1405-07-02"
    service.save("customer_rule_delete", moved_values, moved["revision"])
    assert not any(
        rule["customer_id"] == invoice["customer_id"]
        for rule in service.report("1405-08")["customer_rules"]
    )
    try:
        service.save(
            "target",
            dict(month="1405-08", seller="fixture-user", channel="consumer", target=1000),
            initial["revision"],
        )
        raise AssertionError("Stale edit accepted")
    except frappe.ValidationError:
        pass
    try:
        service.save(
            "target",
            dict(month="1405-08", seller="fixture-user", channel="consumer", target=-1),
            service.report("1405-08")["revision"],
        )
        raise AssertionError("Negative target accepted")
    except frappe.ValidationError:
        pass
    with patch("saeenaria_portal.sales_reports.service.settings", return_value={}):
        assert service.settings() == {}
    # No real API key is required, transmitted, or printed by this test.
    service.configure_api("fixture-api-key-do-not-use")
    assert (
        frappe.get_single(service.DT).get_password("didar_api_key") == "fixture-api-key-do-not-use"
    )
    assert "fixture-api-key-do-not-use" not in str(service.report("1405-08"))
    current = service.settings()
    service.save_config(current)
    assert (
        frappe.get_single(service.DT).get_password("didar_api_key") == "fixture-api-key-do-not-use"
    )
    with (
        patch.object(service, "admin", return_value=False),
        patch.object(service, "roles", return_value=set()),
        patch.object(service, "managed_domains", return_value=["inventory"]),
    ):
        assert not service.allowed("unrelated-manager")
        with patch.object(service, "managed_domains", return_value=["sales"]):
            assert service.allowed("sales-manager")
        with patch.object(service, "roles", return_value={"Company Director"}):
            assert service.allowed("director")
        try:
            service.configure_api("fixture-api-key")
            raise AssertionError("Nonadministrator key update allowed")
        except frappe.PermissionError:
            pass
    with (
        TemporaryDirectory() as temporary,
        patch.object(service, "folder", return_value=Path(temporary)),
    ):
        snapshot = Path(temporary) / "1405-08-20000101000000.json"
        snapshot.write_text('{"preserved": true}')
        with patch(
            "saeenaria_portal.sales_reports.sources.load",
            side_effect=RuntimeError("sensitive connection string"),
        ):
            assert "error" in service.build("1405-08")
        assert service.read_latest("1405-08") == {"preserved": True}
        assert "sensitive" not in (Path(temporary) / "1405-08.error").read_text()
        service.set_job_state("1405-08", "queued")
        status = service.report("1405-08")
        assert status["busy"] and not status["error"]
    frappe.set_user("Guest")
    for call in (
        lambda: service.report("1405-08"),
        lambda: service.refresh("1405-08"),
        lambda: service.configure_api("fixture-api-key"),
        lambda: service.save("target", {}, ""),
    ):
        try:
            call()
            raise AssertionError("Guest access allowed")
        except frappe.PermissionError:
            pass
    print(
        "PASS sales month boundaries, target validation, stale-edit rejection, encrypted API key, permission matrix, failure preservation and Guest authorization"
    )
finally:
    frappe.db.rollback()
    frappe.destroy()
