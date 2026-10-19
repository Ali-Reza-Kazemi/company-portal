import json
import os
import frappe
os.chdir('/home/frappe/workspace/portal-bench/sites')
frappe.init(site='portal.localhost')
frappe.connect()
frappe.set_user('Administrator')
old_apps=[app for app in frappe.get_installed_apps() if app != 'frappe']
assert len(old_apps)==1, 'Unexpected app configuration'
old=old_apps[0]
new='saeenaria_portal'
for module in frappe.get_all('Module Def',filters={'app_name':old},fields=['name']):
    target='Saeenaria Portal'
    if module.name != target:
        frappe.db.set_value('Module Def',module.name,'custom',1)
        frappe.rename_doc('Module Def',module.name,target,force=True)
    frappe.db.set_value('Module Def',target,{'app_name':new,'module_name':target,'custom':0})
if frappe.db.exists('DocType','Installed Application') and frappe.get_meta('Installed Application').has_field('app_name'):
    for row in frappe.get_all('Installed Application',filters={'app_name':old},pluck='name'):
        frappe.db.set_value('Installed Application',row,'app_name',new)
frappe.db.set_global('installed_apps',json.dumps(['frappe',new]))
frappe.db.commit()
frappe.clear_cache()
print('Application registry and module renamed successfully')
frappe.destroy()
