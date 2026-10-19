import hashlib
import json
import frappe
from frappe.utils import getdate, get_time, get_datetime, now_datetime, cint, flt
from saeenaria_portal.permissions import admin, roles, managed_domains, domains
from saeenaria_portal.user_names import display_name

SOURCES={
 "Portal Action": ["title","description","domain","responsible","status","progress","result","obstacle","due_date","completed_at","is_demo"],
 "Portal Record": ["title","domain","responsible","record_type","record_date","details","quantity","amount","cost","status","channel","item_code","customer_code","service","planned_at","ordered_at","promised_at","actual_at","rating","external_id","period_start","period_end","baseline_snapshot","locked","is_demo"],
 "Portal Metric Value": ["domain","metric","period_start","period_end","actual","has_target","target","data_status","source","is_demo"],
 "Portal Report": ["title","domain","period_start","period_end","achievements","obstacles","next_plan","is_demo"]}
LABELS={"Portal Action":"اقدام کاری","Portal Record":"ورودی عملیاتی","Portal Metric Value":"مقدار شاخص","Portal Report":"گزارش حوزه"}

def signed_in():
    if frappe.session.user=="Guest":frappe.throw("ورود لازم است",frappe.PermissionError)

def leadership(user):return admin(user) or "Company Director" in roles(user)

def assignable(review,user):
    return leadership(user) or review.domain in managed_domains(user)

def can_review(review,user):
    if review.source_type not in SOURCES:return False
    if user=="Guest" or user==review.employee:return False
    if review.reviewer:return review.reviewer==user
    return leadership(user) or review.domain in managed_domains(user)

def can_view(review,user):return review.source_type in SOURCES and (user==review.employee or user==review.reviewer or assignable(review,user))

def review_validate(doc,method=None):
    if not doc.flags.portal_review_internal:
        frappe.throw("بررسی فقط از صفحه بررسی و تأیید فعالیت‌ها انجام می‌شود",frappe.PermissionError)

def save_review(doc):
    doc.flags.portal_review_internal=True
    doc.save(ignore_permissions=True)

def snapshot(doc):
    values={}
    for key in SOURCES[doc.doctype]:
        value=doc.get(key)
        field=doc.meta.get_field(key)
        kind=field.fieldtype if field else "Data"
        if kind in ("Check","Int"):value=cint(value)
        elif kind in ("Float","Currency","Percent"):value=flt(value)
        elif value in (None,""):value=None
        elif kind=="Date":value=getdate(value).isoformat()
        elif kind=="Datetime":value=get_datetime(value).isoformat()
        elif kind=="Time":value=str(get_time(value))
        values[key]=value
    values["evidence"]=doc.get("evidence") or None
    text=json.dumps(values,ensure_ascii=False,default=str,sort_keys=True)
    return text,hashlib.sha256(text.encode()).hexdigest()

def sync(doc,method=None):
    if doc.doctype not in SOURCES:return
    if getattr(frappe.local,"portal_review_decision",None)==(doc.doctype,doc.name):return
    text,digest=snapshot(doc)
    key=doc.doctype+":"+doc.name
    name=frappe.db.get_value("Portal Activity Review",{"source_key":key},"name")
    if not name:
        if doc.doctype=="Portal Action" and doc.status!="Completed" and not doc.progress and not doc.result:return
        if doc.doctype=="Portal Report" and doc.status!="Submitted":return
    if name:
        review=frappe.get_doc("Portal Activity Review",name)
        if review.source_hash==digest and not (doc.doctype=="Portal Report" and doc.status=="Submitted" and review.status=="Returned"):return
    else:
        review=frappe.new_doc("Portal Activity Review")
        review.source_key=key;review.source_type=doc.doctype;review.source_name=doc.name
    review.title=doc.get("title") or ("مقدار شاخص: "+str(frappe.db.get_value("Portal Metric",doc.get("metric"),"title") or doc.name))
    review.domain=doc.domain
    review.employee=doc.get("employee") or doc.get("responsible") or doc.owner
    if review.reviewer==review.employee:review.reviewer=None
    review.snapshot=text;review.source_hash=digest;review.is_demo=doc.get("is_demo") or 0
    review.status="Cancelled" if doc.get("cancelled") or doc.get("status")=="Cancelled" else "Pending"
    review.review_note=None;review.reviewed_at=None;review.reviewed_by=None
    save_review(review)



@frappe.whitelist()
def overview(is_demo=0):
    signed_in();user=frappe.session.user
    filters={"is_demo":cint(is_demo)}
    rows=frappe.get_all("Portal Activity Review",filters=filters,fields=["*"],order_by="modified desc",limit_page_length=0)
    output=[]
    for row in rows:
        if not can_view(row,user):continue
        row["employee_name"]=display_name(row.employee)
        row["reviewer_name"]=display_name(row.reviewer) if row.reviewer else "مدیر واحد"
        row["reviewed_by_name"]=display_name(row.reviewed_by) if row.reviewed_by else ""
        row["kind"]=LABELS[row.source_type]
        row["can_review"]=can_review(row,user)
        row["can_assign"]=assignable(row,user) and not (row.source_type=="Portal Report" and row.status=="Approved")
        row.pop("source_key",None);row.pop("source_hash",None)
        output.append(row)
    return {"reviews":output,"user":user}


def locked_review(name):
    frappe.db.get_value("Portal Activity Review",name,"name",for_update=True)
    doc=frappe.get_doc("Portal Activity Review",name)
    if doc.source_type not in SOURCES:frappe.throw("این مورد مربوط به فعالیت‌ها نیست؛ به بخش مرخصی و مأموریت مراجعه کنید",frappe.PermissionError)
    return doc

@frappe.whitelist(methods=["POST"])
def assign_reviewer(name,reviewer,expected_modified):
    signed_in();doc=locked_review(name)
    if not assignable(doc,frappe.session.user):frappe.throw("تعیین بررسی‌کننده فقط برای مدیر مجاز است",frappe.PermissionError)
    if str(doc.modified)!=str(expected_modified):frappe.throw("اطلاعات تغییر کرده؛ صفحه را تازه کنید")
    if doc.status=="Cancelled":frappe.throw("درخواست لغو شده است")
    if doc.source_type=="Portal Report" and doc.status=="Approved":frappe.throw("گزارش تأییدشده ثابت است؛ اصلاحیه ثبت کنید")
    if reviewer and (reviewer==doc.employee or not frappe.db.exists("User",{"name":reviewer,"enabled":1,"user_type":"System User"})):frappe.throw("بررسی‌کننده باید کاربر فعال و غیر از صاحب فعالیت باشد")
    doc.reviewer=reviewer or None;doc.status="Pending";doc.review_note=None;doc.reviewed_at=None;doc.reviewed_by=None
    save_review(doc)
    doc.add_comment("Info","تعیین بررسی‌کننده توسط "+display_name(frappe.session.user)+": "+(display_name(reviewer) if reviewer else "مدیر واحد"))
    return "بررسی‌کننده تعیین شد؛ این اختیار فقط برای همین مورد است."

@frappe.whitelist(methods=["POST"])
def decide(name,status,note,expected_modified):
    signed_in();doc=locked_review(name)
    if not can_review(doc,frappe.session.user):frappe.throw("شما بررسی‌کننده این مورد نیستید یا صاحب فعالیت هستید",frappe.PermissionError)
    if doc.status!="Pending" or str(doc.modified)!=str(expected_modified):frappe.throw("نسخه مورد بررسی تغییر کرده؛ صفحه را تازه کنید")
    if status not in ("Approved","Returned"):frappe.throw("نتیجه بررسی نامعتبر است")
    if not (note or "").strip():frappe.throw("نظر بررسی‌کننده الزامی است")
    frappe.db.get_value(doc.source_type,doc.source_name,"name",for_update=True)
    source=frappe.get_doc(doc.source_type,doc.source_name)
    if snapshot(source)[1]!=doc.source_hash:frappe.throw("محتوای فعالیت تغییر کرده است؛ نسخه جدید باید بررسی شود")
    if source.doctype=="Portal Action" and status=="Approved" and source.status!="Completed":frappe.throw("تأیید نهایی اقدام فقط پس از ثبت انجام کامل ممکن است؛ برای بررسی میانی نظر ثبت کنید")
    doc.status=status;doc.review_note=note.strip();doc.reviewed_by=frappe.session.user;doc.reviewed_at=now_datetime()
    if source.doctype=="Portal Report":
        source.status="Approved" if status=="Approved" else "Needs Revision";source.management_comment=doc.review_note
        frappe.local.portal_review_decision=(source.doctype,source.name)
        try:source.save(ignore_permissions=True)
        finally:frappe.local.portal_review_decision=None
    save_review(doc)
    doc.add_comment("Info",("تأیید" if status=="Approved" else "برگشت برای اصلاح")+" توسط "+display_name(frappe.session.user)+": "+frappe.utils.escape_html(doc.review_note))
    return "نتیجه بررسی ثبت شد."

@frappe.whitelist(methods=["POST"])
def comment(name,note):
    signed_in();doc=locked_review(name)
    if not can_review(doc,frappe.session.user):frappe.throw("اجازه بررسی ندارید",frappe.PermissionError)
    if not (note or "").strip():frappe.throw("نظر را بنویسید")
    doc.add_comment("Info","نظر بررسی توسط "+display_name(frappe.session.user)+": "+frappe.utils.escape_html(note.strip()))
    doc.review_note=note.strip();save_review(doc)
    return "نظر بررسی ثبت شد؛ این کار به معنی تأیید نهایی نیست."


@frappe.whitelist()
def history(name):
    signed_in();doc=frappe.get_doc("Portal Activity Review",name)
    if not can_view(doc,frappe.session.user):frappe.throw("اجازه مشاهده ندارید",frappe.PermissionError)
    from frappe.utils import strip_html
    return [strip_html(row.content) for row in frappe.get_all("Comment",filters={"reference_doctype":doc.doctype,"reference_name":doc.name,"comment_type":"Info"},fields=["content"],order_by="creation asc",limit_page_length=100)]

def backfill():
    if not admin(frappe.session.user):frappe.throw("فقط مدیر سامانه",frappe.PermissionError)
    count=0
    for doctype in SOURCES:
        for name in frappe.get_all(doctype,pluck="name",limit_page_length=0):
            if not frappe.db.exists("Portal Activity Review",{"source_key":doctype+":"+name}):
                sync(frappe.get_doc(doctype,name));count+=1
    return {"examined":count,"review_count":frappe.db.count("Portal Activity Review")}


@frappe.whitelist()
def options():
    signed_in();user=frappe.session.user
    units=frappe.get_all("Portal Domain",fields=["name","title"],limit_page_length=0)
    if not leadership(user):units=[d for d in units if d.name in domains(user) or d.name in managed_domains(user)]
    can_assign=leadership(user) or bool(managed_domains(user))
    users=frappe.get_all("User",filters={"enabled":1,"user_type":"System User","name":["!=","Guest"]},fields=["name","full_name"],limit_page_length=0) if can_assign else []
    for row in users:row["full_name"]=display_name(row.name)
    return {"domains":units,"users":users,"self":user,"self_name":display_name(user)}
