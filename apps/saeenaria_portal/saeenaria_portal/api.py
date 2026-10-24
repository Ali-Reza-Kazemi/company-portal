"""Stable HTTP API. Business rules live in services; existing URLs are preserved."""

import frappe

from saeenaria_portal.services import account, actions, people
from saeenaria_portal.services.actions import (
    timing_status,  # noqa: F401 - compatibility
)


@frappe.whitelist(methods=["POST"])
def export_actions(names, domain=None, start=None, end=None, is_demo=0, mine=None):
    return actions.export_actions(
        names=names, domain=domain, start=start, end=end, is_demo=is_demo, mine=mine
    )


@frappe.whitelist()
def dashboard(domain=None, start=None, end=None, is_demo=0, mine=None):
    return actions.dashboard(domain=domain, start=start, end=end, is_demo=is_demo, mine=mine)


@frappe.whitelist(methods=["POST"])
def update_progress(name, status, progress, result="", obstacle="", expected_modified=None):
    return actions.update_progress(
        name=name,
        status=status,
        progress=progress,
        result=result,
        obstacle=obstacle,
        expected_modified=expected_modified,
    )


@frappe.whitelist(methods=["POST"])
def save_action(data):
    return actions.save_action(data=data)


@frappe.whitelist()
def management(domain=None, is_demo=0):
    return actions.management(domain=domain, is_demo=is_demo)


@frappe.whitelist()
def calendar_holidays(start, end):
    return actions.calendar_holidays(start=start, end=end)


@frappe.whitelist()
def responsible_users(domain, all_users=0):
    return people.responsible_users(domain=domain, all_users=all_users)


@frappe.whitelist()
def people_overview():
    return people.people_overview()


@frappe.whitelist(methods=["POST"])
def set_unit_member(user, domain, is_manager=0, enabled=1, expected_modified=None):
    return people.set_unit_member(
        user=user,
        domain=domain,
        is_manager=is_manager,
        enabled=enabled,
        expected_modified=expected_modified,
    )


@frappe.whitelist(methods=["POST"])
def delete_unit_member(name, expected_modified):
    return people.delete_unit_member(name=name, expected_modified=expected_modified)


@frappe.whitelist(methods=["POST"])
def set_hr_manager(user, enabled):
    return people.set_hr_manager(user=user, enabled=enabled)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def template_responsibles(doctype, txt, searchfield, start, page_len, filters):
    return people.template_responsibles(
        doctype=doctype,
        txt=txt,
        searchfield=searchfield,
        start=start,
        page_len=page_len,
        filters=filters,
    )


@frappe.whitelist()
def template_assignment_access(domain):
    return people.template_assignment_access(domain=domain)


@frappe.whitelist()
def template_responsible_options(domain, all_users=0, template=None):
    return people.template_responsible_options(
        domain=domain, all_users=all_users, template=template
    )


@frappe.whitelist()
def environment_navigation():
    return account.environment_navigation()


@frappe.whitelist()
def my_account():
    return account.my_account()


@frappe.whitelist(methods=["POST"])
def update_my_profile(first_name, last_name="", mobile_no=""):
    return account.update_my_profile(
        first_name=first_name, last_name=last_name, mobile_no=mobile_no
    )
