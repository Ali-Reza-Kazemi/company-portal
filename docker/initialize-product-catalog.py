import os,json
os.chdir('/home/frappe/workspace/portal-bench/sites')
import frappe
frappe.init(site='portal.localhost');frappe.connect();frappe.set_user('Administrator')
from saeenaria_portal.purchase_reports import product_catalog as c
try:
 result=c.initialize()
 print(json.dumps({'initialization':result,'pending':frappe.db.count(c.DT,{'needs_completion':1}),'source_missing':frappe.db.count(c.DT,{'source_present':0}),'catalog_total':frappe.db.count(c.DT)},ensure_ascii=False,default=str))
 c.auto_sync()
 from saeenaria_portal.purchase_reports.service import _enqueue
 from saeenaria_portal.purchase_reports.workflow import enqueue_daily
 _enqueue();enqueue_daily();frappe.db.commit()
except Exception:frappe.db.rollback();raise
finally:frappe.destroy()
