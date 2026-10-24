"""Shared configurable site bootstrap for rollback-only integration scripts."""

import os
import sys
from pathlib import Path


def init_site():
    import frappe

    bench = Path(os.environ.get("PORTAL_TEST_BENCH", Path(sys.prefix).parent))
    sites = bench / "sites"
    site = os.environ.get("PORTAL_TEST_SITE")
    if not site:
        candidates = sorted(path.parent.name for path in sites.glob("*/site_config.json"))
        if len(candidates) != 1:
            raise RuntimeError("Set PORTAL_TEST_SITE when the bench has zero or multiple sites")
        site = candidates[0]
    os.chdir(sites)
    frappe.init(site=site, sites_path=str(sites))
    frappe.connect()
    frappe.set_user("Administrator")
