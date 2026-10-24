import os,json,hashlib
from pathlib import Path
os.chdir('/home/frappe/workspace/portal-bench/sites')
import frappe
frappe.init(site='portal.localhost');frappe.connect();frappe.set_user('Administrator')
from saeenaria_portal.purchase_reports import product_catalog as c
from saeenaria_portal.purchase_reports.service import _enqueue,read_snapshot
from saeenaria_portal.purchase_reports.workflow import enqueue_daily
try:
 fields=['item_code','category','reference_code','review_status','order_control','notes']
 before=frappe.get_all(c.DT,fields=fields,order_by='item_code',limit_page_length=0)
 result=c.sync_items();frappe.db.commit()
 after=frappe.get_all(c.DT,fields=fields,order_by='item_code',limit_page_length=0)
 assert before==after,'Source sync overwrote enrichment'
 listing=c.listing(status="new");assert len(listing['rows'])==9
 assert frappe.db.exists('Scheduled Job Type',{'method':'saeenaria_portal.purchase_reports.product_catalog.auto_sync','stopped':0})
 _enqueue();enqueue_daily();frappe.db.commit()
 print(json.dumps({'repeat_sync':result,'new_products':len(listing['rows']),'all_pending_or_conflicting':listing['pending'],'manual_fields_preserved':True,'hourly_job_registered':True,'report_errors':read_snapshot('state').get('errors',{})},ensure_ascii=False,default=str))
except Exception:frappe.db.rollback();raise
finally:frappe.destroy()
