from unittest.mock import patch

import frappe
from frappe.utils import today

from saeenaria_portal.testing import portal_fixtures


def run():
    with portal_fixtures() as fixture:
        users = [fixture.employee, fixture.other]
        a = frappe.get_doc(
            {
                "doctype": "Portal Action",
                "title": "آزمون دسترسی",
                "domain": fixture.domains[0],
                "responsible": users[0],
                "due_date": today(),
                "progress": 0,
                "is_demo": 1,
            }
        ).insert()
        frappe.set_user(users[1])
        assert not frappe.get_list("Portal Action", filters={"name": a.name}), (
            "Other domain leaked in list"
        )
        try:
            doc = frappe.get_doc("Portal Action", a.name)
            doc.check_permission("read")
        except frappe.PermissionError:
            pass
        else:
            raise AssertionError("Other domain readable")
        try:
            doc = frappe.get_doc("Portal Action", a.name)
            doc.title = "تغییر غیرمجاز"
            doc.save()
        except frappe.PermissionError:
            pass
        else:
            raise AssertionError("Other domain writable")
        frappe.set_user(users[0])
        doc = frappe.get_doc("Portal Action", a.name)
        doc.progress = 25
        doc.save()
        assert frappe.get_list("Portal Action", filters={"name": a.name})
        try:
            doc.domain = fixture.domains[1]
            doc.save()
        except frappe.PermissionError:
            pass
        else:
            raise AssertionError("Unauthorized domain transfer")
        return {
            "cross_domain_list": "passed",
            "cross_domain_read": "passed",
            "cross_domain_write": "passed",
            "own_domain_update": "passed",
            "domain_transfer": "passed",
        }


def extended():
    from frappe.utils import getdate

    from saeenaria_portal.imports import import_csv
    from saeenaria_portal.metrics import forecast_error, overview, ratio, signal
    from saeenaria_portal.schedule import generate, next_workday

    with portal_fixtures() as fixture:
        assert ratio(1, 0) is None and ratio(None, 5) is None
        assert forecast_error([10, 20], [0, 0]) is None
        assert forecast_error([10, 20], [8, 22]) == 4 / 30 * 100
        m = frappe.get_doc(
            {
                "doctype": "Portal Metric",
                "domain": fixture.domains[0],
                "title": "Test metric",
                "definition": "Test",
                "unit": "count",
                "direction": "Higher",
                "has_default_target": 0,
            }
        ).insert()
        assert signal(0, None, "Higher", "Valid", m) == "No Target"
        assert signal(0, 10, "Higher", "Missing", m) == "Missing"
        frappe.get_doc(
            {
                "doctype": "Portal Metric Value",
                "domain": fixture.domains[0],
                "metric": m.name,
                "period_start": "2090-01-01",
                "period_end": "2090-01-31",
                "data_status": "Missing",
                "actual": 0,
                "is_demo": 1,
            }
        ).insert()
        values = overview(fixture.domains[0], "2090-01-01", "2090-01-31", 1)
        assert values[0]["actual"] is None and values[0]["target"] is None
        report = frappe.get_doc(
            {
                "doctype": "Portal Report",
                "domain": fixture.domains[0],
                "title": "آزمون گردش",
                "period_start": "2090-01-01",
                "period_end": "2090-01-31",
                "is_demo": 1,
            }
        ).insert()
        report.status = "Submitted"
        report.save()
        assert report.snapshot
        # Direct approval remains forbidden; approve through the real review API.
        report.status = "Approved"
        try:
            report.save()
        except frappe.ValidationError:
            report.reload()
        else:
            raise AssertionError("Direct report approval accepted")
        from saeenaria_portal.reviews import decide

        review = frappe.get_doc(
            "Portal Activity Review", {"source_key": "Portal Report:" + report.name}
        )
        frappe.set_user(fixture.director)
        decide(review.name, "Approved", "Test final approval", str(review.modified))
        frappe.set_user("Administrator")
        report.reload()
        assert report.status == "Approved"
        try:
            report.achievements = "تغییر غیرمجاز"
            report.save()
        except frappe.ValidationError:
            pass
        else:
            raise AssertionError("Approved report editable")
        assert next_workday("2026-10-15", set()).weekday() == 5
        assert next_workday("2026-10-15", {getdate("2026-10-17")}).weekday() == 6
        template = frappe.get_doc(
            {
                "doctype": "Portal Template",
                "domain": fixture.domains[1],
                "title": "آزمون برنامه",
                "responsible": "Administrator",
                "frequency": "Daily",
                "enabled": 1,
            }
        ).insert()
        from saeenaria_portal import schedule

        real_get_all = frappe.get_all

        def fixture_rows(doctype, *args, **kwargs):
            if doctype == "Portal Template":
                return [template]
            if doctype == "Portal Holiday":
                return []
            return real_get_all(doctype, *args, **kwargs)

        with patch.object(schedule.frappe, "get_all", side_effect=fixture_rows):
            first = generate("2090-01-01", "2090-01-07")["created"]
            second = generate("2090-01-01", "2090-01-07")["created"]
        assert first == 5 and second == 0
        for day in frappe.get_all(
            "Portal Action",
            filters={"schedule_key": ["like", template.name + ":%"]},
            pluck="due_date",
        ):
            assert getdate(day).weekday() not in (3, 4)
        content = f"title,domain,responsible,due_date,schedule_key,is_demo\nآزمون CSV,{fixture.domains[0]},Administrator,2090-01-01,{fixture.token},1\n"
        assert import_csv("Portal Action", content, 0)["valid"]
        assert not frappe.db.exists("Portal Action", {"schedule_key": "csv:" + fixture.token})
        assert import_csv("Portal Action", content, 1)["created"] == 1
        assert not import_csv("Portal Action", content, 0)["valid"]
        return {
            "division_by_zero": "passed",
            "missing_vs_zero": "passed",
            "target_missing": "passed",
            "approved_report_lock": "passed",
            "holiday_weekend": "passed",
            "recurrence_idempotency": "passed",
            "csv_preview_no_write": "passed",
            "csv_duplicate": "passed",
        }
