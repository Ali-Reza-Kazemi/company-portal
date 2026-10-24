"""Explicit, idempotent transition requested by the user; never run on install."""
from datetime import timedelta
import json
from pathlib import Path
import frappe
import jdatetime
from frappe.utils import getdate,today
from .workflow import PLAN,owner,metric_name,existing_forecast
from . import workflow_math as math
from .sources import json_default


def setup_plan(dry_run=False):
    from saeenaria_portal.permissions import admin
    if not admin(frappe.session.user):frappe.throw("مدیر سامانه لازم است",frappe.PermissionError)
    from saeenaria_portal.automatic_work import AUTO_CODES
    user=owner()
    old=frappe.get_all("Portal Template",filters={"responsible":user},fields=["name","title"])
    old=[r for r in old if not r.name.startswith("INVPLAN-")]
    actions=frappe.get_all("Portal Action",filters={"responsible":user,"is_demo":0,"status":["not in",["Completed","Cancelled"]]},fields=["name","schedule_key","progress"])
    actions=[r for r in actions if r.schedule_key and not r.schedule_key.startswith("INVPLAN-")]
    if dry_run:return {"templates_to_remove":len(old),"open_recurring_to_archive":len(actions),"new_templates":len(set(PLAN)-AUTO_CODES)}
    if old or actions:
        folder=Path(frappe.get_site_path("private","inventory-transition-backups"));folder.mkdir(parents=True,exist_ok=True)
        path=folder/("before-"+frappe.generate_hash(length=12)+".json")
        payload={"templates":[frappe.get_doc("Portal Template",r.name).as_dict() for r in old],"actions":[frappe.get_doc("Portal Action",r.name).as_dict() for r in actions]}
        path.write_text(json.dumps(payload,ensure_ascii=False,default=json_default),encoding="utf-8");path.chmod(0o600)
    for r in actions:
        doc=frappe.get_doc("Portal Action",r.name)
        doc.status="Cancelled";doc.obstacle="برنامه قدیمی طبق درخواست مدیریت با برنامه پایش هفتگی و ماهانه موجودی جایگزین شد؛ سوابق و پیشرفت قبلی حفظ است"
        doc.save(ignore_permissions=True);doc.add_comment("Info","جایگزینی برنامه تکرارشونده؛ سابقه اقدام حذف نشده است")
    for r in old:frappe.delete_doc("Portal Template",r.name,ignore_permissions=True)
    definitions={
      "cancel":("درصد کنسلی درخواست به علت نبود کالا","درصد","Lower","معاملات ناموفق با علت دقیق نبود کالا / همه معاملات یکتای تعیین‌تکلیف‌شده هفته × ۱۰۰"),
      "capital":("ارزش موجودی به قیمت رسمی فروش","ریال","Lower","موجودی مثبت هر کالا × قیمت رسمی همان کالا و واحد در پایان دوره؛ مبنای فروش و نه بهای تمام‌شده"),
      "slow":("ارزش کل کالای راکد به قیمت رسمی فروش","ریال","Lower","کل موجودی مثبت کالای مشمول قاعده رسوب × قیمت رسمی؛ مستقل از فقط مقدار مازاد پوشش"),
      "turnover":("گردش تعدادی سالانه موجودی","مرتبه","Higher","فروش خالص ۱۲ماهه / متوسط ۱۲ موجودی پایان ماه شمسی؛ مستقل از شاخص ارزش‌محور قدیمی"),
      "lead":("زمان آلارم اتمام کالا تا رسید","روز","Lower","میانگین روزهای آلارم تا رسید دارای ارتباط صریح؛ دقت رسید روزانه است"),
      "forecast":("دقت پیش‌بینی تقاضا","درصد","Higher","max(0,100-100×Σ|پیش‌بینی قفل‌شده گروه−فروش خالص گروه|/Σفروش خالص شش گروه)؛ بدون مبنای پیش از دوره ناموجود"),
      "variance":("درصد مغایرت اقلام شمارش‌شده","درصد","Lower","تعداد اقلام و انبارهای دارای اختلاف / تعداد اقلام و انبارهای واقعاً شمارش‌شده ماه × ۱۰۰"),
      "urgency":("اقلام نیازمند تصمیم خرید","قلم","Lower","تعداد کالاهای مرجع سفارش‌پذیر دارای نیاز خرید؛ فوریت و زمان پیشنهادی در ریز گزارش، فاقد هدف عددی")}
    for code,(title,unit,direction,formula) in definitions.items():
        name=metric_name(code)
        if not frappe.db.exists("Portal Metric",name):
            frappe.get_doc(dict(doctype="Portal Metric",domain="inventory",title=title,definition=formula,formula=formula,unit=unit,direction=direction,frequency="Weekly" if code=="cancel" else "Monthly",data_owner=user,source="پایش خودکار سپیدار و دیدار؛ "+math.POLICY,has_default_target=0,thresholds_configured=0)).insert(ignore_permissions=True,set_name=name)
    current=getdate(today());holidays={getdate(d) for d in frappe.get_all("Portal Holiday",filters={"enabled":1},pluck="date")}
    from saeenaria_portal.schedule import next_workday
    month_start=math.month_bounds(current)[1]+timedelta(days=1)
    for code,(frequency,title,description) in PLAN.items():
        from saeenaria_portal.automatic_work import AUTO_CODES
        if code in AUTO_CODES:continue
        name="INVPLAN-"+code
        if not frappe.db.exists("Portal Template",name):
            frappe.get_doc(dict(doctype="Portal Template",domain="inventory",title=title,description=description+"\nثبت، سوابق و نمودار: /portal-inventory",responsible=user,frequency=frequency,weekday=5,day_of_month=15 if code=="variance" else 25 if code=="forecast" else 3,enabled=1)).insert(ignore_permissions=True,set_name=name)
        nominal=math.previous_week(current)[1]+timedelta(days=1) if frequency=="Weekly" else month_start+timedelta(days=2)
        if code=="forecast":nominal=month_start
        if code=="variance":
            initial=jdatetime.date(1405,8,15).togregorian()
            candidates=[jdatetime.date(year,month,15).togregorian() for year in range(jdatetime.date.fromgregorian(date=current).year,jdatetime.date.fromgregorian(date=current).year+2) for month in (1,7)]
            nominal=min(d for d in [initial]+candidates if d>=current)
        schedule_key=name+":"+nominal.isoformat()
        if not frappe.db.exists("Portal Action",{"schedule_key":schedule_key}):
            due=next_workday(current if frequency=="Weekly" else nominal,holidays)
            if code=="forecast":
                due=month_start-timedelta(days=1)
                while due.weekday() in (3,4) or due in holidays:due-=timedelta(days=1)
            frappe.get_doc(dict(doctype="Portal Action",domain="inventory",title=title,description=description+"\nصفحه انجام کار: /portal-inventory",responsible=user,start_date=current if frequency=="Weekly" else due,due_date=due,schedule_key=schedule_key,is_demo=0)).insert(ignore_permissions=True)
    bootstrap=0
    return {"templates_removed":len(old),"old_open_recurring_archived":len(actions),"new_active_templates":len(set(PLAN)-AUTO_CODES),"initial_forecast_action_created":bootstrap}
