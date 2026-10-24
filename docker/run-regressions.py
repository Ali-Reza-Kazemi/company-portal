"""Run the regression scripts in a configured bench, continuing after failures."""

import argparse
import os
import subprocess
import sys
from pathlib import Path

import frappe
from frappe.utils import get_bench_path
from test_support import init_site

parser = argparse.ArgumentParser()
parser.add_argument("--http", action="store_true", help="Also test the running HTTP server")
args = parser.parse_args()
init_site()
site = frappe.local.site
bench = Path(get_bench_path())


def fixture_counts():
    return (
        frappe.db.count("User", {"name": ["like", "portal-%@example.invalid"]}),
        frappe.db.count("Portal Domain", {"name": ["like", "test-%"]}),
    )


before = fixture_counts()
frappe.destroy()
env = dict(os.environ, PORTAL_TEST_SITE=site, PORTAL_TEST_BENCH=str(bench))
folder = Path(__file__).resolve().parent
checks = [[sys.executable, str(path)] for path in sorted(folder.glob("test-*.py"))]
for method in ("smoke.run", "smoke.extended") + (("http_smoke.run",) if args.http else ()):
    checks.append(["bench", "--site", site, "execute", "saeenaria_portal." + method])
failed = []
for command in checks:
    print("RUN", Path(command[-1]).name, flush=True)
    result = subprocess.run(command, cwd=bench, env=env)
    if result.returncode:
        failed.append(command[-1])
init_site()
try:
    if fixture_counts() != before:
        failed.append("temporary fixture cleanup")
    else:
        print("PASS temporary user/domain counts unchanged", flush=True)
finally:
    frappe.destroy()
print(f"RESULT: {len(checks) - len(failed)}/{len(checks)} checks passed", flush=True)
if failed:
    print("FAILED:", ", ".join(failed))
sys.exit(bool(failed))
