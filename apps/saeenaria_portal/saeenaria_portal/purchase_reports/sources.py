"""Fixed SELECTs only; credentials and snapshots live outside public files/Git."""

import json
import ssl
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from .calculations import text

QUERIES = json.loads(Path(__file__).with_name("queries.json").read_text(encoding="utf-8"))
MAX_SOURCE_ROWS = 1_000_000


def json_default(value):
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(type(value).__name__)


def credentials():
    import frappe

    path = Path(frappe.get_site_path("private", "purchase-order-connections.json"))
    if not path.exists():
        return {}
    config = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(config, dict):
        raise ValueError("Invalid source connection configuration")
    if frappe.conf.get("purchase_order_require_tls"):
        config["require_tls"] = True
    return config


def tls_options(kind, config):
    """Opt in to verified full-session TLS; strict mode rejects missing CAs."""
    if kind not in ("mysql", "sqlserver"):
        raise ValueError("Unsupported source connection")
    if not isinstance(config, dict):
        raise ValueError("Invalid source connection configuration")
    cfg = config.get(kind, {})
    if not isinstance(cfg, dict):
        raise ValueError("Invalid source connection configuration")
    tls = cfg.get("tls", {})
    if not isinstance(tls, dict) or not isinstance(config.get("require_tls", False), bool):
        raise ValueError("Invalid TLS configuration")
    if not isinstance(tls.get("enabled", True), bool):
        raise ValueError("TLS enabled must be a boolean")
    ca_file = tls.get("ca_file")
    enabled = tls.get("enabled", bool(ca_file))
    if not enabled:
        if config.get("require_tls") or ca_file:
            raise ValueError("Verified TLS is required for source connections")
        return {}
    if not isinstance(ca_file, str) or not Path(ca_file).is_file():
        raise ValueError("TLS requires a readable CA certificate file")
    if kind == "mysql":
        return {"ssl_ca": ca_file, "ssl_verify_cert": True, "ssl_verify_identity": True}
    return {"cafile": ca_file, "validate_host": True, "enc_login_only": False}


@contextmanager
def connection(kind, config):
    options = tls_options(kind, config)
    cfg = config.get(kind, {})
    if not all(cfg.get(k) for k in ("database", "user", "password")):
        raise ValueError("Source connection is not configured")
    if kind == "mysql":
        import pymysql

        conn = pymysql.connect(
            host=cfg["host"],
            port=int(cfg.get("port", 3306)),
            database=cfg["database"],
            user=cfg["user"],
            password=cfg["password"],
            charset="utf8mb4",
            connect_timeout=10,
            read_timeout=180,
            autocommit=False,
            cursorclass=pymysql.cursors.DictCursor,
            **options,
        )
        try:
            # Some driver versions can downgrade when the server lacks TLS.
            if options and not isinstance(conn._sock, ssl.SSLSocket):
                raise ValueError("Source did not establish TLS")
            with conn.cursor() as cursor:
                cursor.execute("SET TRANSACTION READ ONLY")
                cursor.execute("START TRANSACTION WITH CONSISTENT SNAPSHOT")
            yield conn
        finally:
            try:
                conn.rollback()
            finally:
                conn.close()
    else:
        import pytds

        conn = pytds.connect(
            server=cfg["server"],
            port=cfg.get("port"),
            database=cfg["database"],
            user=cfg["user"],
            password=cfg["password"],
            timeout=300,
            login_timeout=10,
            readonly=True,
            autocommit=False,
            as_dict=True,
            appname="Saeenaria Portal Purchase Reports",
            **options,
        )
        try:
            yield conn
        finally:
            try:
                conn.rollback()
            finally:
                conn.close()


def rows(conn, query, params=None):
    # Callers choose queries exclusively from the packaged, reviewed catalog.
    with conn.cursor() as cursor:
        cursor.execute(query, params)
        result = []
        while batch := cursor.fetchmany(2000):
            result.extend(
                {k: text(v) if isinstance(v, str) else v for k, v in r.items()} for r in batch
            )
            if len(result) > MAX_SOURCE_ROWS:
                raise ValueError("Source is larger than the configured safe extraction limit")
        return result


def extract_sqlserver(config):
    with connection("sqlserver", config) as conn:
        return {
            name: rows(conn, q["sql"]) for name, q in QUERIES.items() if q["source"] == "sqlserver"
        }
