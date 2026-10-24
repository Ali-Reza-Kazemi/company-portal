import os,json
os.chdir('/home/frappe/workspace/portal-bench/sites')
import frappe
frappe.init(site='portal.localhost');frappe.connect();frappe.set_user('Administrator')
from saeenaria_portal.purchase_reports.workflow import settings_bundle
from saeenaria_portal.purchase_reports.sources import connection,credentials,rows,QUERIES
bundle=settings_bundle();mapping=bundle['ProductMapping']
with connection('sqlserver',credentials()) as c:items=rows(c,QUERIES['SepidarItems']['sql'])
print(json.dumps({'mapping_count':len(mapping),'items_count':len(items),'keys':sorted(set(k for r in mapping for k in r)),'sample':mapping[:2],'categories':sorted({str(r.get('دسته‌بندی اختصاصی') or '') for r in mapping}),'reviews':sorted({str(r.get('وضعیت بررسی') or '') for r in mapping}),'controls':sorted({str(r.get('کنترل سفارش') or '') for r in mapping})},ensure_ascii=False))
frappe.db.rollback();frappe.destroy()
