"""Automatic output classification, isolated from the installed company's plan."""
import frappe
from test_support import init_site
init_site()
from frappe.utils import today
from saeenaria_portal.automatic_work import automatic_source, automatic_action, automatic_template
from saeenaria_portal.testing import portal_fixtures
from saeenaria_portal.purchase_reports import workflow as w
from saeenaria_portal import api

try:
 with portal_fixtures() as f:
  for code in ('cancel','capital','slow','turnover','cash'):
   assert automatic_template('INVPLAN-'+code)
   assert automatic_action('INVPLAN-'+code+':2099-01-01')
  metric=frappe.get_doc(dict(doctype='Portal Metric',domain=f.domains[0],title='Test metric',definition='Test',unit='count',direction='Higher')).insert()
  value=frappe.get_doc(dict(doctype='Portal Metric Value',metric=metric.name,domain=f.domains[0],responsible=f.employee,period_start='2099-01-01',period_end='2099-01-07',actual=7,data_status='Valid',source='پایش خودکار موجودی / TEST',is_demo=0)).insert()
  action=frappe.get_doc(dict(doctype='Portal Action',domain=f.domains[0],responsible=f.employee,title='Test automatic',due_date=today(),schedule_key='INVPLAN-cancel:'+f.token,status='Completed',progress=100,result='Test',is_demo=0)).insert()
  assert automatic_source(value) and automatic_source(action)
  for doc in (value,action):
   assert not frappe.db.exists('Portal Activity Review',{'source_key':doc.doctype+':'+doc.name})
  assert action.name not in [row.name for row in api.dashboard(domain=f.domains[0])['actions']]
  human=frappe.get_doc(dict(doctype='Portal Action',domain=f.domains[0],responsible=f.employee,title='Test manual',due_date=today(),status='Completed',progress=100,result='Test',is_demo=0)).insert()
  assert not automatic_source(human)
  assert frappe.db.exists('Portal Activity Review',{'source_key':human.doctype+':'+human.name})
  try:w.submit('unused');raise AssertionError('automatic report submission accepted')
  except frappe.ValidationError:pass
 print('PASS automatic outputs hidden and excluded from review, manual actions remain reviewable, automatic report submission denied')
finally:
 frappe.db.rollback();frappe.destroy()
