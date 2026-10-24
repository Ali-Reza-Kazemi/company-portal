import hashlib
import json
import frappe
from frappe.utils import getdate, now_datetime, today, flt, cint
from saeenaria_portal.permissions import admin, can_domain, roles

def private_evidence(doc):
    if doc.get("evidence"):
        if not doc.evidence.startswith("/private/files/"):
            frappe.throw("مدرک باید به صورت فایل خصوصی بارگذاری شود")
        files = frappe.get_all("File", filters={"file_url": doc.evidence}, fields=["name", "attached_to_doctype", "attached_to_name"])
        if not files:
            frappe.throw("فایل مدرک یافت نشد")
        for info in files:
            file = frappe.get_doc("File", info.name)
            file.check_permission("read")
            if info.attached_to_name and (info.attached_to_doctype != doc.doctype or info.attached_to_name != doc.name):
                frappe.throw("این فایل به رکورد دیگری متصل است")

def validate(doc, method=None):
    user = frappe.session.user
    before = doc.get_doc_before_save()
    delegated_review = bool(getattr(frappe.local,"portal_review_decision",None)==(doc.doctype,doc.name) and doc.doctype == "Portal Report")
    director = "Company Director" in roles(user) or delegated_review
    management_doc = doc.doctype in ("Portal Report", "Portal Decision", "Portal Metric", "Portal Metric Value")
    manager = admin(user) or director
    if doc.doctype == "Portal Metric" and not manager:
        frappe.throw("تعریف و ویرایش شناسنامه شاخص فقط برای مدیریت مجاز است", frappe.PermissionError)
    if not can_domain(user, doc.domain, write=True) and not (director and management_doc):
        frappe.throw("اجازه ثبت در این حوزه را ندارید", frappe.PermissionError)
    if before and not can_domain(user, before.domain, write=True) and not (director and management_doc):
        frappe.throw("انتقال غیرمجاز رکورد", frappe.PermissionError)
    if doc.get("period_start") and doc.get("period_end") and getdate(doc.period_start) > getdate(doc.period_end):
        frappe.throw("پایان دوره پیش از شروع است")
    private_evidence(doc)
    if doc.doctype == "Portal Metric Value":
        if not manager and (doc.get("responsible") or "") != (before.get("responsible") or "" if before else ""):
            frappe.throw("تغییر مسئول مقدار شاخص فقط برای مدیریت مجاز است",frappe.PermissionError)
        if not manager:
            baseline_flag = cint(before.has_target) if before else 0
            baseline_target = flt(before.target) if before else 0
            if cint(doc.has_target) != baseline_flag or flt(doc.target) != baseline_target:
                frappe.throw("تعیین یا تغییر هدف شاخص فقط برای مدیریت مجاز است", frappe.PermissionError)
            if before and any(str(doc.get(key) or "") != str(before.get(key) or "") for key in ("domain", "metric", "period_start", "period_end", "is_demo")):
                frappe.throw("برای دوره یا شاخص دیگر، مقدار جدید ثبت کنید؛ هویت رکورد موجود قابل تغییر نیست", frappe.PermissionError)
        metric = frappe.get_doc("Portal Metric", doc.metric)
        if metric.domain != doc.domain:
            frappe.throw("حوزه شاخص و مقدار یکسان نیست")
        if not before and not doc.has_target and metric.has_default_target:
            doc.has_target = 1
            doc.target = metric.default_target
        doc.dedup_key = hashlib.sha256(f"{doc.metric}|{doc.period_start}|{doc.period_end}|{int(doc.is_demo or 0)}".encode()).hexdigest()
    if doc.doctype == "Portal Metric" and doc.thresholds_configured:
        if doc.direction == "Higher" and doc.red_threshold > doc.green_threshold:
            frappe.throw("آستانه قرمز باید کمتر از سبز باشد")
        if doc.direction == "Lower" and doc.red_threshold < doc.green_threshold:
            frappe.throw("آستانه قرمز باید بیشتر از سبز باشد")
    if doc.doctype == "Portal Report":
        if before and before.get("inventory_snapshot") != doc.get("inventory_snapshot"):
            frappe.throw("نسخه مبنای گزارش موجود قابل تعویض نیست؛ گزارش تازه ثبت کنید")
        if doc.get("inventory_snapshot"):
            basis=frappe.get_doc("Portal Inventory Snapshot",doc.inventory_snapshot)
            if not delegated_review:basis.check_permission("read")
            if basis.domain!=doc.domain or getdate(basis.period_start)!=getdate(doc.period_start) or getdate(basis.period_end)!=getdate(doc.period_end):
                frappe.throw("دوره و حوزه گزارش با نسخه مبنا یکسان نیست")
        if doc.status in ("Approved", "Needs Revision") and (not before or doc.status != before.status) and not delegated_review:
            frappe.throw("تأیید یا برگشت گزارش از صفحه بررسی و تأیید فعالیت‌ها انجام می‌شود")
        if before and before.status == "Approved":
            frappe.throw("گزارش تأییدشده تغییر نمی‌کند؛ اصلاحیه‌ای با ارجاع به اصل بسازید")
        old = before.status if before else "Draft"
        transitions = {"Draft": {"Draft", "Submitted"}, "Submitted": {"Submitted", "Needs Revision", "Approved"}, "Needs Revision": {"Needs Revision", "Submitted"}}
        if doc.status not in transitions.get(old, set()):
            frappe.throw("تغییر وضعیت گزارش مجاز نیست")
        if doc.status in ("Approved", "Needs Revision") and old != doc.status and not (admin(user) or director):
            frappe.throw("تأیید و درخواست اصلاح فقط برای مدیریت مجاز است", frappe.PermissionError)
        if before and not (admin(user) or director) and before.management_comment != doc.management_comment:
            frappe.throw("نظر مدیریت قابل ویرایش نیست", frappe.PermissionError)
        if doc.supersedes:
            previous = frappe.get_doc("Portal Report", doc.supersedes)
            previous.check_permission("read")
            if previous.domain != doc.domain or previous.status != "Approved":
                frappe.throw("اصلاحیه باید به گزارش تأییدشده همین حوزه ارجاع دهد")
        if doc.status == "Submitted" and old != "Submitted":
            if doc.get("inventory_snapshot"):
                from saeenaria_portal.purchase_reports.workflow import report_metric_snapshot
                doc.snapshot=json.dumps(report_metric_snapshot(doc.inventory_snapshot),ensure_ascii=False,default=str)
            else:
                from saeenaria_portal.metrics import overview
                doc.snapshot = json.dumps(overview(doc.domain, doc.period_start, doc.period_end, doc.is_demo), ensure_ascii=False, default=str)
        elif before:
            doc.snapshot = before.snapshot
    if doc.doctype == "Portal Decision":
        if doc.response and (not before or before.response != doc.response):
            if not (admin(user) or director):
                frappe.throw("پاسخ فقط توسط مدیریت ثبت می‌شود", frappe.PermissionError)
            doc.responded_by = user
            doc.responded_at = now_datetime()
            doc.status = "Answered"
        elif before:
            doc.responded_by, doc.responded_at = before.responded_by, before.responded_at
    if doc.doctype == "Portal Record":
        doc.dedup_key = hashlib.sha256(f"{doc.domain}|{doc.record_type}|{doc.external_id}|{int(doc.is_demo or 0)}".encode()).hexdigest()
        if before and before.locked:
            frappe.throw("نسخه مبنا قفل است؛ برای اصلاح، نسخه مستقل با شناسه جدید بسازید")
        if doc.record_type == "Demand Forecast":
            if not doc.period_start or getdate(doc.record_date) >= getdate(doc.period_start):
                frappe.throw("پیش‌بینی باید پیش از شروع دوره ثبت شود")
            if not before and getdate(today()) >= getdate(doc.period_start):
                frappe.throw("پیش‌بینی دوره گذشته ثبت نمی‌شود")
            doc.locked = 1
