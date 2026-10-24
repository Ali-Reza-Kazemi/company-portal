"""All reports share one native pipeline; no workbook, ETL or MySQL fallback."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import frappe
from saeenaria_portal.purchase_reports import (
    general_settings,
    portal_inputs,
    product_catalog,
    service,
    sources,
)
from test_support import init_site

init_site()

try:
    inputs = {
        "ProductMapping": [{"کد کالا": "A"}],
        "GeneralSettings": [],
        "IncomingOrders": [],
        "metadata": [{"source": "portal-native-v2", "portal_settings_revision": 12}],
    }
    facts = {
        "SepidarItems": [{"ItemCode": "A"}],
        "FactInventory": [dict(ItemCode="A", StockId=1, StockTitle="S", Quantity=10, UnitPrice=5)],
        "FactSales": [],
        "FactMonthlyInventory": [],
    }
    assert all(query["source"] == "sqlserver" for query in sources.QUERIES.values())
    with (
        TemporaryDirectory() as folder,
        patch.object(service, "storage", return_value=Path(folder)),
        patch.object(service, "credentials", return_value={"sqlserver": {"configured": True}}),
        patch.object(service, "extract_sqlserver", return_value=facts),
        patch.object(sources, "connection", side_effect=AssertionError("Legacy source read")),
        patch.object(product_catalog, "active", return_value=True),
        patch.object(product_catalog, "sync_items"),
        patch.object(general_settings, "active", return_value=True),
        patch.object(portal_inputs, "read_inputs", return_value=inputs),
        patch.object(frappe.db, "commit"),
    ):
        service.refresh_data()
        result = service.read_snapshot("combined")
        assert result["processor"] == "portal-native-v2"
        assert set(result["reports"]) == set(service.REPORTS)
        assert len(result["reports"]["sediment"]) == 1
        assert result["settings_at"][0]["portal_settings_revision"] == 12
        assert not service.read_snapshot("state")["errors"]
        assert not (Path(folder) / "mysql.json").exists()
        original = service.read_snapshot

        def native_only(name):
            assert not name.startswith("mysql"), "Legacy cached report read"
            return original(name)

        with patch.object(service, "read_snapshot", side_effect=native_only):
            assert len(service.overview()["reports"]) == 7
            for name in service.REPORTS:
                assert service.report(name)["available"]
    with (
        patch.object(product_catalog, "active", return_value=False),
        patch.object(
            sources, "connection", side_effect=AssertionError("Uninitialized fallback read")
        ),
    ):
        try:
            portal_inputs.read_inputs()
        except frappe.ValidationError:
            pass
        else:
            raise AssertionError("Inactive catalog silently fell back")
    print(
        "PASS native pipeline: all eight reports, SQL-only facts, one atomic family, native policy revision, no legacy source/cache fallback"
    )
finally:
    frappe.db.rollback()
    frappe.destroy()
