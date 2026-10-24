"""Settings checks inside a rolled-back transaction; no real policy is changed."""
import os
from unittest.mock import patch,MagicMock
import frappe
from test_support import init_site
init_site()
from saeenaria_portal.purchase_reports import general_settings as g,product_catalog as c,workflow,workflow_data,sources
from saeenaria_portal.purchase_reports.calculations import DEFAULTS
try:
 doc=frappe.get_single(g.DT)
 if not doc.initialized:
  doc.update({f:str(DEFAULTS[l]) for f,l,*_ in g.SCHEMA});doc.initialized=1;doc.revision=1;doc.save(ignore_permissions=True)
 data=g.overview();assert len(data['schema'])==11 and data['can_edit']
 original=dict(data['values']);revision=data['revision'];before_history=frappe.db.count(g.HISTORY)
 proposed={**original,'coverage_months':str(int(float(original['coverage_months']))+1)}
 preview=g.preview(proposed,revision);assert len(preview['changes'])==1 and preview['changes'][0]['field']=='coverage_months'
 assert g.values()==original and frappe.db.count(g.HISTORY)==before_history
 for field,value in [('sales_months','0'),('lead_months','-1'),('pack_size','0'),('growth_percent','NaN'),('active_months','1.5')]:
  try:g.validate({**original,field:value});raise AssertionError('invalid value accepted')
  except frappe.ValidationError:pass
 with patch.object(frappe,'enqueue') as queue:
  result=g.save(proposed,revision);assert result['revision']==revision+1
  assert queue.call_args.kwargs['enqueue_after_commit'] and queue.call_args.kwargs['revision']==revision+1
 assert g.values()['coverage_months']==proposed['coverage_months']
 assert frappe.db.count(g.HISTORY)==before_history+1
 assert g.rows()==[{'پارامتر':l,'مقدار':g.values()[f]} for f,l,*_ in g.SCHEMA]
 try:g.save(original,revision);raise AssertionError('stale revision accepted')
 except frappe.TimestampMismatchError:pass
 assert not g.save(proposed,revision+1)['saved'] and frappe.db.count(g.HISTORY)==before_history+1
 # Both purchasing and inventory must read policy from the portal, not Excel.
 with patch.object(sources,'connection',side_effect=AssertionError('external policy source read')):
  bundle=workflow.settings_bundle()
  assert bundle['GeneralSettings']==g.rows()
  assert bundle['ProductMapping']==c.mapping_rows()
  assert bundle['metadata'][0]['portal_settings_revision']==revision+1
 with patch.object(c,'can_edit',return_value=False),patch.object(g,'can_edit',return_value=False):
  assert not g.overview()['can_edit']
  try:g.save(original,revision+1);raise AssertionError('read-only viewer edited')
  except frappe.PermissionError:pass
 frappe.set_user('Guest')
 try:g.overview();raise AssertionError('guest accepted')
 except frappe.PermissionError:pass
 print('PASS: 11 parameters, preview without writes, numeric validation, versioned atomic save, audit history, stale-edit rejection, no-op save, after-commit recalculation, shared portal policy in both report pipelines, read-only and guest permissions.')
finally:frappe.db.rollback();frappe.destroy()
