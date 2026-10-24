"""Connection contract tests. No network access or real credentials are used."""

import ssl
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from saeenaria_portal.purchase_reports.sources import connection, tls_options


def rejects(config, kind="mysql"):
    try:
        tls_options(kind, config)
    except ValueError:
        return
    raise AssertionError("Invalid TLS policy accepted")


with TemporaryDirectory() as folder:
    ca = Path(folder) / "ca.pem"
    ca.write_text("Driver mocks validate options, not certificate contents")
    config = {
        "require_tls": True,
        "mysql": {
            "host": "mysql.example.invalid",
            "database": "fixture",
            "user": "reader",
            "password": "fixture",
            "tls": {"enabled": True, "ca_file": str(ca)},
        },
        "sqlserver": {
            "server": "sql.example.invalid",
            "database": "fixture",
            "user": "reader",
            "password": "fixture",
            "tls": {"enabled": True, "ca_file": str(ca)},
        },
    }
    assert tls_options("mysql", config)["ssl_verify_identity"]
    assert tls_options("sqlserver", config)["enc_login_only"] is False
    rejects({"require_tls": True, "mysql": {}})
    rejects({"mysql": {"tls": {"enabled": "false"}}})
    rejects({"mysql": {"tls": {"enabled": True, "ca_file": str(ca) + ".missing"}}})
    rejects({"require_tls": "false"})
    rejects([])
    rejects({"mysql": None})
    rejects({}, kind="unknown")
    assert tls_options("mysql", {}) == {}
    mysql = MagicMock()
    mysql._sock = MagicMock(spec=ssl.SSLSocket)
    with patch("pymysql.connect", return_value=mysql) as connect:
        with connection("mysql", config):
            pass
        assert connect.call_args.kwargs["ssl_verify_cert"] is True
        statements = [
            c.args[0]
            for c in mysql.cursor.return_value.__enter__.return_value.execute.call_args_list
        ]
        assert statements == [
            "SET TRANSACTION READ ONLY",
            "START TRANSACTION WITH CONSISTENT SNAPSHOT",
        ]
        mysql.rollback.assert_called_once()
        mysql.close.assert_called_once()
    insecure = MagicMock()
    insecure._sock = object()
    with patch("pymysql.connect", return_value=insecure):
        try:
            with connection("mysql", config):
                raise AssertionError("TLS downgrade accepted")
        except ValueError:
            pass
        insecure.cursor.assert_not_called()
        insecure.close.assert_called_once()
    sql = MagicMock()
    with patch("pytds.connect", return_value=sql) as connect:
        with connection("sqlserver", config):
            pass
        assert connect.call_args.kwargs["readonly"] is True
        assert connect.call_args.kwargs["validate_host"] is True
        assert connect.call_args.kwargs["cafile"] == str(ca)
        sql.close.assert_called_once()
    sql = MagicMock()
    sql.rollback.side_effect = RuntimeError("fixture rollback failure")
    with patch("pytds.connect", return_value=sql):
        try:
            with connection("sqlserver", config):
                pass
        except RuntimeError:
            pass
        sql.close.assert_called_once()
print(
    "PASS TLS policy validation, CA and hostname verification options, downgrade denial, read-only transaction and connection cleanup"
)
