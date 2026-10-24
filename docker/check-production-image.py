"""Offline checks inside a built image; no site or database is needed."""
from importlib.metadata import version
import os
from pathlib import Path

import MySQLdb
import OpenSSL
import pymysql
from pytds import tls

from saeenaria_portal import api
from saeenaria_portal.purchase_reports import workflow, workflow_data, workflow_storage
from saeenaria_portal.services import account, actions, people

assert os.getuid() != 0, "Image must run as an unprivileged user"
assert tls.OPENSSL_AVAILABLE, "SQL Server TLS support unavailable"
assert MySQLdb and OpenSSL and pymysql
assert all((api, workflow, workflow_data, workflow_storage, account, actions, people))
bench = Path("/home/frappe/frappe-bench")
assert Path("/opt/portal-assets/assets.json").is_file()
assert bench.joinpath("apps/frappe/socketio.js").is_file()
constraints = bench.joinpath("apps/saeenaria_portal/constraints-runtime.txt")
for line in constraints.read_text().splitlines():
    if line and not line.startswith("#"):
        name, expected = line.split("==", 1)
        assert version(name) == expected, f"Runtime dependency differs: {name}"
print("PASS non-root image, native database libraries, SQL Server TLS, service imports, bundled assets and all runtime constraints")
