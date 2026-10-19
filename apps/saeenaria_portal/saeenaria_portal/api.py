import frappe
from saeenaria_portal.user_names import display_name
from frappe.utils import getdate, get_datetime, today
from saeenaria_portal.permissions import admin, roles, can_assign, managed_domains, manage_people


def timing_status(row, date=None):
    date = getdate(date or today())
    if row.status == "Cancelled":
        return "Cancelled"
    if row.status == "Completed":
        if not row.completed_at or not row.completion_due_date:
            return "Unknown"
        return "On Time" if getdate(row.completed_at) <= getdate(row.completion_due_date) else "Late"
    due = getdate(row.due_date)
    return "Overdue" if due < date else "Due Today" if due == date else "Upcoming"


@frappe.whitelist()
def dashboard(domain=None, start=None, end=None, is_demo=0, mine=None):
    user = frappe.session.user
    if user == "Guest":
        frappe.throw("ورود لازم است", frappe.PermissionError)
    manager = admin(user) or "Company Director" in roles(user) or bool(managed_domains(user))
    mine = not manager if mine in (None, "") else bool(int(mine))
    filters = {"is_demo": int(is_demo or 0)}
    if mine:
        filters["responsible"] = user
    if domain:
        filters["domain"] = domain
    if start and end:
        if getdate(start) > getdate(end):
            frappe.throw("بازه تاریخ نادرست است")
        filters["due_date"] = ["between", [getdate(start), getdate(end)]]
    elif start:
        filters["due_date"] = [">=", getdate(start)]
    elif end:
        filters["due_date"] = ["<=", getdate(end)]
    actions = frappe.get_list("Portal Action", filters=filters,
        fields=["name", "title", "description", "domain", "responsible", "priority", "start_date", "due_date", "status", "progress", "obstacle", "result", "is_demo", "modified", "completed_at", "completed_by", "completion_due_date"],
        order_by="due_date asc", limit_page_length=500)
    reviews={row.source_name:row.status for row in frappe.get_all("Portal Activity Review",filters={"source_type":"Portal Action","source_name":["in",[a.name for a in actions]]},fields=["source_name","status"])} if actions else {}
    action_domains={name:frappe.db.get_value("Portal Domain",name,"title") for name in {row.domain for row in actions}}
    for row in actions:
        row["review_status"]=reviews.get(row.name)
        row["responsible_name"]=display_name(row.responsible)
        row["completed_by_name"]=display_name(row.completed_by) if row.completed_by else None
        row["domain_title"]=action_domains.get(row.domain)
        row["timing_status"] = timing_status(row)
        row["can_update"] = bool((admin(user) or row.responsible == user) and frappe.has_permission("Portal Action", "write", doc=frappe.get_doc("Portal Action", row.name)))
    return {
        "domains": frappe.get_list("Portal Domain", fields=["name", "title"], limit_page_length=100),
        "actions": actions, "user": user, "mine": mine, "today": today(),
    }


@frappe.whitelist(methods=["POST"])
def update_progress(name, status, progress, result="", obstacle="", expected_modified=None):
    doc = frappe.get_doc("Portal Action", name)
    doc.check_permission("write")
    if not admin(frappe.session.user) and doc.responsible != frappe.session.user:
        frappe.throw("فقط مسئول اقدام می‌تواند پیشرفت آن را ثبت کند", frappe.PermissionError)
    if not expected_modified or get_datetime(expected_modified) != get_datetime(doc.modified):
        frappe.throw("این اقدام تغییر کرده است؛ گزارش را تازه‌سازی و دوباره تلاش کنید", frappe.TimestampMismatchError)
    if status not in ("Open", "In Progress", "Blocked", "Completed"):
        frappe.throw("وضعیت انتخاب‌شده مجاز نیست")
    doc.status, doc.progress, doc.result, doc.obstacle = status, progress, result, obstacle
    doc.save()
    return {"name": doc.name, "timing_status": timing_status(doc)}


@frappe.whitelist(methods=["POST"])
def save_action(data):
    data = frappe.parse_json(data)
    allowed = {"title", "description", "domain", "responsible", "priority", "start_date", "due_date", "status", "progress", "obstacle", "result", "is_demo", "allow_external_responsible"}
    values = {key: value for key, value in data.items() if key in allowed}
    if data.get("name"):
        doc = frappe.get_doc("Portal Action", data["name"])
        doc.check_permission("write")
        doc.update(values)
        doc.save()
    else:
        doc = frappe.get_doc({"doctype": "Portal Action", **values}).insert()
    return doc.name


@frappe.whitelist()
def management(domain=None, is_demo=0):
    filters = {"is_demo": int(is_demo or 0)}
    if domain: filters["domain"] = domain
    result = {
        "reports": frappe.get_list("Portal Report", filters=filters, fields=["name","title","domain","status","achievements","obstacles","management_comment","next_plan","period_start","period_end","is_demo"], limit_page_length=100),
        "decisions": frappe.get_list("Portal Decision", filters=filters, fields=["name","title","domain","request","response","status","due_date","responded_at","responded_by","is_demo"], order_by="modified desc", limit_page_length=100),
    }
    for decision in result["decisions"]:
        decision["responded_by_name"]=display_name(decision.responded_by) if decision.responded_by else None
    return result

@frappe.whitelist()
def calendar_holidays(start, end):
    if frappe.session.user == "Guest":
        frappe.throw("ورود لازم است", frappe.PermissionError)
    start, end = getdate(start), getdate(end)
    if end < start or (end-start).days > 400:
        frappe.throw("بازه تقویم نامعتبر است")
    return frappe.get_all("Portal Holiday", filters={"enabled":1,"date":["between",[start,end]]}, fields=["date","title"], limit_page_length=400)


@frappe.whitelist()
def responsible_users(domain, all_users=0):
    """Return enabled members of an accessible domain, without exposing other users."""
    user = frappe.session.user
    if user == "Guest" or not frappe.has_permission("Portal Domain", "read", doc=frappe.get_doc("Portal Domain", domain)):
        frappe.throw("اجازه مشاهده این حوزه را ندارید", frappe.PermissionError)
    if int(all_users):
        if not can_assign(user,domain):
            frappe.throw("انتخاب کاربران سایر حوزه‌ها فقط برای مدیر مجاز است",frappe.PermissionError)
        return frappe.get_all("User",filters={"enabled":1,"user_type":"System User","name":["not in",["Guest","Administrator"]]},fields=["name","full_name"],order_by="full_name asc",limit_page_length=0)
    members = frappe.get_all("Portal Assignment", filters={"domain": domain, "enabled": 1}, pluck="user")
    if not can_assign(user, domain):
        members = [member for member in members if member == user]
    if not members:
        return []
    return frappe.get_all("User", filters={"enabled": 1, "name": ["in", list(set(members) - {"Guest"})]},
        fields=["name", "full_name"], order_by="full_name asc", limit_page_length=0)


@frappe.whitelist()
def people_overview():
    if not manage_people(frappe.session.user):
        frappe.throw("فقط مدیر ارشد یا مسئول منابع انسانی دسترسی دارد", frappe.PermissionError)
    users = frappe.get_all("User", filters={"name": ["not in", ["Guest", "Administrator"]], "user_type": "System User"}, fields=["name", "full_name", "enabled"], order_by="full_name asc", limit_page_length=0)
    return {"users": users, "domains": frappe.get_all("Portal Domain", fields=["name", "title"]),
        "assignments": frappe.get_all("Portal Assignment", fields=["name", "domain", "user", "enabled", "is_manager", "modified"], limit_page_length=0),
        "hr_users": frappe.get_all("Has Role", filters={"parenttype": "User", "role": "Portal HR Manager"}, pluck="parent"),
        "can_set_hr": admin(frappe.session.user) or "Company Director" in roles(frappe.session.user)}


@frappe.whitelist(methods=["POST"])
def set_unit_member(user, domain, is_manager=0, enabled=1, expected_modified=None):
    if not manage_people(frappe.session.user):
        frappe.throw("فقط مدیر ارشد یا مسئول منابع انسانی می‌تواند نقش واحد را تغییر دهد", frappe.PermissionError)
    if user in ("Guest", "Administrator") or not frappe.db.get_value("User", user, "enabled"):
        frappe.throw("کاربر فعال معتبر را انتخاب کنید")
    if not frappe.db.exists("Portal Domain", domain):
        frappe.throw("حوزه معتبر را انتخاب کنید")
    names = frappe.get_all("Portal Assignment", filters={"user": user, "domain": domain}, pluck="name")
    if len(names) > 1:
        frappe.throw("عضویت تکراری وجود دارد؛ مدیر سامانه باید آن را اصلاح کند")
    doc = frappe.get_doc("Portal Assignment", names[0]) if names else frappe.new_doc("Portal Assignment")
    if names and (not expected_modified or get_datetime(expected_modified) != get_datetime(doc.modified)):
        frappe.throw("عضویت تغییر کرده است؛ فهرست را تازه‌سازی کنید", frappe.TimestampMismatchError)
    doc.update({"user": user, "domain": domain, "is_manager": int(bool(int(is_manager))), "enabled": int(bool(int(enabled)))})
    doc.save(ignore_permissions=True)
    # Membership needs a base portal role; never grant an administrative role here.
    if doc.enabled and not (roles(user) & {"Domain Officer", "Portal Contributor", "Company Director", "System Manager", "Portal Administrator"}):
        member = frappe.get_doc("User", user)
        member.append("roles", {"role": "Portal Contributor"})
        member.save(ignore_permissions=True)
    frappe.clear_cache(user=user)
    return {"name": doc.name, "modified": doc.modified}


@frappe.whitelist(methods=["POST"])
def set_hr_manager(user, enabled):
    if not (admin(frappe.session.user) or "Company Director" in roles(frappe.session.user)):
        frappe.throw("تعیین مسئول منابع انسانی فقط در اختیار مدیر ارشد است", frappe.PermissionError)
    if user in ("Guest", "Administrator") or not frappe.db.get_value("User", user, "enabled"):
        frappe.throw("کاربر فعال معتبر را انتخاب کنید")
    member = frappe.get_doc("User", user)
    if int(enabled):
        if "Portal HR Manager" not in roles(user):
            member.append("roles", {"role": "Portal HR Manager"})
        if not (roles(user) & {"Domain Officer", "Portal Contributor", "Company Director", "System Manager", "Portal Administrator"}):
            member.append("roles", {"role": "Portal Contributor"})
    else:
        member.set("roles", [row for row in member.roles if row.role != "Portal HR Manager"])
    member.save(ignore_permissions=True)
    frappe.clear_cache(user=user)
    return {"user": user}


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def template_responsibles(doctype, txt, searchfield, start, page_len, filters):
    filters = frappe.parse_json(filters) if isinstance(filters, str) else (filters or {})
    domain = filters.get("domain")
    from saeenaria_portal.permissions import can_domain
    user = frappe.session.user
    if user == "Guest" or not domain or not can_domain(user, domain):
        frappe.throw("ابتدا حوزه مجاز را انتخاب کنید", frappe.PermissionError)
    if int(filters.get("all_users") or 0):
        if not can_assign(user, domain):
            frappe.throw("انتخاب مسئول سایر حوزه‌ها فقط برای مدیر مجاز است", frappe.PermissionError)
        members = frappe.get_all("User", filters={"enabled":1,"user_type":"System User"}, pluck="name")
    else:
        members = [row.name for row in responsible_users(domain)]
    if not members:return []
    rows = frappe.get_all("User",filters={"enabled":1,"name":["in",list(set(members)-{"Guest","Administrator"})]},
        or_filters={"name":["like","%"+txt+"%"],"full_name":["like","%"+txt+"%"]},fields=["name","full_name"],order_by="full_name asc",start=int(start),limit_page_length=min(int(page_len),50))
    return [[row.name,row.full_name] for row in rows]

@frappe.whitelist()
def template_assignment_access(domain):
    from saeenaria_portal.permissions import can_domain
    if frappe.session.user=="Guest" or not can_domain(frappe.session.user,domain):
        frappe.throw("حوزه مجاز نیست",frappe.PermissionError)
    return can_assign(frappe.session.user,domain)


@frappe.whitelist()
def template_responsible_options(domain, all_users=0, template=None):
    from saeenaria_portal.permissions import can_domain
    user=frappe.session.user
    if user=="Guest" or not can_domain(user,domain):
        frappe.throw("حوزه مجاز نیست",frappe.PermissionError)
    if int(all_users):
        if not can_assign(user,domain):
            frappe.throw("نمایش همه کاربران فقط برای مدیر مجاز است",frappe.PermissionError)
        users=frappe.get_all("User",filters={"enabled":1,"user_type":"System User","name":["not in",["Guest","Administrator"]]},fields=["name","full_name"],order_by="full_name asc",limit_page_length=0)
    else:
        users=responsible_users(domain)
    current=None
    if template and frappe.db.exists("Portal Template",template):
        doc=frappe.get_doc("Portal Template",template);doc.check_permission("read")
        if doc.responsible:
            current=frappe.db.get_value("User",doc.responsible,["name","full_name"],as_dict=True)
    return {"users":users,"current":current}


@frappe.whitelist()
def environment_navigation():
    user=frappe.session.user
    if user=="Guest":return {"links":[]}
    from saeenaria_portal.permissions import can_manage_desk
    if not can_manage_desk(user):
        return {"links":[]}
    links=[dict(label="پورتال روزانه",url="/portal",kind="portal")]
    if can_manage_desk(user):
        links += [dict(label="میزکار مدیریت",url="/portal-admin",kind="hub"),dict(label="فرم‌ها و فهرست‌ها",url="/desk/saeenaria-portal/portal-domain",kind="records")]
    if user=="Administrator" or "System Manager" in roles(user):
        links.append(dict(label="ساخت و تنظیمات فنی",url="/desk/build",kind="build"))
    links.append(dict(label="راهنمای محیط‌ها",url="/portal-guide",kind="guide"))
    return {"links":links}


@frappe.whitelist()
def my_account():
    user=frappe.session.user
    if user=="Guest":frappe.throw("ورود لازم است",frappe.PermissionError)
    doc=frappe.get_doc("User",user)
    return {"name":display_name(user),"login":user,"first_name":doc.first_name,"last_name":doc.last_name,"mobile_no":doc.mobile_no,
        "domains":frappe.get_all("Portal Domain",filters={"name":["in",frappe.get_all("Portal Assignment",filters={"user":user,"enabled":1},pluck="domain")]},fields=["title"])}

@frappe.whitelist(methods=["POST"])
def update_my_profile(first_name,last_name="",mobile_no=""):
    user=frappe.session.user
    if user=="Guest":frappe.throw("ورود لازم است",frappe.PermissionError)
    first_name=str(first_name or "").strip();last_name=str(last_name or "").strip();mobile_no=str(mobile_no or "").strip()
    if not first_name or len(first_name)>100 or len(last_name)>100 or len(mobile_no)>30:
        frappe.throw("نام و شماره تماس معتبر وارد کنید")
    doc=frappe.get_doc("User",user)
    # No user id, email, roles, permissions or enabled flag is accepted from the client.
    doc.first_name,doc.last_name,doc.mobile_no=first_name,last_name,mobile_no
    doc.save(ignore_permissions=True)
    frappe.db.set_value("Portal Template",{"responsible":user},"responsible_name",doc.full_name,update_modified=False)
    frappe.clear_cache(user=user)
    return {"name":display_name(user)}
