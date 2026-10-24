import os,json
import frappe
from frappe.utils import today
from test_support import init_site
init_site()
from saeenaria_portal import reviews as r
from saeenaria_portal.testing import portal_fixtures
try:
 with portal_fixtures() as fixture:
  employee=fixture.employee;delegate=fixture.other;second=fixture.hr
  template_a='TESTPLAN-'+fixture.token+'-a';template_b='TESTPLAN-'+fixture.token+'-b'
  for name in (template_a,template_b):
   frappe.get_doc(dict(doctype='Portal Template',domain=fixture.domains[0],title=name,responsible=employee,frequency='Daily',enabled=1)).insert(set_name=name)
  def action(template,date):
   d=frappe.get_doc(dict(doctype='Portal Action',title='TEST persistent review',description='TEST',domain=fixture.domains[0],responsible=employee,due_date=date,start_date=date,status='Completed',progress=100,result='TEST',schedule_key=template+':'+date,is_demo=0)).insert(ignore_permissions=True)
   return frappe.get_doc('Portal Activity Review',{'source_key':'Portal Action:'+d.name})
  first=action(template_a,'2099-01-03');other=action(template_b,'2099-01-04')
  r.assign_reviewer(first.name,second,str(first.modified));first.reload()
  r.delegate_domain(fixture.domains[0],delegate,'Series',['template:'+template_a])
  first.reload();assert r.can_review(first,delegate) and not r.can_review(other,delegate)
  future=action(template_a,'2099-01-10');assert r.can_review(future,delegate)
  assert not r.can_review(future,employee)
  r.delegate_domain(fixture.domains[0],second,'Domain',[])
  assert r.can_review(future,second) and not r.can_review(future,delegate) and r.can_review(other,second)
  rule=frappe.get_doc('Portal Review Delegation',{'domain':fixture.domains[0],'enabled':1})
  r.revoke_delegation(rule.name,str(rule.modified));assert not r.can_review(future,second)
  # Bulk preview is explicit and version checked, never revives a final approval.
  def oneoff():
   d=frappe.get_doc(dict(doctype='Portal Record',domain=fixture.domains[0],title='TEST one-off review',responsible=employee,record_type='Supply Request',record_date=today(),external_id=frappe.generate_hash(length=20),is_demo=0)).insert(ignore_permissions=True)
   return frappe.get_doc('Portal Activity Review',{'source_key':'Portal Record:'+d.name})
  assert r.preview_bulk_reviewer(fixture.domains[0],delegate,[first.name])['skipped']
  first,other=oneoff(),oneoff()
  preview=r.preview_bulk_reviewer(fixture.domains[0],delegate,[first.name,other.name])
  assert len(preview['items'])==2
  stale=[dict(row) for row in preview['items']];stale[-1]['modified']='2000-01-01 00:00:00'
  try:r.bulk_assign_reviewer(fixture.domains[0],delegate,stale);raise AssertionError('stale accepted')
  except frappe.ValidationError:pass
  first.reload();assert not first.reviewer
  result=r.bulk_assign_reviewer(fixture.domains[0],delegate,preview['items']);assert result['count']==2
  first.reload();assert first.reviewer==delegate
  try:r.preview_bulk_reviewer(fixture.domains[1],delegate,[first.name]);raise AssertionError('cross domain accepted')
  except frappe.PermissionError:pass
  frappe.set_user(delegate)
  try:r.delegate_domain(fixture.domains[0],second,'Domain',[]);raise AssertionError('privilege escalation')
  except frappe.PermissionError:pass
  print('PASS: persistent selected template across future occurrences, unrelated template excluded, domain replacement/revocation, self-approval blocked, bulk stale atomicity and domain/privilege guards')
finally:
 frappe.db.rollback();frappe.destroy()
