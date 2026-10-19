"""Leave and mission lifecycle, separate from activity reviews."""
import frappe
from contextlib import contextmanager
from frappe.utils import getdate, get_time, get_datetime, now_datetime, cint
from saeenaria_portal.permissions import admin, roles, managed_domains, domains
from saeenaria_portal.user_names import display_name

APPROVAL_FIELDS=("approval_status","approver","approval_note","approved_by","approved_at")
CONTENT_FIELDS=("duration_type","leave_kind","start_date","end_date","start_time","end_time","destination","details","evidence")

def signed_in():
    if frappe.session.user=="Guest":frappe.throw("ورود لازم است",frappe.PermissionError)

def leadership(user):return admin(user) or "Company Director" in roles(user)

def can_manage(doc,user):return leadership(user) or "Portal HR Manager" in roles(user) or doc.domain in managed_domains(user)

def can_approve(doc,user):
    if user=="Guest" or user==doc.employee:return False
    return user==doc.approver if doc.approver else leadership(user) or doc.domain in managed_domains(user)

@contextmanager
def internal_operation():
    previous=getattr(frappe.local,"staff_request_internal",False)
    frappe.local.staff_request_internal=True
    try:yield
    finally:frappe.local.staff_request_internal=previous

def employee_domain(employee):
    """Stable routing: oldest active unit membership, never chosen by the applicant."""
    rows=frappe.get_all("Portal Assignment",filters={"user":employee,"enabled":1},fields=["domain"],order_by="creation asc, name asc",limit_page_length=1)
    return rows[0].domain if rows else None

def validate_request(doc,method=None):
    user=frappe.session.user
    internal=bool(getattr(frappe.local,"staff_request_internal",False))
    old=doc.get_doc_before_save()
    if not old and (doc.employee==user or not doc.domain):
        doc.domain=employee_domain(doc.employee)
        if not doc.domain:frappe.throw("عضویت سازمانی این کارمند ثبت نشده است؛ منابع انسانی باید ابتدا واحد کارمند را مشخص کند.")
    if old and (old.employee!=doc.employee or old.domain!=doc.domain or old.request_type!=doc.request_type):
        frappe.throw("هویت درخواست قابل تغییر نیست؛ درخواست جدید ثبت کنید")
    if not internal and doc.employee!=user:
        if not (leadership(user) or "Portal HR Manager" in roles(user) or doc.domain in managed_domains(user)):
            frappe.throw("ثبت درخواست برای این کارمند مجاز نیست",frappe.PermissionError)
    elif not internal and doc.domain not in domains(user) and not leadership(user):
        frappe.throw("حوزه درخواست باید از واحدهای شما باشد",frappe.PermissionError)
    if doc.employee not in frappe.get_all("Portal Assignment",filters={"domain":doc.domain,"enabled":1},pluck="user") and not leadership(doc.employee):
        frappe.throw("کارمند عضو فعال این حوزه نیست")
    if not frappe.db.get_value("User",doc.employee,"enabled"):frappe.throw("حساب کارمند فعال نیست")
    if doc.request_type not in ("Leave","Mission") or doc.duration_type not in ("Daily","Hourly"):frappe.throw("نوع درخواست نامعتبر است")
    if not (doc.details or "").strip():frappe.throw("شرح درخواست الزامی است")
    if doc.duration_type=="Hourly" and not doc.end_date:doc.end_date=doc.start_date
    if getdate(doc.end_date)<getdate(doc.start_date):frappe.throw("پایان قبل از شروع است")
    if doc.duration_type=="Hourly":
        if getdate(doc.start_date)!=getdate(doc.end_date) or not doc.start_time or not doc.end_time:frappe.throw("درخواست ساعتی باید در یک روز و با ساعت شروع و پایان باشد")
        start,end=get_time(doc.start_time),get_time(doc.end_time)
        minutes=(end.hour*60+end.minute)-(start.hour*60+start.minute)
        if minutes<=0:frappe.throw("ساعت پایان باید بعد از شروع باشد")
        doc.duration_summary=str(minutes)+" دقیقه"
    else:
        doc.start_time=None;doc.end_time=None
        doc.duration_summary=str((getdate(doc.end_date)-getdate(doc.start_date)).days+1)+" روز تقویمی (شامل تعطیلات)"
    if doc.request_type=="Mission" and not (doc.destination or "").strip():frappe.throw("مقصد مأموریت الزامی است")
    if doc.request_type=="Leave" and doc.leave_kind not in ("Annual","Sick","Unpaid","Other"):frappe.throw("نوع مرخصی را انتخاب کنید")
    if old and old.cancelled:frappe.throw("درخواست لغوشده قابل تغییر نیست")
    internal=bool(getattr(frappe.local,"staff_request_internal",False))
    if not internal:
        if old and any(str(doc.get(k) or "")!=str(old.get(k) or "") for k in APPROVAL_FIELDS):
            frappe.throw("وضعیت و مسئول تأیید فقط از بخش مرخصی و مأموریت تغییر می‌کند",frappe.PermissionError)
        if not old and (doc.approval_status not in (None,"","Pending") or any(doc.get(k) for k in APPROVAL_FIELDS[1:])):
            frappe.throw("وضعیت اولیه درخواست باید در انتظار تأیید باشد",frappe.PermissionError)
    changed=not old or any(str(doc.get(k) or "")!=str(old.get(k) or "") for k in CONTENT_FIELDS)
    if old and old.approval_status=="Approved" and changed:
        frappe.throw("درخواست تأییدشده قابل ویرایش نیست؛ برای اصلاح، درخواست قبلی را لغو و مورد جدید ثبت کنید")
    if doc.cancelled:doc.approval_status="Cancelled"
    elif not internal and changed:
        doc.approval_status="Pending";doc.approval_note=None;doc.approved_by=None;doc.approved_at=None
    from saeenaria_portal.rules import private_evidence
    private_evidence(doc)

def request_permission(doc,user=None,permission_type=None):
    user=user or frappe.session.user
    if user=="Guest":return False
    if permission_type=="create":return bool(domains(user)) or leadership(user) or "Portal HR Manager" in roles(user)
    return doc.employee==user or leadership(user) or "Portal HR Manager" in roles(user) or doc.domain in managed_domains(user)

def request_query(user=None):
    user=user or frappe.session.user
    if leadership(user) or "Portal HR Manager" in roles(user):return ""
    units=managed_domains(user)
    return "(`tabPortal Staff Request`.employee="+frappe.db.escape(user)+(" OR `tabPortal Staff Request`.domain IN ("+",".join(frappe.db.escape(d) for d in units)+")" if units else "")+")"

@frappe.whitelist()
def options():
    signed_in();user=frappe.session.user
    units=frappe.get_all("Portal Domain",fields=["name","title"],limit_page_length=0)
    if not leadership(user) and "Portal HR Manager" not in roles(user):units=[d for d in units if d.name in domains(user) or d.name in managed_domains(user)]
    can_assign=leadership(user) or "Portal HR Manager" in roles(user) or bool(managed_domains(user))
    users=frappe.get_all("User",filters={"enabled":1,"user_type":"System User","name":["!=","Guest"]},fields=["name","full_name"],limit_page_length=0) if can_assign else []
    for row in users:row["full_name"]=display_name(row.name)
    return {"domains":units,"users":users,"self":user,"self_name":display_name(user),"self_domain":employee_domain(user)}

@frappe.whitelist(methods=["POST"])
def submit_request(data):
    signed_in();data=frappe.parse_json(data)
    keys={"employee","domain","request_type","duration_type","leave_kind","start_date","end_date","start_time","end_time","destination","details","is_demo"}
    values={k:v for k,v in data.items() if k in keys}
    values.setdefault("employee",frappe.session.user)
    values["title"]=("مرخصی" if values.get("request_type")=="Leave" else "مأموریت")+" — "+display_name(values["employee"])
    doc=frappe.get_doc(dict(doctype="Portal Staff Request",**values)).insert(ignore_permissions=True)
    return {"name":doc.name,"message":"درخواست ثبت و برای بررسی ارسال شد."}

@frappe.whitelist(methods=["POST"])
def update_request(name,data,expected_modified):
    signed_in()
    frappe.db.get_value("Portal Staff Request",name,"name",for_update=True)
    doc=frappe.get_doc("Portal Staff Request",name)
    if not request_permission(doc):frappe.throw("اجازه ویرایش ندارید",frappe.PermissionError)
    if get_datetime(doc.modified)!=get_datetime(expected_modified):frappe.throw("درخواست تغییر کرده است؛ صفحه را تازه کنید")
    values=frappe.parse_json(data)
    for key in ("duration_type","leave_kind","start_date","end_date","start_time","end_time","destination","details"):
        if key in values:doc.set(key,values[key])
    doc.save(ignore_permissions=True)
    return {"name":doc.name,"message":"درخواست اصلاح و دوباره برای بررسی ارسال شد."}

@frappe.whitelist(methods=["POST"])
def cancel_request(name):
    signed_in();doc=frappe.get_doc("Portal Staff Request",name)
    if not request_permission(doc):frappe.throw("اجازه لغو ندارید",frappe.PermissionError)
    doc.cancelled=1;doc.save(ignore_permissions=True)
    doc.add_comment("Info","لغو درخواست توسط "+display_name(frappe.session.user))
    return "درخواست لغو شد و سابقه آن حفظ شد."

@frappe.whitelist()
def overview(is_demo=0):
    signed_in();user=frappe.session.user
    rows=frappe.get_all("Portal Staff Request",filters={"is_demo":cint(is_demo)},fields=["*"],order_by="modified desc",limit_page_length=0)
    rows=[row for row in rows if request_permission(row) or row.approver==user]
    for row in rows:
        row["employee_name"]=display_name(row.employee)
        row["approver_name"]=display_name(row.approver) if row.approver else "مدیر واحد"
        row["approved_by_name"]=display_name(row.approved_by) if row.approved_by else ""
        row["domain_title"]=frappe.db.get_value("Portal Domain",row.domain,"title")
        row["can_edit"]=request_permission(row)
        row["can_assign"]=can_manage(row,user)
        row["can_approve"]=can_approve(row,user)
        row.pop("evidence",None)
        for key in ("start_time","end_time"):
            if row.get(key):row[key]=str(get_time(row[key]))
    return {"requests":rows,"user":user}

def locked_request(name,expected_modified=None):
    frappe.db.get_value("Portal Staff Request",name,"name",for_update=True)
    doc=frappe.get_doc("Portal Staff Request",name)
    if expected_modified and get_datetime(doc.modified)!=get_datetime(expected_modified):frappe.throw("درخواست تغییر کرده است؛ صفحه را تازه کنید")
    return doc

@frappe.whitelist(methods=["POST"])
def assign_approver(name,approver,expected_modified):
    signed_in();doc=locked_request(name,expected_modified)
    if not can_manage(doc,frappe.session.user):frappe.throw("اجازه تعیین مسئول تأیید ندارید",frappe.PermissionError)
    if doc.cancelled:frappe.throw("درخواست لغوشده است")
    if approver and (approver==doc.employee or not frappe.db.exists("User",{"name":approver,"enabled":1,"user_type":"System User"})):frappe.throw("مسئول تأیید باید کاربر فعال و غیر از صاحب درخواست باشد")
    with internal_operation():
        doc.approver=approver or None;doc.approval_status="Pending";doc.approval_note=None;doc.approved_by=None;doc.approved_at=None
        doc.save(ignore_permissions=True)
    doc.add_comment("Info","تعیین مسئول تأیید درخواست توسط "+display_name(frappe.session.user)+": "+(display_name(approver) if approver else "مدیر واحد"))
    return "مسئول تأیید درخواست تعیین شد."

@frappe.whitelist(methods=["POST"])
def decide(name,status,note="",expected_modified=None):
    if not expected_modified:frappe.throw("نسخه درخواست مشخص نیست؛ صفحه را تازه و دوباره تلاش کنید")
    signed_in();doc=locked_request(name,expected_modified)
    if not can_approve(doc,frappe.session.user):frappe.throw("اجازه تأیید این درخواست را ندارید",frappe.PermissionError)
    if doc.approval_status!="Pending" or doc.cancelled:frappe.throw("درخواست در انتظار تأیید نیست")
    if status not in ("Approved","Returned"):frappe.throw("نتیجه نامعتبر است")
    note=(note or "").strip()
    with internal_operation():
        doc.approval_status=status;doc.approval_note=note.strip();doc.approved_by=frappe.session.user;doc.approved_at=now_datetime()
        doc.save(ignore_permissions=True)
    doc.add_comment("Info",("تأیید درخواست" if status=="Approved" else "برگشت درخواست برای اصلاح")+" توسط "+display_name(frappe.session.user)+": "+frappe.utils.escape_html(note.strip()))
    return "درخواست با موفقیت تأیید شد." if status=="Approved" else "درخواست با موفقیت برای اصلاح برگشت داده شد."

@frappe.whitelist()
def history(name):
    signed_in();doc=frappe.get_doc("Portal Staff Request",name)
    if not request_permission(doc) and doc.approver!=frappe.session.user:frappe.throw("اجازه مشاهده ندارید",frappe.PermissionError)
    from frappe.utils import strip_html
    return [strip_html(row.content) for row in frappe.get_all("Comment",filters={"reference_doctype":doc.doctype,"reference_name":doc.name,"comment_type":"Info"},fields=["content"],order_by="creation asc",limit_page_length=100)]

def migrate_legacy():
    if not admin(frappe.session.user):frappe.throw("فقط مدیر سامانه",frappe.PermissionError)
    count=0
    for row in frappe.get_all("Portal Activity Review",filters={"source_type":"Portal Staff Request"},fields=["*"]):
        if not frappe.db.exists("Portal Staff Request",row.source_name):continue
        doc=frappe.get_doc("Portal Staff Request",row.source_name)
        marker="انتقال سابقه از بررسی فعالیت: "+row.name
        if frappe.db.exists("Comment",{"reference_doctype":doc.doctype,"reference_name":doc.name,"content":marker}):continue
        frappe.db.set_value(doc.doctype,doc.name,dict(approval_status=row.status,approver=row.reviewer,approval_note=row.review_note,approved_by=row.reviewed_by,approved_at=row.reviewed_at),update_modified=False)
        for comment in frappe.get_all("Comment",filters={"reference_doctype":"Portal Activity Review","reference_name":row.name,"comment_type":"Info"},fields=["content","comment_by","comment_email","creation"]):
            entry=frappe.get_doc(dict(doctype="Comment",comment_type="Info",reference_doctype=doc.doctype,reference_name=doc.name,content=comment.content,comment_by=comment.comment_by,comment_email=comment.comment_email))
            entry.insert(ignore_permissions=True)
            frappe.db.set_value("Comment",entry.name,"creation",comment.creation,update_modified=False)
        doc.add_comment("Info",marker);count+=1
    return {"migrated":count}
