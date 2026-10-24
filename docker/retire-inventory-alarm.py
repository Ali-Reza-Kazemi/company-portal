import os,json
from pathlib import Path
os.chdir('/home/frappe/workspace/portal-bench/sites')
import frappe
frappe.init(site='portal.localhost');frappe.connect();frappe.set_user('Administrator')
from saeenaria_portal.purchase_reports.workflow import owner
try:
 template=frappe.get_doc('Portal Template','INVPLAN-lead')
 actions=[frappe.get_doc('Portal Action',name) for name in frappe.get_all('Portal Action',filters={'responsible':owner(),'schedule_key':['like','INVPLAN-lead:%'],'status':['not in',['Completed','Cancelled']]},pluck='name')]
 folder=Path(frappe.get_site_path('private','plan-revision-backups'));folder.mkdir(parents=True,exist_ok=True)
 path=folder/('remove-alarm-'+frappe.generate_hash(length=12)+'.json');path.write_text(json.dumps({'template':template.as_dict(),'actions':[d.as_dict() for d in actions]},ensure_ascii=False,default=str),encoding='utf-8');path.chmod(0o600)
 template.enabled=0;template.save(ignore_permissions=True)
 for doc in actions:
  doc.status='Cancelled';doc.obstacle='بخش ثبت آلارم و اتصال رسید طبق درخواست کاربر حذف شد؛ این فعالیت دیگر لازم نیست.';doc.save(ignore_permissions=True)
 frappe.db.commit()
 print(json.dumps({'disabled_template':template.name,'retired_actions':len(actions),'backup':str(path)},ensure_ascii=False))
except Exception:frappe.db.rollback();raise
finally:frappe.destroy()
