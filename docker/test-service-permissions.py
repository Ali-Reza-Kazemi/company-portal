"""Real-role regression tests for stable API wrappers and privileged services."""

import csv
import io
from unittest.mock import patch

import frappe
from frappe.utils import today
from saeenaria_portal import api, reviews
from saeenaria_portal.purchase_reports import (
    general_settings,
    incoming_excel,
    incoming_orders,
    inventory_excel,
    product_catalog,
    workflow,
)
from saeenaria_portal.testing import portal_fixtures
from test_support import init_site

init_site()


def denied(fn, **kwargs):
    try:
        fn(**kwargs)
    except frappe.PermissionError:
        return
    raise AssertionError(f"Unauthorized call accepted: {fn.__name__}")


try:
    with portal_fixtures() as f:
        action = frappe.get_doc(
            dict(
                doctype="Portal Action",
                title="=HYPERLINK(1)",
                domain=f.domains[0],
                responsible=f.employee,
                due_date=today(),
                is_demo=1,
            )
        ).insert()
        membership = frappe.db.get_value(
            "Portal Assignment", {"user": f.employee, "domain": f.domains[0]}, "name"
        )
        for user in (f.employee, f.other, f.manager, "Guest"):
            frappe.set_user(user)
            denied(api.people_overview)
            denied(api.set_unit_member, user=f.other, domain=f.domains[0])
            denied(api.delete_unit_member, name=membership, expected_modified="2000-01-01")
            denied(api.set_hr_manager, user=f.other, enabled=1)
        for user in (f.employee, f.other, f.hr, f.manager, "Guest"):
            frappe.set_user(user)
            denied(workflow.freeze_forecast, values={})
            denied(workflow.save_event, kind="count", item_code="TEST", quantity=1, stock=1)
            denied(
                workflow.link_receipt,
                record="TEST",
                receipt_item="1",
                expected_modified="2000-01-01",
            )
            denied(inventory_excel.preview_counts, content="")
            denied(general_settings.save, proposed={}, expected_revision=1)
            denied(incoming_orders.save, data={})
            denied(incoming_orders.bulk_status, selections=[], status="Received")
            denied(incoming_excel.preview, content="")
            denied(incoming_excel.commit, token="test")
            denied(incoming_excel.template)
            denied(product_catalog.save, name="TEST", category="TEST", reference_code="TEST")
        frappe.set_user(f.other)
        denied(api.export_actions, names=[action.name], is_demo=1, mine=0)
        denied(
            api.update_progress,
            name=action.name,
            status="In Progress",
            progress=1,
            expected_modified=str(action.modified),
        )
        denied(api.save_action, data={"name": action.name, "title": "forbidden"})
        frappe.set_user(f.employee)
        api.export_actions(names=[action.name], domain=f.domains[0], is_demo=1)
        rows = list(csv.reader(io.StringIO(frappe.local.response.filecontent.decode("utf-8-sig"))))
        assert rows[1][0] == "'=HYPERLINK(1)"
        assert len(rows) == 2
        before_roles = set(frappe.get_roles(f.employee))
        api.update_my_profile("Test profile", "Updated", "123")
        assert set(frappe.get_roles(f.employee)) == before_roles
        api.update_progress(action.name, "In Progress", 10, expected_modified=str(action.modified))
        action.reload()
        assert action.progress == 10
        denied(
            reviews.assign_reviewer,
            name=frappe.db.get_value(
                "Portal Activity Review", {"source_name": action.name}, "name"
            ),
            reviewer=f.other,
            expected_modified="2000-01-01",
        )
        for user in (f.hr, f.director):
            frappe.set_user(user)
            assert any(row.name == f.employee for row in api.people_overview()["users"])
        frappe.set_user(f.hr)
        denied(api.set_hr_manager, user=f.other, enabled=1)
        api.set_unit_member(f.other, f.domains[0])
        frappe.set_user("Administrator")
        with patch.dict(frappe.conf, {"inventory_reporting_owner": f.employee}):
            assert workflow.owner() == f.employee
        with patch.dict(frappe.conf, {"inventory_reporting_owner": "Guest"}):
            try:
                workflow.owner()
            except frappe.ValidationError:
                pass
            else:
                raise AssertionError("Guest configured as inventory owner")
    print(
        "PASS real-role service matrix: Guest, employee, other unit, unit manager, HR, director; CSV scope; profile roles; progress; explicit inventory owner"
    )
finally:
    frappe.db.rollback()
    frappe.destroy()
