import os,json
os.chdir('/home/frappe/workspace/portal-bench/sites')
import frappe
frappe.init(site='portal.localhost');frappe.connect();frappe.set_user('Administrator')
from saeenaria_portal.purchase_reports.workflow import owner
u=owner()
print(json.dumps({'user':u,'actions':frappe.get_all('Portal Action',filters={'responsible':u},fields=['name','title','status','progress','schedule_key','creation','obstacle','is_demo'],order_by='creation asc'),'templates':frappe.get_all('Portal Template',filters={'responsible':u},fields=['name','title','enabled'])},ensure_ascii=False,default=str))
frappe.db.rollback();frappe.destroy()
