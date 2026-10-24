import http.cookiejar
import json
import os
import re
import urllib.parse
import urllib.request
from urllib.error import HTTPError

import frappe


def run():
    jar = http.cookiejar.CookieJar()
    client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    # Service resolves itself through localhost; preserve the configured site Host.
    base = os.environ.get("PORTAL_TEST_HTTP_URL", "http://127.0.0.1:8000").rstrip("/")
    csrf_token = ""

    def request(path, data=None):
        headers = {"Host": frappe.local.site}
        if data is not None:
            if csrf_token:
                headers["X-Frappe-CSRF-Token"] = csrf_token
            data = urllib.parse.urlencode(data).encode()
        return client.open(
            urllib.request.Request(base + path, data=data, headers=headers), timeout=30
        )

    request(
        "/api/method/login",
        {"usr": "Administrator", "pwd": os.environ["ADMIN_PASSWORD"]},
    ).read()
    try:
        html = request("/portal").read().decode()
        csrf_token = re.search(r'<meta name="csrf-token" content="([^"]+)"', html).group(1)
        assert '<html lang="fa" dir="rtl">' in html
        assert "ثبت اقدام کاری" in html and "نتایج شاخص‌های عملکرد" in html
        assert "is_demo" in html
        data = json.loads(request("/api/method/saeenaria_portal.api.dashboard").read())["message"]
        expected = set(frappe.get_all("Portal Domain", pluck="name", limit_page_length=0))
        actual = {row["name"] for row in data["domains"]}
        assert actual <= expected and len(actual) == min(100, len(expected))
        assert all(not row["is_demo"] for row in data["actions"])
        request("/portal-import").read()
        assert request("/assets/saeenaria_portal/js/calendar.js").status == 200
        exported = request(
            "/api/method/saeenaria_portal.api.export_actions", {"names": "[]"}
        ).read()
        assert "عنوان" in exported.decode("utf-8-sig")
        try:
            request("/api/method/saeenaria_portal.services.account.my_account")
        except HTTPError as error:
            assert error.code == 403
        else:
            raise AssertionError("Internal service exposed as HTTP API")
        return {
            "authenticated_dashboard": "passed",
            "rtl_markup": "passed",
            "configured_domains": "passed",
            "demo_separation": "passed",
            "import_page": "passed",
            "calendar_asset": "passed",
            "csrf_export": "passed",
            "internal_service_denied": "passed",
        }
    finally:
        request("/api/method/logout", {}).read()
