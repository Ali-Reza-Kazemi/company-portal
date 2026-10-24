import os,json
from pathlib import Path
os.chdir('/home/frappe/workspace/portal-bench/sites')
import frappe
frappe.init(site='portal.localhost');frappe.connect();frappe.set_user('Administrator')
from saeenaria_portal.purchase_reports import product_catalog as c
try:
 path=Path(frappe.get_site_path('private','product-catalog-backups','initial-393465b3451e.json'));legacy=json.loads(path.read_text(encoding='utf-8'))['mapping'];cleared=0
 with frappe.cache.lock('product-catalog-sync:'+frappe.local.site,timeout=300):
  for old in legacy:
   code=c.text(old.get('کد کالا'));reference=c.text(old.get('کد مرجع دستی')) or c.text(old.get('کد مرجع مؤثر')) or code
   doc=frappe.db.get_value(c.DT,code,['name','category','reference_code','needs_completion'],as_dict=True)
   if doc and doc.needs_completion and (doc.category or '')==c.text(old.get('دسته‌بندی اختصاصی')) and doc.reference_code==reference and frappe.db.exists(c.DT,reference):
    frappe.db.set_value(c.DT,doc.name,'needs_completion',0);cleared+=1
  frappe.db.commit()
 print(json.dumps({'preserved_legacy_policies':cleared,'pending_including_source_conflicts':c.listing()['pending'],'new_unclassified':frappe.db.count(c.DT,{'needs_completion':1}),'source_conflicts':frappe.db.count(c.DT,{'source_conflict':1})},ensure_ascii=False))
except Exception:frappe.db.rollback();raise
finally:frappe.destroy()
