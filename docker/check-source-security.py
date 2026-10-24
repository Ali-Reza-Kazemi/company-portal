"""Report local connection-policy metadata without printing credentials or hosts."""
import json
from pathlib import Path
import stat

import frappe
from test_support import init_site

init_site()
from saeenaria_portal.purchase_reports.sources import credentials

try:
    config = credentials()
    path = Path(frappe.get_site_path("private", "purchase-order-connections.json"))
    result = {"connection_file_exists":path.exists(), "strict_tls":bool(config.get("require_tls")),
              "explicit_inventory_owner":bool(frappe.conf.get("inventory_reporting_owner"))}
    if path.exists():
        result["connection_file_mode"] = oct(stat.S_IMODE(path.stat().st_mode))
    for kind in ("mysql", "sqlserver"):
        settings = config.get(kind, {})
        tls = settings.get("tls", {})
        ca = tls.get("ca_file")
        result[kind] = {"configured":bool(settings), "tls_enabled":tls.get("enabled",bool(ca)),
                        "ca_available":bool(isinstance(ca,str) and Path(ca).is_file())}
    print(json.dumps(result))
finally:
    frappe.destroy()
