"""Isolated immutable snapshot and inventory input regression tests."""
import json
from unittest.mock import patch
import frappe
from test_support import init_site
init_site()
from frappe.utils import getdate,today
from saeenaria_portal.testing import portal_fixtures
from saeenaria_portal.purchase_reports import workflow as w,workflow_math as m

try:
 with portal_fixtures() as f, patch.dict(frappe.conf,{'inventory_reporting_owner':None}):
  if not frappe.db.exists('Portal Domain','inventory'):
   frappe.get_doc(dict(doctype='Portal Domain',domain_code='inventory',title='Test inventory')).insert()
  frappe.get_doc(dict(doctype='Portal Assignment',user=f.employee,domain='inventory',enabled=1,is_manager=1)).insert()
  with patch.dict(frappe.conf,{'inventory_reporting_owner':f.employee}), patch.object(m,'POLICY','TEST-'+f.token):
   name=w.metric_name('cancel')
   frappe.get_doc(dict(doctype='Portal Metric',domain='inventory',title='Test cancellation',definition='Test',unit='percent',direction='Lower')).insert(set_name=name)
   start,end=m.previous_week(getdate(today()))
   payload=dict(kind='Weekly',start=str(start),end=str(end),policy=m.POLICY,basis='Test basis',metrics=[m.metric('cancel','Test',10,'percent')],groups=[],urgency=[],evidence={'deals':[{'state':2,'reason':'نبود کالا','customer':'test-stockout'},{'state':1,'reason':'','customer':'test-won'}]})
   snap=w.save_payload(payload);assert w.save_payload(payload).name==snap.name
   w.publish_values(snap)
   value=frappe.get_doc('Portal Metric Value',{'metric':name,'period_start':start,'period_end':end,'is_demo':0})
   assert value.responsible==f.employee and value.actual==10
   assert not frappe.db.exists('Portal Activity Review',{'source_key':'Portal Metric Value:'+value.name})
   snap.payload='{}'
   try:snap.save(ignore_permissions=True);raise AssertionError('mutable snapshot')
   except frappe.ValidationError:pass
   snap.reload()
   changed=json.loads(snap.payload);changed['metrics'][0]['value']=20
   revision=w.save_payload(changed);w.publish_values(revision)
   assert revision.name!=snap.name and revision.revision==snap.revision+1
   value.reload();modified=value.modified
   changed['planner_asof']='2000-01-01';w.publish_values(w.save_payload(changed))
   value.reload();assert value.modified==modified
   assert 'evidence' not in w.public_snapshot(snap)
   assert w.evidence(snap.name)['total']==1
   frappe.set_user(f.employee)
   try:w.submit(snap.name);raise AssertionError('automatic output submitted')
   except frappe.ValidationError:pass
   frozen=w.freeze_forecast({k:10 for k in m.GROUPS})
   assert set(w.existing_forecast(getdate(frozen['start']),getdate(frozen['end'])))==set(m.GROUPS)
   records=frappe.get_all('Portal Record',filters={'responsible':f.employee,'record_type':'Demand Forecast'},pluck='name')
   record=frappe.get_doc('Portal Record',records[0]);record.quantity=99
   try:record.save();raise AssertionError('forecast baseline mutable')
   except frappe.ValidationError:pass
   with patch.object(w.source,'current_book',return_value=[{'quantity':10}]):
    w.save_event('count','TEST-'+f.token,stock=1,quantity=9)
   with patch.object(w.source,'item_exists',return_value=True):
    alarm=w.save_event('alarm','TEST-'+f.token)
   alarm_doc=frappe.get_doc('Portal Record',alarm['name'])
   with patch.object(w.source,'receipt_options',return_value=[dict(receipt_item=999,receipt_date=str(today()),stock=1,item_code='TEST-'+f.token,quantity=5)]):
    w.link_receipt(alarm_doc.name,999,str(alarm_doc.modified))
   alarm_doc.reload();assert alarm_doc.status=='Received' and alarm_doc.locked
   frappe.set_user('Guest')
   for fn,args in [(w.overview,{}),(w.evidence,{'snapshot':snap.name}),(w.freeze_forecast,{'values':{}})]:
    try:fn(**args);raise AssertionError('Guest access')
    except frappe.PermissionError:pass
 print('PASS inventory snapshots: hash deduplication, immutable revisions, automatic-review exclusion, no-op publication, evidence scope, locked forecasts, frozen counts, explicit receipt linkage, Guest denial')
finally:
 frappe.db.rollback();frappe.destroy()
