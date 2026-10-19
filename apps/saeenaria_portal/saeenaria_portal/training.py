"""Explicitly invoked, idempotent educational data; never scheduled."""
import frappe
from frappe.utils import today, getdate, add_days, now_datetime
PREFIX = "آموزشی | "

def seed():
    from saeenaria_portal.permissions import admin
    if not admin(frappe.session.user):
        frappe.throw("فقط مدیر سامانه", frappe.PermissionError)
    result = {}
    def insert(dt, key, data):
        name = frappe.db.exists(dt, key)
        if name:
            return frappe.get_doc(dt, name)
        doc = frappe.get_doc(dict(doctype=dt, **data)).insert()
        result[dt] = result.get(dt, 0) + 1
        return doc
    scenarios = [
        ("marketing", "rkhanbabaei89@gmail.com", "پیگیری پیش‌فاکتور دستگاه جوش", "تماس با مشتری فرضی آذرصنعت؛ ثبت نیاز، زمان خرید و نتیجه تماس. خروجی: تصمیم مشتری و زمان پیگیری بعدی.", "تعداد پیگیری مؤثر فروش", "تعداد", [6,8,7,10], 10),
        ("inventory", "alirezakazemi@saeenaria.com", "کنترل کمبود تورچ جوشکاری", "موجودی و رزرو کالای فرضی TORCH-DEMO را تطبیق دهید و پیشنهاد تأمین همراه با مقدار و زمان موردنیاز ثبت کنید.", "تعداد اقلام کنترل‌شده انبار", "تعداد", [12,15,18,20], 20),
        ("it-data", "alirezakazemi@saeenaria.com", "رفع مغایرت کد مشتری", "کد مشتری فرضی DEMO-C01 را بین فایل فروش و گزارش انبار تطبیق دهید؛ خروجی: فهرست مغایرت و نتیجه اصلاح.", "تعداد خطاهای داده رفع‌شده", "تعداد", [2,4,3,5], 5)]
    for domain, user, title, description, metric_title, values_unit, values, target in scenarios:
        if not frappe.db.exists("User", {"name": user, "enabled": 1}) or not frappe.db.exists("Portal Domain", domain):
            frappe.throw("کاربر یا حوزه موردنیاز سناریوی آموزشی موجود نیست")
        for i, (status, progress, offset) in enumerate([("Open",0,3),("In Progress",50,1),("Blocked",30,-2),("Completed",100,0)]):
            label = ["شروع‌نشده","در حال انجام","دارای مانع","انجام‌شده"][i]
            full_title = PREFIX + title + " ـ " + label
            insert("Portal Action", {"title":full_title,"is_demo":1}, dict(title=full_title,domain=domain,responsible=user,description=description,due_date=add_days(today(),offset),status=status,progress=progress,is_demo=1,allow_external_responsible=1,result="نمونه آموزشی: خروجی تهیه و برای بررسی ارسال شد." if status=="Completed" else "",obstacle="نمونه آموزشی: منتظر پاسخ تأمین‌کننده/واحد مرتبط هستیم." if status=="Blocked" else ""))
        insert("Portal Template", {"title":PREFIX+title}, dict(title=PREFIX+title,domain=domain,responsible=user,description=description,frequency="Weekly",weekday=5,enabled=0,allow_external_responsible=1))
        metric=insert("Portal Metric", {"title":PREFIX+metric_title,"domain":domain},dict(title=PREFIX+metric_title,domain=domain,definition="نمونه ساختگی برای یادگیری؛ شمارش خروجی قابل بررسی در یک هفته، نه امتیاز نهایی کارمند.",formula="شمارش خروجی ثبت‌شده و کنترل‌شده در هفته؛ در این نمونه مقدار دستی است.",unit=values_unit,direction="Higher",frequency="Weekly",source="سناریوی آموزشی ساختگی؛ بدون اتصال به دیدار و سپیدار",thresholds_configured=1,green_threshold=target,red_threshold=target/2))
        for week, value in enumerate(values):
            end=add_days(today(),-7*(3-week))
            start=add_days(end,-6)
            insert("Portal Metric Value", {"metric":metric.name,"period_start":start,"period_end":end,"is_demo":1},dict(domain=domain,metric=metric.name,period_start=start,period_end=end,data_status="Valid",actual=value,has_target=1,target=target,source="داده ساختگی آموزشی؛ ثبت دستی",source_updated_at=now_datetime(),is_demo=1))
        record_types = {"marketing":["Lead","Visit"],"inventory":["Lost Sale","Supply Request"],"it-data":["Ticket","Data Error"]}[domain]
        for i, kind in enumerate(record_types):
            external_id="TRAINING-V1-"+domain+"-"+str(i)
            insert("Portal Record", {"external_id":external_id,"is_demo":1},dict(domain=domain,title=PREFIX+title+" ـ ورودی "+str(i+1),record_type=kind,external_id=external_id,record_date=today(),responsible=user,quantity=2,amount=10000000 if domain=="inventory" else 0,status="نمونه آموزشی",item_code="DEMO-TORCH" if domain=="inventory" else "",customer_code="DEMO-C01",details="نمونه ساختگی؛ این رکورد به‌صورت خودکار شاخص‌ها را محاسبه نمی‌کند. مبلغ به ریال است.",is_demo=1))
        report=insert("Portal Report", {"title":PREFIX+"گزارش "+title,"is_demo":1},dict(domain=domain,title=PREFIX+"گزارش "+title,period_start=add_days(today(),-6),period_end=today(),status="Draft",achievements="خروجی این هفته ثبت شد؛ روند چهار هفته در راهنمای آموزشی قابل مشاهده است.",obstacles="یک کار به علت انتظار پاسخ واحد مرتبط متوقف است.",next_plan="رفع مانع و تکمیل کارهای باز هفته آینده.",is_demo=1))
        if report.status=="Draft":
            report.status="Submitted";report.save()
        insert("Portal Decision", {"title":PREFIX+"درخواست تصمیم "+title,"is_demo":1},dict(domain=domain,title=PREFIX+"درخواست تصمیم "+title,request="نمونه: برای رفع مانع این حوزه، اولویت و مسئول پیگیری مشخص شود.",due_date=add_days(today(),3),status="Open",is_demo=1))
    return result
