"""Disposable delegated report approval coverage; all changes are rolled back."""
import frappe
from frappe.utils import today, add_days
from test_support import init_site
init_site()
from saeenaria_portal import reviews as r
from saeenaria_portal.testing import portal_fixtures

try:
 with portal_fixtures() as f:
  def report():
   frappe.set_user(f.employee)
   doc=frappe.get_doc(dict(doctype='Portal Report',title='Test delegated report',domain=f.domains[0],period_start=today(),period_end=today(),status='Draft',achievements='Test',is_demo=1)).insert()
   doc.status='Submitted';doc.save()
   review=frappe.get_doc('Portal Activity Review',{'source_key':'Portal Report:'+doc.name})
   frappe.set_user('Administrator')
   return doc,review
  source,review=report()
  assert not r.can_review(review,f.other)
  roles_before=set(frappe.get_roles(f.other))
  r.delegate_domain(f.domains[0],f.other,'Domain',[],is_demo=1)
  assert r.can_review(review,f.other) and r.can_view(review,f.other)
  assert not r.can_review(review,f.employee)
  assert not frappe.has_permission('Portal Report','read',doc=source,user=f.other)
  _,future=report();assert r.can_review(future,f.other)
  review.reload()
  r.assign_reviewer(review.name,f.hr,str(review.modified));review.reload()
  assert not r.can_review(review,f.other)
  assert r.can_review(review,f.hr) and r.can_review(review,'Administrator')
  r.decide(review.name,'Approved','Final approval',str(review.modified));review.reload();source.reload()
  assert review.status=='Approved' and source.status=='Approved'
  try:r.assign_reviewer(review.name,f.other,str(review.modified));raise AssertionError('approval reset')
  except frappe.ValidationError:pass
  frappe.set_user(f.other)
  try:r.decide(review.name,'Approved','Repeated approval',str(review.modified));raise AssertionError('second approval')
  except (frappe.ValidationError,frappe.PermissionError):pass
  try:r.delegate_domain(f.domains[0],f.hr,is_demo=1);raise AssertionError('privilege escalation')
  except frappe.PermissionError:pass
  frappe.set_user('Administrator')
  rule=frappe.get_doc('Portal Review Delegation',{'domain':f.domains[0],'enabled':1,'is_demo':1})
  r.revoke_delegation(rule.name,str(rule.modified));assert not r.can_review(future,f.other)
  r.delegate_domain(f.domains[0],f.other,is_demo=1)
  rule=frappe.get_doc('Portal Review Delegation',{'domain':f.domains[0],'enabled':1,'is_demo':1})
  rule.start_date=add_days(today(),1);rule.flags.portal_delegation_internal=True;rule.save(ignore_permissions=True)
  assert not r.can_review(future,f.other)
  rule.start_date=add_days(today(),-2);rule.end_date=add_days(today(),-1);rule.flags.portal_delegation_internal=True;rule.save(ignore_permissions=True)
  assert not r.can_review(future,f.other)
  assert set(frappe.get_roles(f.other))==roles_before
 print('PASS delegated human reports, future occurrences, date bounds, self-review denial, no broad read rights, management override, final approval, revocation and no role changes')
finally:
 frappe.db.rollback();frappe.destroy()
