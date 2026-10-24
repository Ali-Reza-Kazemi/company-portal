import os,json
os.chdir('/home/frappe/workspace/portal-bench/sites')
import frappe
frappe.init(site='portal.localhost');frappe.connect();frappe.set_user('Administrator')
from saeenaria_portal.purchase_reports import general_settings as g
try:
 result=g.initialize()
 data=g.overview()
 frappe.enqueue('saeenaria_portal.purchase_reports.general_settings.recalculate',queue='long',timeout=5400,job_id='purchase-policy:'+frappe.local.site+':'+str(data['revision']),deduplicate=True,revision=data['revision'])
 frappe.db.commit()
 print(json.dumps({'migration':result,'revision':data['revision'],'parameters':len(data['schema']),'history_records':len(data['history'])},ensure_ascii=False,default=str))
except Exception:frappe.db.rollback();raise
finally:frappe.destroy()
