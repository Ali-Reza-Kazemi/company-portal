import os,json
from collections import defaultdict
os.chdir('/home/frappe/workspace/portal-bench/sites')
import frappe
frappe.init(site='portal.localhost');frappe.connect();frappe.set_user('Administrator')
from saeenaria_portal.purchase_reports.product_catalog import read_items
from saeenaria_portal.purchase_reports.calculations import key
by=defaultdict(list)
for r in read_items():by[key(r['ItemCode'])].append(r)
print(json.dumps([v for v in by.values() if len(v)>1],ensure_ascii=False));frappe.destroy()
