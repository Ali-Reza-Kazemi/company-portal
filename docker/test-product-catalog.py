"""Rollback-protected catalog synchronization and enrichment tests."""
import os
from unittest.mock import patch
import frappe
from test_support import init_site
init_site()
from saeenaria_portal.purchase_reports import product_catalog as c
from saeenaria_portal.purchase_reports.calculations import calculate
try:
 baseline=[{'ItemCode':r.item_code,'ItemTitle':r.item_title} for r in frappe.get_all(c.DT,filters={'source_present':1},fields=['item_code','item_title'],limit_page_length=0)]
 with patch.object(c,'active',return_value=True):
  a='CATALOG-TEST-001';b='CATALOG-TEST-002';source=baseline+[{'ItemCode':a,'ItemTitle':'کالای تست یک'},{'ItemCode':b,'ItemTitle':'کالای تست دو'}]
  first=c.sync_items(source);assert first['added']==2
  assert c.sync_items(source)['added']==0
  doc=frappe.get_doc(c.DT,a);assert doc.needs_completion and not doc.category
  with patch.object(frappe.db,'commit'),patch('saeenaria_portal.purchase_reports.service._enqueue'),patch('saeenaria_portal.purchase_reports.workflow.enqueue_daily'):
   c.save(a,'گروه تست',a,expected_modified=str(doc.modified))
  doc.reload();assert not doc.needs_completion and doc.reference_code==a
  c.sync_items(baseline+[{'ItemCode':a,'ItemTitle':'نام تازه'},{'ItemCode':b,'ItemTitle':'کالای تست دو'}]);doc.reload()
  assert doc.item_title=='نام تازه' and doc.category=='گروه تست' and doc.reference_code==a and not doc.needs_completion
  c.sync_items(baseline+[{'ItemCode':a,'ItemTitle':'نام تازه'}]);assert not frappe.db.get_value(c.DT,b,'source_present')
  c.sync_items(baseline+[{'ItemCode':a,'ItemTitle':'نام تازه'},{'ItemCode':b,'ItemTitle':'اول'},{'ItemCode':b,'ItemTitle':'دوم'}]);assert frappe.db.get_value(c.DT,b,'source_conflict')
  count=frappe.db.count(c.DT)
  try:c.sync_items([]);raise AssertionError('empty source accepted')
  except frappe.ValidationError:pass
  assert frappe.db.count(c.DT)==count
  result=c.listing(search='CATALOG-TEST',status='all');assert len(result['rows'])==2
  mapping=[{'کد کالا':'P','نام کالا':'pending','CatalogPending':True}]
  reports=calculate(mapping,[],[],[],[],[],[{'ItemCode':'P'}])
  assert reports['orders'][0]['OrderEligibility']=='نیازمند تکمیل اطلاعات' and reports['orders'][0]['SuggestedOrderQty']==0
  assert reports['reconcile'][0]['MismatchSide']=='نیازمند تکمیل اطلاعات'
  frappe.set_user('Guest')
  try:c.listing();raise AssertionError('guest accepted')
  except frappe.PermissionError:pass
 print('PASS: auto-insert, repeat sync, manual edit, source title update without enrichment overwrite, source removal preservation, empty-source protection, listing, pending order exclusion, guest denial.')
finally:frappe.db.rollback();frappe.destroy()
