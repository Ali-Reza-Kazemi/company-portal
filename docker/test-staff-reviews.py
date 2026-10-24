import os
import frappe
from frappe.utils import today
from test_support import init_site
init_site()
from saeenaria_portal.testing import portal_fixtures
try:
 with portal_fixtures() as fixture:
  from saeenaria_portal import reviews as r
  from saeenaria_portal import staff_requests as staff
  employee=fixture.employee;manager=fixture.manager;delegate=fixture.other
  frappe.set_user(employee)
  result=staff.submit_request(dict(employee=employee,request_type='Leave',duration_type='Hourly',leave_kind='Annual',start_date=today(),start_time='09:00',end_time='11:00',details='آزمون موقت',is_demo=1))
  request=frappe.get_doc('Portal Staff Request',result['name']);assert request.duration_summary=='120 دقیقه' and request.start_date==request.end_date
  assert request.domain==staff.employee_domain(employee)
  assert not frappe.db.exists('Portal Activity Review',{'source_key':request.doctype+':'+request.name})
  assert not staff.can_approve(request,employee)
  frappe.set_user(manager)
  staff.assign_approver(request.name,delegate,str(request.modified));request.reload()
  assert not staff.can_approve(request,manager) and staff.can_approve(request,delegate)
  frappe.set_user(delegate)
  assert any(row.name==request.name for row in staff.overview(1)['requests'])
  staff.decide(request.name,'Returned','تاریخ نیاز به اصلاح دارد',str(request.modified));request.reload();assert request.approval_status=='Returned'
  frappe.set_user(employee)
  staff.update_request(request.name,{'details':'درخواست اصلاح‌شده'},str(request.modified));request.reload();assert request.approval_status=='Pending'
  frappe.set_user(delegate)
  staff.decide(request.name,'Approved','',str(request.modified));request.reload();assert request.approval_status=='Approved'
  frappe.set_user(employee)
  try:staff.update_request(request.name,{'details':'تغییر پس از تأیید'},str(request.modified));raise AssertionError('approved request editable')
  except frappe.ValidationError:pass
  staff.cancel_request(request.name);request.reload();assert request.approval_status=='Cancelled'
  assert all(row.source_type!='Portal Staff Request' for row in r.overview(1)['reviews'])
  frappe.set_user('Administrator')
  action=frappe.get_doc(dict(doctype='Portal Action',title='آزمون موقت بررسی',domain=fixture.domains[0],responsible=employee,due_date=today(),status='Completed',progress=100,result='خروجی آزمون',is_demo=1)).insert()
  ar=frappe.get_doc('Portal Activity Review',{'source_key':'Portal Action:'+action.name})
  frappe.set_user(manager);r.decide(ar.name,'Approved','خروجی قابل قبول',str(ar.modified));ar.reload();assert ar.status=='Approved'
  frappe.set_user(employee);action.reload();action.result='خروجی اصلاح‌شده';action.save();ar.reload();assert ar.status=='Pending'
  try:r.assign_reviewer(ar.name,employee,str(ar.modified));raise AssertionError('self assign allowed')
  except (frappe.PermissionError,frappe.ValidationError):pass

  frappe.set_user('Administrator')
  report=frappe.get_doc(dict(doctype='Portal Report',title='آزمون موقت گزارش',domain=fixture.domains[1],period_start=today(),period_end=today(),status='Draft',achievements='خروجی آزمایشی',is_demo=1)).insert()
  report.status='Submitted';report.save()
  rr=frappe.get_doc('Portal Activity Review',{'source_key':'Portal Report:'+report.name})
  r.assign_reviewer(rr.name,employee,str(rr.modified));rr.reload()
  frappe.set_user(employee)
  assert not frappe.has_permission('Portal Report','read',doc=report)
  assert any(row.name==rr.name for row in r.overview(1)['reviews'])
  r.decide(rr.name,'Returned','اصلاح گزارش لازم است',str(rr.modified));report.reload();assert report.status=='Needs Revision'
  frappe.set_user('Administrator');report.status='Submitted';report.save();rr.reload();assert rr.status=='Pending'
  frappe.set_user(employee);r.decide(rr.name,'Approved','تأیید گزارش',str(rr.modified));report.reload();assert report.status=='Approved'
  assert r.history(rr.name)
  frappe.set_user('Administrator')
  record=frappe.get_doc(dict(doctype='Portal Record',title='آزمون موقت ورودی',domain=fixture.domains[1],responsible=delegate,record_type='Ticket',external_id=frappe.generate_hash(length=12),record_date=today(),details='بررسی موقت',is_demo=1)).insert()
  vr=frappe.get_doc('Portal Activity Review',{'source_key':'Portal Record:'+record.name})
  r.assign_reviewer(vr.name,employee,str(vr.modified));vr.reload()
  frappe.set_user(employee);r.decide(vr.name,'Approved','تأیید رخداد',str(vr.modified));vr.reload();assert vr.status=='Approved'
  frappe.set_user('Administrator');record.details='ویرایش ورودی';record.save();vr.reload();assert vr.status=='Pending'
  frappe.set_user(employee)
  try:r.decide(vr.name,'Approved','قدیمی',str(rr.modified));raise AssertionError('stale decision accepted')
  except frappe.ValidationError:pass

  frappe.set_user(fixture.hr)
  try:r.assign_reviewer(vr.name,employee,str(vr.modified));raise AssertionError('HR delegated unrelated activity')
  except frappe.PermissionError:pass
  frappe.set_user('Administrator')
  metric=frappe.get_doc(dict(doctype='Portal Metric',domain=fixture.domains[0],title='Test metric',definition='Test',unit='count',direction='Higher')).insert().name
  mv=frappe.get_doc(dict(doctype='Portal Metric Value',domain=fixture.domains[0],metric=metric,period_start='2030-01-01',period_end='2030-01-07',data_status='Valid',actual=2,has_target=1,target=3,is_demo=1)).insert()
  mr=frappe.get_doc('Portal Activity Review',{'source_key':'Portal Metric Value:'+mv.name})
  r.assign_reviewer(mr.name,employee,str(mr.modified));mr.reload()
  frappe.set_user(employee);r.decide(mr.name,'Approved','مقادیر کنترل شد',str(mr.modified));mr.reload();assert mr.status=='Approved'

  frappe.set_user('Administrator')
  legacy_request=staff.submit_request(dict(domain=fixture.domains[0],employee=employee,request_type='Mission',duration_type='Daily',start_date=today(),end_date=today(),destination='مقصد آزمون',details='آزمون انتقال سابقه',is_demo=1))
  legacy_doc=frappe.get_doc('Portal Staff Request',legacy_request['name'])
  legacy=frappe.get_doc(dict(doctype='Portal Activity Review',title=legacy_doc.title,source_type='Portal Staff Request',source_name=legacy_doc.name,source_key='Portal Staff Request:'+legacy_doc.name,domain=fixture.domains[0],employee=employee,reviewer=delegate,status='Approved',review_note='نظر قبلی حفظ شود',reviewed_by=delegate,is_demo=1))
  r.save_review(legacy);legacy.add_comment('Info','سابقه قبلی آزمون')
  staff.migrate_legacy();legacy_doc.reload()
  assert legacy_doc.approval_status=='Approved' and legacy_doc.approver==delegate and legacy_doc.approval_note=='نظر قبلی حفظ شود'
  assert any('سابقه قبلی آزمون' in item for item in staff.history(legacy_doc.name))
  assert staff.migrate_legacy()['migrated']==0
  assert all(item.source_type!='Portal Staff Request' for item in r.overview(1)['reviews'])
  try:r.assign_reviewer(legacy.name,delegate,str(legacy.modified));raise AssertionError('legacy staff row editable as activity')
  except frappe.PermissionError:pass
  frappe.set_user('Guest')
  try:r.overview();raise AssertionError('Guest admitted')
  except (frappe.PermissionError,frappe.ValidationError):pass
  print('PASS: independent staff lifecycle and activity lifecycle, no mixed queue, delegation, returns/approvals/cancel, activity invalidation, Guest denial. Rollback.')
finally:frappe.db.rollback();frappe.destroy()
