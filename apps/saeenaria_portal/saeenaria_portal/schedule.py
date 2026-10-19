import datetime
import jdatetime
import frappe
from frappe.utils import getdate, today


def next_workday(date, holidays):
    date = getdate(date)
    while date.weekday() in (3,4) or date in holidays:
        date += datetime.timedelta(days=1)
    return date


def nominal_dates(template, start, end):
    date = getdate(start)
    while date <= getdate(end):
        jalali = jdatetime.date.fromgregorian(date=date)
        if template.frequency == "Daily" or (template.frequency == "Weekly" and date.weekday() == template.weekday) or (template.frequency == "Monthly" and jalali.day == template.day_of_month) or (template.frequency == "Quarterly" and jalali.month in (1,4,7,10) and jalali.day == template.day_of_month):
            yield date
        date += datetime.timedelta(days=1)

@frappe.whitelist(methods=["POST"])
def generate(start=None, end=None):
    from saeenaria_portal.permissions import admin
    if not admin(frappe.session.user):
        frappe.throw("تولید برنامه فقط برای مدیر سامانه مجاز است",frappe.PermissionError)
    start, end = getdate(start or today()), getdate(end or today())
    if end < start or (end-start).days > 366:
        frappe.throw("بازه تولید باید حداکثر یک سال باشد")
    holidays = {getdate(d) for d in frappe.get_all("Portal Holiday",filters={"enabled":1},pluck="date")}
    created = 0
    for t in frappe.get_all("Portal Template",filters={"enabled":1},fields=["*"]):
        if not t.responsible: continue
        for nominal in nominal_dates(t,start,end):
            if t.frequency == "Daily" and (nominal.weekday() in (3,4) or nominal in holidays): continue
            due = next_workday(nominal,holidays)
            key = f"{t.name}:{nominal.isoformat()}"
            if frappe.db.exists("Portal Action",{"schedule_key":key}): continue
            try:
                frappe.get_doc({"doctype":"Portal Action","title":t.title,"description":t.description,"domain":t.domain,"responsible":t.responsible,"due_date":due,"start_date":due,"schedule_key":key}).insert()
                created += 1
            except frappe.DuplicateEntryError:
                pass
    return {"created":created}

def generate_today():
    generate()
