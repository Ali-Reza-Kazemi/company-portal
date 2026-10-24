"""A known product missing from a limited report must remain discoverable."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import frappe
from test_support import init_site

init_site()
from saeenaria_portal.purchase_reports import product_catalog as catalog, service
from saeenaria_portal.testing import portal_fixtures

try:
    with portal_fixtures() as fixture, TemporaryDirectory() as folder, patch.object(service,"storage",return_value=Path(folder)):
        code = "SEARCH-"+fixture.token+".5034"
        catalog.insert_many([dict(item_code=code,item_title="Test bearing",reference_code=code,
            category="Test",review_status="تأیید شده",needs_completion=0,source_present=1)])
        unavailable=service.report("ideal",filters={"search":code})
        assert not unavailable["available"] and unavailable["catalog_matches"]==[]
        service.write_snapshot("combined",{"reports":{
            "orders":[dict(ItemCode=code,ItemTitle="Test bearing",StockId=None,
                StockTitle="همه انبارها",SuggestedOrderQty=0,OrderEligibility="فروش موردی/رسوبی")],
            "ideal":[], "reconcile":[]}})
        for name in ("ideal","reconcile"):
            result=service.report(name,filters={"search":code.lower()})
            assert result["total"]==0 and result["rows"]==[]
            matches=result["catalog_matches"]
            assert len(matches)==1 and matches[0]["code"]==code
            params=parse_qs(urlsplit(matches[0]["url"]).query)
            assert params=={"search":[code],"status":["all"]}
            assert urlsplit(matches[0]["url"]).path=="/portal-products"
            assert service.search_suggestions(name,code.lower())[0]["value"]==code
            assert not service.report(name)["catalog_matches"]
            assert not service.report(name,filters={"search":"ABSENT-"+fixture.token})["catalog_matches"]
        ideal=service.report("ideal",filters={"search":code})
        assert "فروش موردی/رسوبی" in ideal["catalog_matches"][0]["reason"]
        reconcile=service.report("reconcile",filters={"search":code})
        assert "اطلاعات تکمیلی آن کامل است" in reconcile["catalog_matches"][0]["reason"]
        assert catalog.listing(code.lower(),"all")["matched"]==1
        assert catalog.listing(code.lower(),"pending")["matched"]==0
        snapshot=service.read_snapshot("combined")
        snapshot["reports"]["ideal"]=[dict(ItemCode=code,ItemTitle="Test bearing",StockTitle="Test",Category="Test",CurrentItemStock=3,IdealQty=4)]
        service.write_snapshot("combined",snapshot)
        present=service.report("ideal",filters={"search":code})
        assert present["total"]==1 and present["catalog_matches"]==[]
        frappe.set_user("Guest")
        for fn,kwargs in [(service.report,{"name":"ideal","filters":{"search":code}}),
                          (service.search_suggestions,{"name":"reconcile","query":code})]:
            try:
                fn(**kwargs)
            except frappe.PermissionError:
                pass
            else:
                raise AssertionError("Guest catalog disclosure")
    print("PASS product discovery: lowercase code, dormant ideal exclusion explained, complete catalog item absent from mismatches explained, suggestions, filtered catalog link, unknown queries, no duplicate rows, Guest denial")
finally:
    frappe.db.rollback()
    frappe.destroy()
