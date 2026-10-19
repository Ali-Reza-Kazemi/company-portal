"""Validated imports from Time.ir's published current-year calendar, not calculated lunar dates."""
import datetime
import hashlib
import json
import re
import requests
import jdatetime
import frappe
from frappe.utils import getdate, now_datetime, get_datetime
from saeenaria_portal.permissions import admin, roles

SOURCE = 'https://www.time.ir/event-year'

def current_year():
    return jdatetime.date.fromgregorian(date=getdate()).year

def parse_calendar(html, year):
    chunks = re.findall(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)', html)
    text = ''.join(json.loads(chunk) for chunk in chunks)
    marker = '"defaultYearlyCalendar":'
    if text.count(marker) != 1:
        raise ValueError('ساختار تقویم منبع تغییر کرده است')
    months, _ = json.JSONDecoder().raw_decode(text.split(marker, 1)[1])
    if len(months) != 12 or {m['month'] for m in months} != set(range(1,13)) or any(m['year'] != year for m in months):
        raise ValueError('منبع هنوز تقویم کامل سال جاری را منتشر نکرده است')
    result = {}
    day_count = 0
    for month in months:
        days = [d for d in month['day_list'] if d['enabled']]
        expected = (jdatetime.date(year+1,1,1).togregorian()-jdatetime.date(year,12,1).togregorian()).days if month['month']==12 else (31 if month['month']<=6 else 30)
        if sorted(d['index_in_base1'] for d in days) != list(range(1, expected+1)):
            raise ValueError('روزهای تقویم منبع کامل نیست')
        day_count += len(days)
        for event in month['event_list']:
            if event['is_holiday'] is not True:
                continue
            if event['jalali_year'] != year or event['jalali_month'] != month['month']:
                raise ValueError('سال یا ماه رویداد نادرست است')
            date = jdatetime.date(year,event['jalali_month'],event['jalali_day']).togregorian()
            if date != datetime.date(event['gregorian_year'],event['gregorian_month'],event['gregorian_day']):
                raise ValueError('تاریخ شمسی و میلادی رویداد تطابق ندارد')
            title = event['title'].strip()
            if not title or len(title)>1000:
                raise ValueError('عنوان تعطیلی معتبر نیست')
            result.setdefault(date, [])
            if title not in result[date]:result[date].append(title)
    fixed = [(1,1),(1,2),(1,3),(1,4),(1,12),(1,13),(3,14),(3,15),(11,22),(12,29)]
    if not 20 <= len(result) <= 40 or any(jdatetime.date(year,m,d).togregorian() not in result for m,d in fixed):
        raise ValueError('فهرست تعطیلات رسمی منبع کامل به نظر نمی‌رسد')
    return {date:' / '.join(titles) for date,titles in result.items()}

def fetch_calendar(year):
    response=requests.get(SOURCE,timeout=(8,25),stream=True)
    response.raise_for_status()
    data=bytearray()
    for chunk in response.iter_content(65536):
        data.extend(chunk)
        if len(data)>4_000_000:raise ValueError('حجم پاسخ منبع بیش از حد مجاز است')
    html=data.decode('utf-8')
    return parse_calendar(html,year),hashlib.sha256(data).hexdigest()

def synchronize():
    year=current_year()
    with frappe.cache.lock('saeenaria-holiday-sync',timeout=100,blocking_timeout=1):
        holidays,digest=fetch_calendar(year)
        counts=dict(created=0,updated=0,unchanged=0,manual=0,deactivated=0)
        rows=frappe.get_all('Portal Holiday',fields=['name','date','title','source_url','imported_title','source_year','enabled'],limit_page_length=0)
        existing={getdate(row.date):row for row in rows}
        for date,title in holidays.items():
            row=existing.get(date)
            if row and (row.source_url!=SOURCE or row.title!=row.imported_title):
                counts['manual']+=1;continue
            if row:
                if row.title==title and row.enabled:
                    counts['unchanged']+=1;continue
                doc=frappe.get_doc('Portal Holiday',row.name);counts['updated']+=1
            else:
                doc=frappe.new_doc('Portal Holiday');counts['created']+=1
            doc.update(dict(date=date,title=title,enabled=1,source_url=SOURCE,source_year=year,imported_title=title))
            doc.save(ignore_permissions=True)
        for row in rows:
            if row.source_url==SOURCE and row.source_year==year and row.enabled and getdate(row.date) not in holidays and row.title==row.imported_title:
                frappe.db.set_value('Portal Holiday',row.name,'enabled',0);counts['deactivated']+=1
        status=frappe.get_single('Portal Calendar Sync')
        status.update(dict(last_year=year,last_sync=now_datetime(),source_hash=digest,holiday_count=len(holidays)))
        status.save(ignore_permissions=True)
        return dict(year=year,total=len(holidays),source=SOURCE,**counts)

@frappe.whitelist(methods=['POST'])
def sync_now():
    if not (admin(frappe.session.user) or 'Company Director' in roles(frappe.session.user)):
        frappe.throw('به‌روزرسانی تعطیلات فقط برای مدیر مجاز است',frappe.PermissionError)
    try:
        return synchronize()
    except (requests.RequestException, ValueError, KeyError, TypeError) as error:
        frappe.log_error(title='Holiday source update failed',message=str(error))
        frappe.throw('دریافت تقویم کامل و معتبر از منبع ممکن نشد؛ تعطیلات قبلی حفظ شدند. کمی بعد دوباره تلاش کنید.')

def auto_sync():
    status=frappe.get_single('Portal Calendar Sync')
    if status.last_year==current_year() and status.last_sync and (now_datetime()-get_datetime(status.last_sync)).days<7:
        return
    try:
        synchronize()
    except Exception:
        frappe.log_error(title='Automatic holiday update failed',message=frappe.get_traceback())
