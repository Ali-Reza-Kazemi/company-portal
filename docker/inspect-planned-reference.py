import os,json
os.chdir('/home/frappe/workspace/portal-bench/sites')
import frappe
frappe.init(site='portal.localhost');frappe.connect();frappe.set_user('Administrator')
for code in ['1201080147','WHY.240']:
 print(json.dumps({'code':code,'catalog':frappe.db.get_value('Portal Product Catalog',{'item_code':code},['name','item_code','item_title','category','reference_code','review_status','order_control','source_present','needs_completion','modified'],as_dict=True)},ensure_ascii=False,default=str))
frappe.destroy()
