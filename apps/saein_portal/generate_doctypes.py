"""Generate standard, versioned Frappe DocType definitions."""
import json
from pathlib import Path
root = Path(__file__).parent / "saein_portal" / "saein_portal" / "doctype"

def field(name, label, kind="Data", **kw):
    return dict(fieldname=name, label=label, fieldtype=kind, **kw)

def permission(role, write=False):
    return dict(role=role, read=1, select=1, print=1, export=1, create=int(write), write=int(write), delete=0)

def create(name, fields, permissions, autoname):
    slug = name.lower().replace(" ", "_")
    folder = root / slug
    folder.mkdir(parents=True, exist_ok=True)
    obj = dict(doctype="DocType", name=name, module="Saein Portal", custom=0, engine="InnoDB", autoname=autoname, track_changes=1, field_order=[f["fieldname"] for f in fields], fields=fields, permissions=permissions, sort_field="modified", sort_order="DESC")
    (folder / f"{slug}.json").write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    (folder / "__init__.py").touch()
    cls = name.replace(" ", "")
    (folder / f"{slug}.py").write_text(f"from frappe.model.document import Document\n\nclass {cls}(Document):\n    pass\n", encoding="utf-8")

admins = [permission("System Manager", True), permission("Portal Administrator", True)]
readers = [permission("Company Director"), permission("Domain Officer"), permission("Portal Contributor")]
create("Portal Domain", [field("domain_code", "کد حوزه", reqd=1, unique=1), field("title", "نام حوزه", reqd=1, in_list_view=1)], admins + readers, "field:domain_code")
create("Portal Assignment", [field("domain", "حوزه", "Link", options="Portal Domain", reqd=1, in_list_view=1), field("user", "کاربر", "Link", options="User", reqd=1, in_list_view=1), field("enabled", "فعال", "Check", default="1")], admins, "hash")
create("Portal Action", [
    field("title", "عنوان", reqd=1, in_list_view=1),
    field("domain", "حوزه", "Link", options="Portal Domain", reqd=1, in_list_view=1),
    field("responsible", "مسئول", "Link", options="User", reqd=1),
    field("priority", "اولویت", "Select", options="Low\nNormal\nHigh\nUrgent", default="Normal", reqd=1),
    field("start_date", "تاریخ شروع", "Date"),
    field("due_date", "موعد", "Date", reqd=1, in_list_view=1),
    field("status", "وضعیت", "Select", options="Open\nIn Progress\nBlocked\nCompleted\nCancelled", default="Open", reqd=1, in_list_view=1),
    field("progress", "پیشرفت", "Percent", default="0"),
    field("obstacle", "مانع", "Small Text"),
    field("result", "نتیجه", "Small Text"),
    field("evidence", "مدرک انجام", "Attach"),
    field("is_demo", "داده آزمایشی", "Check", default="0"),
], admins + [permission("Company Director"), permission("Domain Officer", True), permission("Portal Contributor", True)], "format:ACT-{#####}")
# Shared operational models.
common = [field("domain", "حوزه", "Link", options="Portal Domain", reqd=1, in_list_view=1)]
editors = admins + [permission("Company Director"), permission("Domain Officer", True), permission("Portal Contributor", True)]
create("Portal Metric", common + [
 field("title", "نام شاخص", reqd=1, in_list_view=1), field("definition", "تعریف", "Small Text", reqd=1),
 field("unit", "واحد", reqd=1), field("direction", "جهت مطلوب", "Select", options="Higher\nLower", reqd=1),
 field("formula", "فرمول", "Small Text"), field("source", "منبع"),
 field("frequency", "تناوب", "Select", options="Daily\nWeekly\nMonthly\nQuarterly", default="Monthly"),
 field("data_owner", "مسئول داده", "Link", options="User"),
 field("default_target", "هدف پیش‌فرض", "Float"), field("has_default_target", "هدف تعیین شده", "Check"),
 field("green_threshold", "آستانه سبز", "Float"), field("red_threshold", "آستانه قرمز", "Float"),
 field("thresholds_configured", "آستانه‌ها تنظیم شده", "Check")], editors, "hash")
create("Portal Metric Value", common + [
 field("metric", "شاخص", "Link", options="Portal Metric", reqd=1, in_list_view=1),
 field("period_start", "شروع دوره", "Date", reqd=1), field("period_end", "پایان دوره", "Date", reqd=1),
 field("data_status", "وضعیت داده", "Select", options="Valid\nProvisional\nMissing", default="Missing", reqd=1),
 field("actual", "مقدار واقعی", "Float"), field("has_target", "هدف تعیین شده", "Check"), field("target", "هدف", "Float"),
 field("source", "منبع"), field("source_updated_at", "زمان به‌روزرسانی منبع", "Datetime"),
 field("dedup_key", "شناسه یکتا", unique=1, read_only=1), field("is_demo", "آزمایشی", "Check")], editors, "hash")
create("Portal Report", common + [
 field("title", "عنوان", reqd=1, in_list_view=1), field("period_start", "شروع دوره", "Date", reqd=1),
 field("period_end", "پایان دوره", "Date", reqd=1),
 field("status", "گردش گزارش", "Select", options="Draft\nSubmitted\nNeeds Revision\nApproved", default="Draft", reqd=1, in_list_view=1),
 field("achievements", "دستاوردها", "Small Text"), field("obstacles", "موانع", "Small Text"),
 field("next_plan", "برنامه بعد", "Small Text"), field("management_comment", "نظر مدیریت", "Small Text"),
 field("supersedes", "اصلاحیه گزارش", "Link", options="Portal Report"),
 field("snapshot", "تصویر شاخص‌ها در زمان ارسال", "Code", options="JSON", read_only=1),
 field("is_demo", "آزمایشی", "Check")], editors, "format:RPT-{#####}")
create("Portal Decision", common + [
 field("title", "موضوع تصمیم", reqd=1, in_list_view=1), field("request", "شرح درخواست", "Small Text", reqd=1),
 field("due_date", "موعد", "Date"), field("status", "وضعیت", "Select", options="Open\nAnswered", default="Open"),
 field("response", "پاسخ مدیریت", "Small Text"), field("responded_by", "پاسخ‌دهنده", "Link", options="User", read_only=1),
 field("responded_at", "زمان پاسخ", "Datetime", read_only=1), field("is_demo", "آزمایشی", "Check")], editors, "format:DEC-{#####}")
create("Portal Template", common + [
 field("title", "عنوان اقدام", reqd=1, in_list_view=1), field("responsible", "مسئول", "Link", options="User"),
 field("frequency", "تناوب", "Select", options="Daily\nWeekly\nMonthly\nQuarterly", reqd=1),
 field("weekday", "روز هفته Python (شنبه=۵)", "Int", default="5"),
 field("day_of_month", "روز ماه شمسی", "Int", default="1"),
 field("enabled", "فعال", "Check", default="0")], editors, "hash")
create("Portal Holiday", [field("date", "تاریخ تعطیل", "Date", reqd=1, unique=1), field("title", "عنوان", reqd=1)], admins + readers, "field:date")
create("Portal Policy", [field("title", "عنوان قاعده", reqd=1),field("policy_key", "کد قاعده", reqd=1, unique=1),field("configured", "تنظیم شده", "Check"),field("definition", "تعریف مورد تأیید", "Small Text"),field("value", "مقدار", "Float"),field("unit", "واحد")], admins + readers, "field:policy_key")
create("Portal Record", common + [
 field("title", "عنوان", reqd=1, in_list_view=1),
 field("record_type", "نوع ورودی", "Select", options="Demand Forecast\nSupply Request\nLost Sale\nExcess Reduction\nStock Count\nCampaign\nLead\nTarget Customer\nVisit\nEmergency Visit\nCompetitor Analysis\nEvent\nTicket\nService Outage\nBackup Check\nData Error\nDevelopment Project\nReport Delivery", reqd=1, in_list_view=1),
 field("external_id", "شناسه منبع", reqd=1), field("dedup_key", "شناسه یکتا", unique=1, read_only=1),
 field("record_date", "تاریخ ثبت رویداد", "Date", reqd=1),field("period_start", "شروع دوره", "Date"),field("period_end", "پایان دوره", "Date"),
 field("responsible", "مسئول", "Link", options="User"), field("status", "وضعیت"), field("channel", "کانال / منبع"),
 field("item_code", "کد کالا / گروه"), field("customer_code", "شناسه مشتری"), field("service", "سرویس"),
 field("quantity", "مقدار", "Float"), field("amount", "مبلغ", "Currency"), field("cost", "هزینه", "Currency"),
 field("planned_at", "زمان برنامه / هشدار", "Datetime"),field("ordered_at", "زمان سفارش / ثبت", "Datetime"),
 field("promised_at", "زمان تعهد / موعد", "Datetime"),field("actual_at", "زمان واقعی / رفع", "Datetime"),
 field("rating", "امتیاز رضایت", "Float"), field("details", "جزئیات و نتیجه", "Small Text"),
 field("evidence", "مدرک خصوصی", "Attach"),field("baseline_snapshot", "فهرست مبنای ثابت", "Long Text"),
 field("locked", "نسخه مبنا قفل شده", "Check", default="0"),field("is_demo", "آزمایشی", "Check")], editors, "format:REC-{#####}")
# Idempotent recurrence key.
p = root / "portal_action" / "portal_action.json"
obj = json.loads(p.read_text(encoding="utf-8"))
obj["fields"].append(field("schedule_key", "کلید برنامه", unique=1, read_only=1))
obj["field_order"].append("schedule_key")
p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8")
# Keep generation reproducible for management review rights.
for slug in ("portal_report", "portal_decision"):
    path = root / slug / f"{slug}.json"
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    for perm in obj["permissions"]:
        if perm["role"] == "Company Director": perm.update(write=1,create=1)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding="utf-8")
