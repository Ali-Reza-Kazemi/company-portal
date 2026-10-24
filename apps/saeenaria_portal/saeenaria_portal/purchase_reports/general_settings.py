"""Shared, versioned purchasing policy stored exclusively in portal documents."""
from decimal import Decimal, InvalidOperation
import json

import frappe
from frappe.utils import now_datetime, cint
from .calculations import settings_values
from .service import require_access
from .product_catalog import can_edit, require_edit

DT = 'Portal Purchase Settings'
HISTORY = 'Portal Purchase Settings Change'
SCHEMA = [
    ('sales_months','دوره بررسی فروش','ماه',1,120,True,'میانگین فروش خالص از این تعداد ماه محاسبه می‌شود.'),
    ('lead_months','زمان تأمین','ماه',0,120,False,'زمان مورد انتظار از سفارش تا رسیدن کالا؛ در پیشنهاد خرید و زمان سفارش استفاده می‌شود.'),
    ('coverage_months','پوشش هدف','ماه',0,120,False,'موجودی هدف باید فروش این تعداد ماه را پوشش دهد.'),
    ('safety_months','ذخیره اطمینان','ماه',0,120,False,'پوشش اضافه برای تأخیر تأمین یا افزایش تقاضا.'),
    ('growth_percent','درصد رشد پیش‌بینی','درصد',-100,1000,False,'درصد افزایش یا کاهش نسبت به میانگین فروش؛ صفر یعنی بدون رشد.'),
    ('min_order','حداقل سفارش','عدد',0,1000000000,False,'حداقل تعداد خرید هنگامی که نیاز به سفارش مثبت است.'),
    ('pack_size','ضریب بسته‌بندی','عدد',1,1000000000,False,'مقدار پیشنهادی سفارش رو به بالا به مضرب این عدد گرد می‌شود.'),
    ('return_window_months','پنجره تأیید بازگشت فروش','ماه',0,120,True,'بازه اخیر برای بررسی بازگشت فروش کالاهای راکد.'),
    ('active_months','حداقل ماه فعال برای خروج از رسوب','ماه فعال',0,120,True,'حداقل تعداد ماه دارای فروش مثبت در پنجره اخیر.'),
    ('dormancy_months','آستانه تشخیص رسوب','ماه',0,120,True,'فاصله زمانی مؤثر در تشخیص رکود و فروش موردی.'),
    ('max_coverage_months','حداکثر پوشش مجاز','ماه',0,120,False,'پوشش بالاتر از این مقدار به‌عنوان موجودی بیش از حد بررسی می‌شود.'),
]


def active():
    return bool(frappe.db.exists('DocType',DT) and frappe.db.get_single_value(DT,'initialized'))


def normalized(value):
    return format(Decimal(str(value or 0)).normalize(),'f')


def values(doc=None):
    doc = doc or frappe.get_single(DT)
    return {field:normalized(doc.get(field)) for field,*_ in SCHEMA}


def rows():
    current = values()
    return [{'پارامتر':label,'مقدار':current[field]} for field,label,*_ in SCHEMA]


def validate(proposed):
    proposed = frappe.parse_json(proposed)
    if not isinstance(proposed,dict) or set(proposed)!={r[0] for r in SCHEMA}:
        frappe.throw('تمام متغیرهای شناخته‌شده تنظیمات لازم است؛ صفحه را تازه کنید')
    clean = {}
    for field,label,unit,low,high,integer,description in SCHEMA:
        try:
            raw = proposed[field]
            if isinstance(raw,bool) or raw is None or str(raw).strip()=='':
                raise ValueError()
            number = Decimal(str(raw))
            if not number.is_finite() or number<low or number>high or (integer and number!=int(number)) or number.as_tuple().exponent < -9:
                raise ValueError()
            clean[field]=normalized(number)
        except (ValueError, InvalidOperation,TypeError):
            frappe.throw(f'«{label}» باید عدد معتبر بین {low} و {high}'+(' و صحیح' if integer else '')+' باشد؛ حداکثر ۹ رقم اعشار مجاز است')
    return clean


def record_change(revision,before,after,kind):
    return frappe.get_doc(dict(doctype=HISTORY,revision=revision,changed_by=frappe.session.user,changed_at=now_datetime(),change_kind=kind,before_json=json.dumps(before,ensure_ascii=False),after_json=json.dumps(after,ensure_ascii=False))).insert(ignore_permissions=True)


def initialize():
    from saeenaria_portal.permissions import admin
    if not admin(frappe.session.user):
        frappe.throw('انتقال اولیه فقط برای مدیر سامانه مجاز است',frappe.PermissionError)
    if active():
        return {'already_initialized':True}
    from .calculations import DEFAULTS
    initial=validate({field:str(DEFAULTS[label]) for field,label,*_ in SCHEMA})
    with frappe.cache.lock('purchase-settings:'+frappe.local.site,timeout=60):
        if active():return {'already_initialized':True}
        doc=frappe.get_single(DT);doc.update(initial);doc.initialized=1;doc.revision=1;doc.updated_by=frappe.session.user;doc.updated_at=now_datetime();doc.save(ignore_permissions=True)
        record_change(1,{},initial,'راه‌اندازی بومی پورتال')
        frappe.db.commit()
    return {'revision':1,'values':initial}


@frappe.whitelist()
def overview():
    require_access()
    if not active():frappe.throw('تنظیمات عمومی هنوز به پورتال منتقل نشده است')
    doc=frappe.get_single(DT)
    history=frappe.get_all(HISTORY,fields=['revision','changed_by','changed_at','change_kind','before_json','after_json'],order_by='revision desc',limit_page_length=30)
    for entry in history:
        entry['before']=json.loads(entry.pop('before_json') or '{}');entry['after']=json.loads(entry.pop('after_json') or '{}')
    return {'schema':[{'field':f,'label':l,'unit':u,'min':low,'max':high,'integer':integer,'description':desc} for f,l,u,low,high,integer,desc in SCHEMA],'values':values(doc),'revision':doc.revision,'updated_at':doc.updated_at,'updated_by':doc.updated_by,'can_edit':can_edit(),'history':history}


@frappe.whitelist(methods=['POST'])
def preview(proposed,expected_revision):
    require_edit()
    if not active():frappe.throw('تنظیمات هنوز راه‌اندازی نشده است')
    doc=frappe.get_single(DT)
    if cint(expected_revision)!=doc.revision:frappe.throw('تنظیمات توسط شخص دیگری تغییر کرده؛ مقادیر را دوباره دریافت کنید',frappe.TimestampMismatchError)
    clean=validate(proposed);before=values(doc)
    return {'changes':[{'field':field,'label':label,'unit':unit,'before':before[field],'after':clean[field]} for field,label,unit,*_ in SCHEMA if before[field]!=clean[field]],'revision':doc.revision,'values':clean}


@frappe.whitelist(methods=['POST'])
def save(proposed,expected_revision):
    require_edit()
    clean=validate(proposed)
    with frappe.cache.lock('purchase-settings:'+frappe.local.site,timeout=60):
        # Current-read row locks also protect requests whose DB transaction began
        # before they acquired the Redis lock.
        locked=dict(frappe.db.sql('SELECT field,value FROM `tabSingles` WHERE doctype=%s FOR UPDATE',(DT,)))
        doc=frappe.get_single(DT)
        if not cint(locked.get('initialized')) or cint(locked.get('revision'))!=cint(expected_revision):frappe.throw('تنظیمات تغییر کرده؛ مقادیر جدید را دریافت کنید',frappe.TimestampMismatchError)
        before={field:normalized(locked.get(field)) for field,*_ in SCHEMA}
        if before==clean:return {'saved':False,'revision':cint(locked['revision'])}
        doc.update(clean);doc.revision=cint(locked['revision'])+1;doc.updated_by=frappe.session.user;doc.updated_at=now_datetime();doc.save(ignore_permissions=True)
        record_change(doc.revision,before,clean,'ویرایش تنظیمات')
        # Enqueue only after the transaction is committed. Each revision gets its own job.
        frappe.enqueue('saeenaria_portal.purchase_reports.general_settings.recalculate',queue='long',timeout=5400,job_id='purchase-policy:'+frappe.local.site+':'+str(doc.revision),deduplicate=True,enqueue_after_commit=True,revision=doc.revision)
    return {'saved':True,'revision':doc.revision,'queued':True}


def recalculate(revision):
    from .service import refresh_data
    from .workflow import capture_all
    refresh_data(wait=True)
    capture_all(wait=True)
