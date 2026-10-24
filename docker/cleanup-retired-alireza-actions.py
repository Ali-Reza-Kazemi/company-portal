"""Remove explicitly retired Alireza tasks after a private, restorable backup."""
import os,json
from pathlib import Path
os.chdir('/home/frappe/workspace/portal-bench/sites')
import frappe
frappe.init(site='portal.localhost');frappe.connect();frappe.set_user('Administrator')
from saeenaria_portal.purchase_reports.workflow import owner
user=owner()
names=['ACT-00002','ACT-00003','ACT-00004','ACT-00005','ACT-00013','ACT-00014','ACT-00015','ACT-00016','ACT-00047','ACT-00048','ACT-00049','ACT-00054']
try:
 docs=[frappe.get_doc('Portal Action',name) for name in names]
 for doc in docs:
  assert doc.responsible==user and doc.status=='Cancelled' and not doc.is_demo
  assert ('برنامه قدیمی' in (doc.obstacle or '') or 'تکلیف انسانی' in (doc.obstacle or ''))
 preserved=frappe.get_all('Portal Action',filters={'responsible':user,'name':['not in',names]},pluck='name')
 reviews=frappe.get_all('Portal Activity Review',filters={'source_type':'Portal Action','source_name':['in',names]},pluck='name')
 review_docs=[frappe.get_doc('Portal Activity Review',name) for name in reviews]
 folder=Path(frappe.get_site_path('private','retired-action-backups'));folder.mkdir(parents=True,exist_ok=True)
 path=folder/('alireza-'+frappe.generate_hash(length=12)+'.json')
 path.write_text(json.dumps({'actions':[d.as_dict() for d in docs],'reviews':[d.as_dict() for d in review_docs]},ensure_ascii=False,default=str),encoding='utf-8');path.chmod(0o600)
 for d in review_docs:frappe.delete_doc('Portal Activity Review',d.name,ignore_permissions=True)
 for d in docs:frappe.delete_doc('Portal Action',d.name,ignore_permissions=True)
 assert not frappe.db.count('Portal Action',{'name':['in',names]})
 assert all(frappe.db.exists('Portal Action',name) for name in preserved)
 frappe.db.commit()
 print(json.dumps({'deleted_actions':len(docs),'deleted_related_reviews':len(review_docs),'preserved_actions':len(preserved),'backup':str(path),'titles':[d.title for d in docs]},ensure_ascii=False))
except Exception:
 frappe.db.rollback();raise
finally:frappe.destroy()
