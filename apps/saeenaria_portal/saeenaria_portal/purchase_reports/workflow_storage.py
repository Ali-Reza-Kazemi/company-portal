"""Immutable inventory snapshot persistence and presentation."""

import hashlib
import json

import frappe
from frappe.utils import now_datetime

from . import workflow_math as math
from .sources import json_default


def latest(kind):
    names = frappe.get_all(
        "Portal Inventory Snapshot",
        filters={"kind": kind, "policy": math.POLICY},
        pluck="name",
        order_by="period_end desc,captured_at desc",
        limit_page_length=1,
    )
    return frappe.get_doc("Portal Inventory Snapshot", names[0]) if names else None


def save_payload(payload):
    from .workflow import KINDS, owner

    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=json_default)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    existing = frappe.db.get_value("Portal Inventory Snapshot", {"snapshot_hash": digest}, "name")
    if existing:
        return frappe.get_doc("Portal Inventory Snapshot", existing)
    revision = (
        frappe.db.count(
            "Portal Inventory Snapshot",
            {
                "kind": payload["kind"],
                "period_start": payload["start"],
                "period_end": payload["end"],
                "policy": math.POLICY,
            },
        )
        + 1
    )
    doc = frappe.get_doc(
        dict(
            doctype="Portal Inventory Snapshot",
            title=f"پایش {KINDS[payload['kind']]} {payload['end']} ـ نسخه {revision}",
            domain="inventory",
            responsible=owner(),
            kind=payload["kind"],
            period_start=payload["start"],
            period_end=payload["end"],
            revision=revision,
            policy=math.POLICY,
            valuation_basis=payload["basis"],
            captured_at=now_datetime(),
            snapshot_hash=digest,
            metrics_json=json.dumps(payload["metrics"], ensure_ascii=False, default=json_default),
            payload=raw,
        )
    )
    frappe.local.inventory_capture_internal = True
    try:
        doc.insert(ignore_permissions=True)
    finally:
        frappe.local.inventory_capture_internal = False
    return doc


def publish_values(snapshot):
    from .workflow import metric_name, owner

    if snapshot.kind == "Cash":
        return
    payload = json.loads(snapshot.payload)
    for value in payload["metrics"]:
        metric_id = metric_name(value["code"], snapshot.policy)
        filters = {
            "metric": metric_id,
            "period_start": snapshot.period_start,
            "period_end": snapshot.period_end,
            "is_demo": 0,
        }
        name = frappe.db.get_value("Portal Metric Value", filters, "name")
        doc = (
            frappe.get_doc("Portal Metric Value", name)
            if name
            else frappe.get_doc(
                dict(
                    doctype="Portal Metric Value",
                    domain="inventory",
                    responsible=owner(),
                    **filters,
                )
            )
        )
        actual = float(value["value"]) if value["value"] is not None else 0
        evidence_hash = hashlib.sha256(
            json.dumps(
                {"policy": snapshot.policy, "metric": value},
                sort_keys=True,
                ensure_ascii=False,
            ).encode()
        ).hexdigest()[:12]
        src = "پایش خودکار موجودی / " + snapshot.policy + " / " + evidence_hash
        if (
            name
            and doc.actual == actual
            and doc.data_status == value["status"]
            and doc.source == src
        ):
            continue
        doc.actual = actual
        doc.data_status = value["status"]
        doc.source = src
        doc.source_updated_at = snapshot.captured_at
        doc.save(ignore_permissions=True)


def public_snapshot(doc):
    if not doc:
        return None
    payload = json.loads(doc.payload)
    payload.pop("evidence", None)
    report = frappe.db.get_value(
        "Portal Report",
        {"inventory_snapshot": doc.name},
        ["name", "status"],
        as_dict=True,
    )
    return {
        "name": doc.name,
        "captured_at": doc.captured_at,
        "revision": doc.revision,
        "report": report,
        **payload,
    }


def report_metric_snapshot(name):
    from .workflow import metric_name

    doc = frappe.get_doc("Portal Inventory Snapshot", name)
    p = json.loads(doc.payload)
    return [
        {
            "name": metric_name(v["code"], doc.policy),
            "title": v["title"],
            "domain": "inventory",
            "unit": v["unit"],
            "actual": v["value"],
            "target": None,
            "change": None,
            "signal": "Missing" if v["value"] is None else "No Target",
            "data_status": v["status"],
            "source": doc.valuation_basis,
            "updated_at": doc.captured_at,
            "period_start": doc.period_start,
            "period_end": doc.period_end,
        }
        for v in p["metrics"]
    ]
