import frappe

MANAGERS = {"System Manager", "Portal Administrator"}

def roles(user):
    return set(frappe.get_roles(user))

def admin(user):
    return user == "Administrator" or bool(roles(user) & MANAGERS)

def domains(user):
    return frappe.get_all("Portal Assignment", filters={"user": user, "enabled": 1}, pluck="domain")

def can_domain(user, domain, write=False):
    if admin(user):
        return True
    if "Company Director" in roles(user):
        return not write
    return domain in domains(user)

def action_query(user=None):
    user = user or frappe.session.user
    if admin(user) or "Company Director" in roles(user):
        return ""
    allowed = domains(user)
    return "`tabPortal Action`.`domain` in ({})".format(
        ",".join(frappe.db.escape(d) for d in allowed)
    ) if allowed else "1=0"

def domain_query(user=None):
    return action_query(user).replace("`tabPortal Action`.`domain`", "`tabPortal Domain`.`name`")

def action_permission(doc, user=None, permission_type=None):
    return can_domain(user or frappe.session.user, doc.domain, permission_type not in (None, "read", "select", "print", "export"))

def domain_permission(doc, user=None, permission_type=None):
    user = user or frappe.session.user
    if permission_type not in (None, "read", "select", "print", "export"):
        return admin(user)
    return can_domain(user, doc.name)

def scoped_permission(doc, user=None, permission_type=None):
    user = user or frappe.session.user
    if doc.doctype in ("Portal Report", "Portal Decision") and "Company Director" in roles(user):
        return True
    return action_permission(doc, user, permission_type)

def _query(doctype):
    def condition(user=None):
        return action_query(user).replace("`tabPortal Action`", "`tab" + doctype + "`")
    return condition

for _doctype in ("Portal Metric", "Portal Metric Value", "Portal Report", "Portal Decision", "Portal Template", "Portal Record"):
    globals()[_doctype.lower().replace(" ", "_") + "_query"] = _query(_doctype)
