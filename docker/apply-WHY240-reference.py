import os,json
from pathlib import Path
os.chdir('/home/frappe/workspace/portal-bench/sites')
import frappe
frappe.init(site='portal.localhost');frappe.connect();frappe.set_user('Administrator')
from saeenaria_portal.purchase_reports import product_catalog as c
try:
 doc=frappe.get_doc(c.DT,'1201080147')
 folder=Path(frappe.get_site_path('private','product-catalog-backups'));folder.mkdir(parents=True,exist_ok=True)
 backup=folder/('planned-WHY240-'+frappe.generate_hash(length=12)+'.json');backup.write_text(json.dumps({'product':doc.as_dict(),'reference_before':frappe.db.get_value(c.DT,{'item_code':'WHY.240'},'*',as_dict=True)},ensure_ascii=False,default=str),encoding='utf-8');backup.chmod(0o600)
 c.save(doc.name,doc.category,'WHY.240',order_control=doc.order_control,notes=doc.notes or '',expected_modified=str(doc.modified),review_status=doc.review_status)
 doc.reload();reference=frappe.get_doc(c.DT,'WHY.240');listing=c.listing(status='all')
 assert doc.reference_code=='WHY.240' and not doc.needs_completion and reference.is_planned and not reference.source_present
 print(json.dumps({'product':doc.item_code,'reference':reference.item_code,'planned':bool(reference.is_planned),'source_present':bool(reference.source_present),'category_preserved':doc.category,'catalog_total':listing['total'],'pages':listing['pages'],'backup':str(backup)},ensure_ascii=False))
except Exception:frappe.db.rollback();raise
finally:frappe.destroy()
