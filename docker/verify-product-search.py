"""Verify the reported product using authenticated HTTP, without changing its data."""
import argparse
import http.cookiejar
import json
import os
import re
import urllib.parse
import urllib.request

import frappe
from test_support import init_site

parser = argparse.ArgumentParser()
parser.add_argument("code")
args = parser.parse_args()
init_site()
client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
base = os.environ.get("PORTAL_TEST_HTTP_URL","http://127.0.0.1:8000")
csrf = ""


def request(path, data=None):
    headers = {"Host":frappe.local.site}
    if data is not None:
        headers["X-Frappe-CSRF-Token"] = csrf
        data = urllib.parse.urlencode(data).encode()
    return client.open(urllib.request.Request(base+path,data=data,headers=headers),timeout=30)


try:
    request("/api/method/login",{"usr":"Administrator","pwd":os.environ["ADMIN_PASSWORD"]}).read()
    page=request("/portal-purchase").read().decode()
    csrf=re.search(r'<meta name="csrf-token" content="([^"]+)"',page).group(1)
    assert "purchase-reports.js?v=8" in page
    result = {}
    for name in ("ideal","reconcile"):
        query=urllib.parse.urlencode({"name":name,"filters":json.dumps({"search":args.code})})
        report=json.loads(request("/api/method/saeenaria_portal.purchase_reports.service.report?"+query).read())["message"]
        match=next(item for item in report["catalog_matches"] if item["code"].casefold()==args.code.casefold())
        assert report["total"]==0
        catalog_page=request(match["url"]).read().decode()
        assert "product-catalog.js?v=5" in catalog_page
        result[name]={"title":match["title"],"reason":match["reason"],"catalog_url":match["url"]}
    print(json.dumps(result,ensure_ascii=False))
finally:
    if csrf:
        request("/api/method/logout",{}).read()
    frappe.destroy()
