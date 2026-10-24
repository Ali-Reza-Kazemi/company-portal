"""Read-only comparison of a specific product code in Sepidar and the portal."""
import argparse
import json

import frappe
from test_support import init_site

parser = argparse.ArgumentParser()
parser.add_argument("code")
args = parser.parse_args()
init_site()
from saeenaria_portal.purchase_reports import product_catalog as catalog
from saeenaria_portal.purchase_reports.sources import connection, credentials, rows
from saeenaria_portal.purchase_reports import service

try:
    result = {"code":args.code, "catalog_active":catalog.active(),
              "last_sync":frappe.db.get_single_value(catalog.SETTINGS,"last_sync"),
              "last_result":frappe.db.get_single_value(catalog.SETTINGS,"last_result")}
    result["local"] = frappe.get_all(catalog.DT,
        filters={"item_code":["like","%"+args.code+"%"]}, fields=catalog.FIELDS, limit_page_length=20)
    result["listing"] = {status:catalog.listing(args.code,status)["matched"] for status in ("all","pending","reviewed","missing","new")}
    result["reports"] = {}
    for family in ("combined","mysql"):
        snapshot = service.read_snapshot(family)
        for name, data in snapshot.get("reports",{}).items():
            found = [row for row in data if any(str(row.get(field,"")).casefold()==args.code.casefold()
                     for field in ("ItemCode","ReferenceCode","EffectiveReference"))]
            if found:
                result["reports"][name] = {"updated_at":snapshot.get("updated_at"),"source_rows":len(found),
                    "visible_search_rows":len(service.filtered_rows(name,{"search":args.code})[0]),
                    "sample":[{k:row.get(k) for k in ("ItemCode","ReferenceCode","EffectiveReference","StockTitle","SuggestedOrderQty","CurrentStock","ReferenceInventoryQty","OrderEligibility")} for row in found[:4]]}
    with connection("sqlserver",credentials()) as conn:
        result["sepidar"] = rows(conn,
            "SELECT TOP (20) it.ItemID AS ItemId, it.Code AS ItemCode, it.Title AS ItemTitle FROM INV.Item it WHERE LOWER(LTRIM(RTRIM(CAST(it.Code AS nvarchar(100))))) LIKE %s",
            ("%"+args.code.strip().lower()+"%",))
    print(json.dumps(result,ensure_ascii=False,default=str))
finally:
    frappe.db.rollback()
    frappe.destroy()
