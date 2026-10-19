import frappe

MANAGERS = {"System Manager", "Portal Administrator"}

def roles(user):
    return set(frappe.get_roles(user))

def admin(user):
    return user == "Administrator" or bool(roles(user) & MANAGERS)

def domains(user):
    return frappe.get_all("Portal Assignment", filters={"user": user, "enabled": 1}, pluck="domain")

def manage_people(user):
    return admin(user) or bool(roles(user) & {"Company Director", "Portal HR Manager"})

def managed_domains(user):
    return frappe.get_all("Portal Assignment", filters={"user": user, "enabled": 1, "is_manager": 1}, pluck="domain")

def can_manage_desk(user):
    return user != "Guest" and (manage_people(user) or bool(managed_domains(user)))

def can_assign(user, domain):
    return admin(user) or "Company Director" in roles(user) or domain in managed_domains(user)

def can_domain(user, domain, write=False):
    if admin(user):
        return True
    if "Company Director" in roles(user):
        return not write
    return domain in domains(user)

def scope_query(user=None):
    user = user or frappe.session.user
    if admin(user) or "Company Director" in roles(user):
        return ""
    allowed = domains(user)
    return "`tabPortal Action`.`domain` in ({})".format(
        ",".join(frappe.db.escape(d) for d in allowed)
    ) if allowed else "1=0"

def action_query(user=None):
    user=user or frappe.session.user
    scope=scope_query(user)
    return "("+scope+" OR `tabPortal Action`.`responsible`="+frappe.db.escape(user)+")" if scope else ""

def domain_query(user=None):
    return scope_query(user).replace("`tabPortal Action`.`domain`", "`tabPortal Domain`.`name`")

def action_permission(doc, user=None, permission_type=None):
    user = user or frappe.session.user
    if permission_type == "create":
        return can_assign(user, doc.domain) or can_domain(user, doc.domain, write=True)
    if doc.responsible == user and permission_type in (None,"read","select","write","print","export"):
        return True
    if permission_type == "write":
        return admin(user) or (can_domain(user, doc.domain, write=True) and
            (doc.responsible == user or doc.domain in managed_domains(user)))
    return can_domain(user, doc.domain, permission_type not in (None, "read", "select", "print", "export"))


def domain_permission(doc, user=None, permission_type=None):
    user = user or frappe.session.user
    if permission_type not in (None, "read", "select", "print", "export"):
        return admin(user)
    return can_domain(user, doc.name)

def scoped_permission(doc, user=None, permission_type=None):
    user = user or frappe.session.user
    if doc.doctype == "Portal Metric" and permission_type not in (None, "read", "select", "print", "export"):
        return admin(user) or "Company Director" in roles(user)
    if doc.doctype in ("Portal Report", "Portal Decision", "Portal Metric Value") and "Company Director" in roles(user):
        return True
    return can_domain(user, doc.domain, permission_type not in (None, "read", "select", "print", "export"))

def _query(doctype):
    def condition(user=None):
        return scope_query(user).replace("`tabPortal Action`", "`tab" + doctype + "`")
    return condition

for _doctype in ("Portal Metric", "Portal Metric Value", "Portal Report", "Portal Decision", "Portal Template", "Portal Record"):
    globals()[_doctype.lower().replace(" ", "_") + "_query"] = _query(_doctype)
