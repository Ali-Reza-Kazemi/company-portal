"""Disposable integration fixtures. Call only from tests, never request handlers."""

from contextlib import contextmanager
from uuid import uuid4

import frappe


@contextmanager
def portal_fixtures():
    original = frappe.session.user
    token = uuid4().hex[:12]
    savepoint = "portal_test_" + token
    users = []
    frappe.db.savepoint(savepoint)
    try:
        frappe.set_user("Administrator")
        domains = []
        for index in range(2):
            domains.append(
                frappe.get_doc(
                    {
                        "doctype": "Portal Domain",
                        "domain_code": f"test-{token}-{index}",
                        "title": f"Test domain {index}",
                    }
                )
                .insert()
                .name
            )
        for index, role in enumerate(
            (
                "Domain Officer",
                "Domain Officer",
                "Company Director",
                "Domain Officer",
                "Portal HR Manager",
            )
        ):
            email = f"portal-{token}-{index}@example.invalid"
            frappe.get_doc(
                {
                    "doctype": "User",
                    "email": email,
                    "first_name": f"Test {index}",
                    "send_welcome_email": 0,
                    "roles": [{"role": role}],
                }
            ).insert()
            users.append(email)
        for user, domain in zip(users, domains):
            frappe.get_doc(
                {
                    "doctype": "Portal Assignment",
                    "user": user,
                    "domain": domain,
                    "enabled": 1,
                }
            ).insert()
        frappe.get_doc(
            {
                "doctype": "Portal Assignment",
                "user": users[3],
                "domain": domains[0],
                "enabled": 1,
                "is_manager": 1,
            }
        ).insert()
        yield frappe._dict(
            domains=domains,
            employee=users[0],
            other=users[1],
            director=users[2],
            manager=users[3],
            hr=users[4],
            token=token,
        )
    finally:
        frappe.db.rollback(save_point=savepoint)
        frappe.set_user("Administrator")
        for user in users:
            frappe.clear_cache(user=user)
        frappe.set_user(original)
