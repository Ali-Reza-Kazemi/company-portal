"""Explicit plan revision with private before-images, preserving actual forecast records."""
import os,json
from pathlib import Path
from datetime import timedelta
import jdatetime
os.chdir('/home/frappe/workspace/portal-bench/sites')
import frappe
from frappe.utils import today,getdate
frappe.init(site='portal.localhost');frappe.connect();frappe.set_user('Administrator')
from saeenaria_portal.purchase_reports import workflow as w
try:
 user=w.owner();start,end=w.math.month_bounds(w.math.month_bounds(getdate(today()))[1]+timedelta(days=1))
 candidates=frappe.get_all('Portal Action',filters={'responsible':user,'schedule_key':['in',['INVPLAN-bootstrap:'+start.isoformat(),'INVPLAN-forecast:'+start.isoformat(),'INVPLAN-forecast:'+(start+timedelta(days=2)).isoformat()]]},pluck='name')
 count_names=frappe.get_all('Portal Action',filters={'responsible':user,'schedule_key':['like','INVPLAN-variance:%'],'status':['not in',['Completed','Cancelled']]},pluck='name')
 docs=[frappe.get_doc('Portal Action',n) for n in candidates+count_names]
 template_docs=[frappe.get_doc('Portal Template',n) for n in ['INVPLAN-forecast','INVPLAN-variance']]
 related=frappe.get_all('Portal Activity Review',filters={'source_type':'Portal Action','source_name':['in',candidates+count_names]},pluck='name')
 folder=Path(frappe.get_site_path('private','plan-revision-backups'));folder.mkdir(parents=True,exist_ok=True)
 path=folder/('before-'+frappe.generate_hash(length=12)+'.json');path.write_text(json.dumps({'actions':[d.as_dict() for d in docs],'templates':[d.as_dict() for d in template_docs],'reviews':[frappe.get_doc('Portal Activity Review',n).as_dict() for n in related]},ensure_ascii=False,default=str),encoding='utf-8');path.chmod(0o600)
 forecast=template_docs[0];forecast.day_of_month=25;forecast.description='پیش از شروع ماه آینده، پیش‌بینی تعداد فروش هر شش گروه را در صفحه پایش موجودی بررسی و ثبت کنید. یک ثبت کامل برای این فعالیت کافی است.';forecast.save(ignore_permissions=True)
 actions=[frappe.get_doc('Portal Action',n) for n in candidates]
 saved=w.existing_forecast(start,end)
 if actions:
  keep=max(actions,key=lambda d:(d.status=='Completed',d.progress or 0,not d.schedule_key.startswith('INVPLAN-bootstrap:')))
  for other in actions:
   if other.name==keep.name:continue
   for review in frappe.get_all('Portal Activity Review',filters={'source_type':'Portal Action','source_name':other.name},pluck='name'):frappe.delete_doc('Portal Activity Review',review,ignore_permissions=True)
   frappe.delete_doc('Portal Action',other.name,ignore_permissions=True)
  keep.schedule_key='INVPLAN-forecast:'+start.isoformat();keep.title='ثبت پیش‌بینی فروش ماه آینده';keep.description=forecast.description
  deadline=start-timedelta(days=1);holidays={getdate(d) for d in frappe.get_all('Portal Holiday',filters={'enabled':1},pluck='date')}
  while deadline.weekday() in (3,4) or deadline in holidays:deadline-=timedelta(days=1)
  if keep.status!='Completed':keep.start_date=min(getdate(keep.start_date),deadline);keep.due_date=deadline
  if saved:keep.status='Completed';keep.progress=100;keep.result='پیش‌بینی کامل شش گروه قبلاً ثبت و قفل شده؛ فعالیت‌های هم‌پوشان ادغام شدند.'
  keep.save(ignore_permissions=True);keep.add_comment('Info','ادغام فعالیت پیش‌بینی اولیه و ماهانه طبق درخواست کاربر؛ داده‌های واقعی پیش‌بینی حفظ شدند.')
 count=template_docs[1];count.frequency='Semiannual';count.day_of_month=15;count.description='شمارش فیزیکی انبار و ثبت دستی یا اکسل در ۱۵ فروردین و ۱۵ مهر؛ نوبت آغازین استثنایی ۱۵ آبان ۱۴۰۵ است.';count.save(ignore_permissions=True)
 initial=jdatetime.date(1405,8,15).togregorian()
 for name in count_names:
  doc=frappe.get_doc('Portal Action',name);doc.schedule_key='INVPLAN-variance:'+initial.isoformat();doc.start_date=initial;doc.due_date=initial;doc.description=count.description;doc.save(ignore_permissions=True)
 frappe.db.commit()
 print(json.dumps({'backup':str(path),'forecast_actions':len(actions),'forecast_remaining':keep.name if actions else None,'existing_forecast_preserved':saved,'count_first':str(initial),'count_recurrence':'15 Farvardin / 15 Mehr'},ensure_ascii=False,default=str))
except Exception:frappe.db.rollback();raise
finally:frappe.destroy()
