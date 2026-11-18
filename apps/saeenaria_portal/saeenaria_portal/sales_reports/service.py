"""Authorized monthly reports, audited configuration, private immutable snapshots."""

import json
import re
import time
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import frappe
import jdatetime

from saeenaria_portal.permissions import admin, managed_domains, roles
from saeenaria_portal.purchase_reports.sources import json_default

from .calculations import (
    CHANNELS,
    DOCUMENT_CHANNELS,
    GROUPS,
    PIPELINES,
    POLICY,
    apply_targets,
    attribution_suggestions,
    calculate,
    num,
)

DT = "Portal Sales Settings"


def allowed(user=None):
    user = user or frappe.session.user
    return user != "Guest" and (
        admin(user)
        or "Company Director" in roles(user)
        or (frappe.conf.get("sales_domain") or "sales") in managed_domains(user)
    )


def require_access():
    if not allowed():
        frappe.throw(
            "گزارش فروش فقط برای مدیر شرکت و مدیر مجاز واحد فروش در دسترس است",
            frappe.PermissionError,
        )


def initialize():
    if not frappe.db.exists("Portal Domain", "sales"):
        frappe.get_doc(dict(doctype="Portal Domain", domain_code="sales", title="فروش")).insert(
            ignore_permissions=True
        )
    if not directory_cache():
        snapshot=read_latest(bounds()[0])
        if snapshot:
            save_directory(snapshot.get('crm_metadata',{}),snapshot.get('sellers',{}))


def bounds(month=None):
    if month is None:
        today = jdatetime.date.fromgregorian(date=frappe.utils.getdate(frappe.utils.today()))
        month = f"{today.year:04}-{today.month:02}"
    month = str(month).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    if not re.fullmatch(r"1[34]\d{2}-(0[1-9]|1[0-2])", month):
        frappe.throw("ماه شمسی را به شکل ۱۴۰۵-۰۸ وارد کنید")
    year, m = map(int, month.split("-"))
    start = jdatetime.date(year, m, 1).togregorian()
    end = jdatetime.date(year + (m == 12), m % 12 + 1, 1).togregorian() - timedelta(days=1)
    previous = jdatetime.date(year - (m == 1), (m - 2) % 12 + 1, 1).togregorian()
    return month, start, end, previous


def settings():
    return json.loads(frappe.db.get_single_value(DT, "payload") or "{}")


def save_config(config):
    doc = frappe.get_single(DT)
    # Single-document saves otherwise clear a password stored only in __Auth.
    key = doc.get_password("didar_api_key", raise_exception=False)
    if key:
        doc.didar_api_key = key
    doc.payload = json.dumps(config, ensure_ascii=False)
    doc.save(ignore_permissions=True)


def folder():
    return Path(frappe.get_site_path("private", "sales_reports"))


def job_state(month):
    path = folder() / (month + ".state")
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def set_job_state(month, status, detail=""):
    root = folder()
    root.mkdir(parents=True, exist_ok=True)
    temp = root / (uuid4().hex + ".tmp")
    temp.write_text(
        json.dumps({"status": status, "detail": detail, "updated": time.time()}), encoding="utf-8"
    )
    temp.replace(root / (month + ".state"))


def read_latest(month):
    root = folder()
    files = sorted(root.glob(month + "-*.json")) if root.exists() else []
    return json.loads(files[-1].read_text(encoding="utf-8")) if files else None


def directory_cache():
    path = folder() / "directory.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def customer_groups(snapshot):
    return {str(row['CustomerGroupId']): str(row.get('CustomerGroupTitle') or 'بدون نام')
            for row in (snapshot or {}).get('facts', {}).get('sales', [])
            if row.get('CustomerGroupId') is not None}


def save_directory(metadata, sellers):
    if not metadata.get("available"):
        return
    data = {
        k: metadata.get(k, {}) for k in ("seller_choices", "seller_aliases", "inactive_sellers", "customer_catalog")
    }
    data["sellers"] = sellers
    temp = folder() / (uuid4().hex + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    temp.replace(folder() / "directory.json")


def calculation_settings(config, metadata):
    result = deepcopy(config)
    result['customer_catalog'] = metadata.get('customer_catalog') or []
    aliases = metadata.get("seller_aliases", {})
    for record in [
        *result.get("invoices", {}).values(),
        *result.get("targets", []),
        *result.get("customer_rules", []),
        *result.get("customer_references", {}).values(),
        *result.get("customer_group_sellers", {}).values(),
    ]:
        record["seller"] = aliases.get(record.get("seller"), record.get("seller"))
    catalog = frappe.get_all(
        "Portal Product Catalog",
        fields=["item_code", "category", "reference_code", "source_conflict"],
        limit_page_length=0,
    )
    categories = {r.item_code: r.category for r in catalog if r.category and not r.source_conflict}
    result["products"] = {
        r.item_code: categories.get(r.item_code) or categories.get(r.reference_code) or ""
        for r in catalog
        if not r.source_conflict
    }
    result["group_labels"] = {name: name for name in sorted(set(categories.values()))}
    return result


def current_snapshot(snap, config, start, end, previous):
    snap = deepcopy(snap)
    metadata = snap.get("crm_metadata", {})
    directory = directory_cache()
    if directory:
        metadata.update(
            {
                k: directory[k]
                for k in ("seller_choices", "seller_aliases", "inactive_sellers", "customer_catalog")
                if k in directory
            }
        )
        snap["sellers"] = {**snap.get("sellers", {}), **directory.get("sellers", {})}
    calc = calculation_settings(config, metadata)
    facts = snap.get("facts")
    if facts:
        aliases = metadata.get("seller_aliases", {})
        deals = [
            {**d, "seller": aliases.get(d.get("seller"), d.get("seller"))} for d in facts["deals"]
        ]
        if metadata.get('customer_catalog'):
            from .channels import tagged_customer_names
            from .matching import customer_name
            tagged_names = tagged_customer_names(metadata['customer_catalog'])
            tagged = {r['id'] for r in metadata['customer_catalog'] if r.get('reseller')}
            for deal in deals:
                if 'customer_ids' in deal:
                    deal['customer_reseller'] = bool(set(deal['customer_ids']) & tagged)
                else:
                    deal['customer_reseller'] = any(customer_name(n) in tagged_names for n in deal.get('customer_names', []))
        snap.update(
            calculate(
                facts["sales"],
                deals,
                facts["activities"],
                calc,
                start,
                end,
                previous,
                facts["first"],
            )
        )
        snap["suggestions"] = attribution_suggestions(
            snap["invoices"], deals, calc.get("pipelines", PIPELINES), facts['sales'], snap.get('sellers', {}), calc.get('customer_group_sellers', {})
        )
        from .matching import invoice_customer_names
        from .manual_matching import reserved_deals
        for key, proposal in list(snap['suggestions'].items()):
            if (proposal.get('confidence') in ('document','document_minor_difference') or proposal.get('document_confidence')) and set(proposal.get('deal_ids',[])) & reserved_deals(config,key):
                del snap['suggestions'][key]
        invoice_customer_names(snap['invoices'], deals, metadata.get('customer_catalog', []),
                               calc.get('invoices', {}), snap['suggestions'])
        from .repair_sellers import annotate
        annotate(snap['invoices'], facts['sales'], deals, config, metadata)
    snap["rows"] = apply_targets(
        snap.get("rows", []),
        config.get("targets", []),
        metadata.get("seller_aliases", {}),
        start,
        snap.get("sellers", {}),
        snap.get("group_labels", GROUPS),
    )
    from .facilitators import annotate as annotate_facilitators
    annotate_facilitators(snap, config, start, end)
    from decimal import Decimal
    repair_rows = []
    seller_names = {**snap.get('sellers', {}), **metadata.get('seller_choices', {})}
    for invoice in snap.get('invoices', []):
        if not invoice.get('is_repair') or invoice.get('excluded') or not str(start) <= str(invoice['date']) <= str(end):
            continue
        channel = 'reseller' if invoice.get('customer_reseller') else 'consumer'
        seller = invoice.get('repair_sales_seller')
        facilitator = invoice.get('facilitator') or {}
        row = dict(invoice, repair_channel=channel, repair_seller=seller,
                   repair_seller_name=seller_names.get(seller, 'کارشناس نامشخص'),
                   repair_facilitator_amount=facilitator.get('amount', 0))
        repair_rows.append(row)
        if not seller:
            continue
        performance = next((item for item in snap.get('rows', [])
                            if item['seller'] == seller and item['channel'] == channel), None)
        if performance is None:
            performance = dict(seller=seller, seller_name=row['repair_seller_name'], channel=channel,
                               actual=0, invoice_count=0, sale_value=0, gross=0, discount=0)
            snap.setdefault('rows', []).append(performance)
        performance['actual'] = float(Decimal(str(performance.get('actual') or 0)) + Decimal(str(invoice.get('amount') or 0)))
        performance['invoice_count'] = int(performance.get('invoice_count') or 0) + 1
        performance['repair_invoice_count'] = int(performance.get('repair_invoice_count') or 0) + 1
        performance['repair_sales'] = float(Decimal(str(performance.get('repair_sales') or 0)) + Decimal(str(invoice.get('amount') or 0)))
        performance['repair_facilitator_cost'] = float(Decimal(str(performance.get('repair_facilitator_cost') or 0)) + Decimal(str(facilitator.get('amount') or 0)))
        performance['facilitator_cost'] = float(Decimal(str(performance.get('facilitator_cost') or 0)) + Decimal(str(facilitator.get('amount') or 0)))
        performance['after_facilitator'] = float(Decimal(str(performance['actual'])) - Decimal(str(performance['facilitator_cost'])))
        if performance.get('target'):
            performance['achievement'] = float(Decimal(str(performance['actual'])) * 100 / Decimal(str(performance['target'])))
    snap['repair_rows'] = repair_rows
    return snap


@frappe.whitelist()
def export_invoices(month=None, scope='all'):
    require_access()
    from .excel import export, TABS
    if scope not in {'all', *TABS}:
        frappe.throw('تب انتخاب‌شده معتبر نیست')
    view = report(month)
    if not view.get('snapshot'):
        frappe.throw('ابتدا گزارش ماه را دریافت کنید')
    from .sources import quotation_creators_for_export
    invoices = [row for row in view['snapshot'].get('invoices', [])
                if view['start'] <= row['date'] <= view['end']]
    def invoice_tab(row):
        return 'excluded' if row.get('excluded') else 'repair' if row.get('is_repair') else 'assigned' if row.get('mapped') else 'unassigned'
    selected = [row for row in invoices if scope == 'all' or invoice_tab(row) == scope]
    creators = quotation_creators_for_export(selected)
    for row in selected:
        row['quotation_creator_name'] = creators.get(row['key'])
    frappe.local.response.filename = f'sales-invoices-{view["month"]}-{scope}.xlsx'
    frappe.local.response.filecontent = export(view, scope)
    frappe.local.response.type = 'binary'
    frappe.local.response.display_content_as = 'attachment'


@frappe.whitelist()
def export_performance(month=None):
    """Export monthly performance and the related repair invoices with column notes."""
    require_access()
    from .performance_excel import export
    view = report(month)
    if not view.get('snapshot'):
        frappe.throw('ابتدا گزارش ماه را دریافت کنید')
    frappe.local.response.filename = f'sales-performance-{view["month"]}.xlsx'
    frappe.local.response.filecontent = export(view)
    frappe.local.response.type = 'binary'
    frappe.local.response.display_content_as = 'attachment'


@frappe.whitelist()
def deal_candidates(month, key, days=30):
    require_access()
    from .manual_matching import candidates
    month, start, end, previous = bounds(month)
    days = int(days)
    if days not in (7, 15, 30, 60, 90):
        frappe.throw('بازه زمانی معتبر نیست')
    config = settings()
    raw = read_latest(month)
    if not raw:
        frappe.throw('ابتدا گزارش ماه را دریافت کنید')
    snap = current_snapshot(raw, config, start, end, previous)
    invoice = next((i for i in snap['invoices'] if i['key']==key and str(start)<=i['date']<=str(end)), None)
    if not invoice or invoice.get('is_repair') or invoice.get('excluded') or not key.startswith('Sale:'):
        frappe.throw('این سند برای اتصال معامله فروش مجاز نیست')
    aliases = snap.get('crm_metadata', {}).get('seller_aliases', {})
    invoice = {**invoice, 'items': [r for r in raw.get('facts', {}).get('sales', [])
               if str(r.get('DocumentType')) + ':' + str(r.get('DocumentId')) == key]}
    deals = [{**d, 'seller':aliases.get(d.get('seller'),d.get('seller'))} for d in raw.get('facts', {}).get('deals', [])]
    return dict(invoice=invoice, deals=candidates(invoice,deals,config,snap.get('sellers',{}),days),
                revision=str(frappe.db.get_single_value(DT,'modified')), captured_at=raw.get('captured_at'))


@frappe.whitelist()
def candidate_detail(month, key, deal_id, days=30):
    context = deal_candidates(month, key, days)
    candidate = next((d for d in context['deals'] if d['id']==deal_id), None)
    if not candidate:
        frappe.throw('معامله دیگر قابل انتخاب نیست؛ فهرست را دوباره دریافت کنید')
    from .didar import Client
    api_key = frappe.get_single(DT).get_password('didar_api_key', raise_exception=False)
    if not api_key:
        frappe.throw('کلید دیدار ثبت نشده است')
    detail = Client(api_key).request('deal_detail', {'Id':deal_id})
    if not isinstance(detail, dict) or detail.get('Id') != deal_id:
        frappe.throw('جزئیات معامله معتبر نیست')
    candidate.update(title=detail.get('Title') or candidate['title'], code=detail.get('Code'),
                     total=detail.get('FinalAdjustmentPrice'),
                     items=[{k:r.get(k) for k in ('ProductCode','Quantity','UnitPrice','Price','Discount','TaxPrice')} for r in detail.get('Items') or []])
    from .manual_matching import item_overlap
    candidate['item_match'] = item_overlap(context['invoice'].get('items'), candidate['items'])
    return dict(deal=candidate, revision=context['revision'])


@frappe.whitelist()
def invoice_details(month, key):
    require_access()
    month, start, end, _ = bounds(month)
    snapshot = read_latest(month) or {}
    rows = [r for r in snapshot.get('facts', {}).get('sales', [])
            if str(r.get('DocumentType')) + ':' + str(r.get('DocumentId')) == str(key)
            and str(start) <= str(r.get('DocumentDate'))[:10] <= str(end)]
    if not rows:
        frappe.throw('جزئیات این سند در گزارش ماه انتخاب‌شده موجود نیست؛ دریافت مجدد را انجام دهید')
    items = []
    totals = {k: num(0) for k in ('gross', 'discount', 'amount', 'tax', 'addition', 'total')}
    for index, row in enumerate(rows, 1):
        gross, discount = num(row.get('GrossPrice')), num(row.get('Discount'))
        amount = gross - discount
        tax = num(row.get('Tax')) + num(row.get('Duty'))
        addition = num(row.get('Addition'))
        total = num(row['NetPrice']) if row.get('NetPrice') is not None else amount + tax + addition
        values = dict(gross=gross, discount=discount, amount=amount, tax=tax, addition=addition, total=total)
        items.append(dict(index=index, code=str(row.get('ItemCode') or ''), title=row.get('ItemTitle') or '—',
                          quantity=float(num(row.get('Quantity'))), unit=row.get('UnitTitle') or '—',
                          fee=float(num(row.get('Fee'))), **{k:float(v) for k,v in values.items()}))
        for name, value in values.items():
            totals[name] += value
    first = rows[0]
    from .facilitators import cost
    facilitator = cost(dict(key=key,customer_id=str(first.get('CustomerId') or ''),amount=totals['amount']),settings())
    from .sources import invoice_creator
    try:
        creator = invoice_creator(first.get('DocumentType'), first.get('DocumentId')) or {}
        creator_status = 'available' if creator else 'missing'
    except Exception:
        creator, creator_status = {}, 'unavailable'
    return dict(key=key, number=str(first.get('DocumentNumber') or ''), date=str(first.get('DocumentDate'))[:10],
                facilitator=facilitator, revision=str(frappe.db.get_single_value(DT,'modified')),
                creator_name=creator.get('creator_name'), creator_username=creator.get('creator_username'), creator_status=creator_status,
                quotation_creator_name=creator.get('quotation_creator_name'), quotation_creator_username=creator.get('quotation_creator_username'),
                quotation_creator_status=('not_applicable' if first.get('DocumentType') != 'Sale' else
                                          'unavailable' if creator_status == 'unavailable' else
                                          'present' if creator.get('quotation_id') else 'missing'),
                customer=' '.join(str(first.get(k) or '').strip() for k in ('CustomerName', 'CustomerLastName')).strip(),
                customer_id=str(first.get('CustomerId') or ''), document_type=first.get('DocumentType'),
                quotation_number=first.get('QuotationNumber'), quotation_status=first.get('QuotationStatus'),
                captured_at=snapshot.get('captured_at'), items=items,
                totals={k:float(v) for k,v in totals.items()})


@frappe.whitelist()
def report(month=None):
    require_access()
    month, start, end, previous = bounds(month)
    config = settings()
    snap = read_latest(month)
    if snap:
        snap = current_snapshot(snap, config, start, end, previous)
    has_facts = bool(snap and snap.get("facts"))
    groups = customer_groups(snap)
    if snap:
        snap.pop("facts", None)
    job = job_state(month)
    busy = job.get("status") in ("queued", "running") and time.time() - job.get("updated", 0) < 1200
    targets = [t for t in config.get("targets", []) if t["period_start"] == str(start)]
    return dict(
        month=month,
        start=str(start),
        end=str(end),
        channels=CHANNELS,
        document_channels=DOCUMENT_CHANNELS,
        groups=(snap or {}).get("group_labels", {}),
        snapshot=snap,
        directory=directory_cache(),
        customer_groups=groups,
        customer_group_sellers=config.get('customer_group_sellers', {}),
        targets=targets,
        revision=str(frappe.db.get_single_value(DT, "modified")),
        config_changed=bool(
            snap
            and not has_facts
            and snap.get("config", {}).get("invoices") != config.get("invoices")
        ),
        api_configured=bool(
            frappe.get_single(DT).get_password("didar_api_key", raise_exception=False)
        ),
        can_configure_api=admin(frappe.session.user),
        error=(folder() / (month + ".error")).exists() and not busy,
        busy=busy,
        job=job,
        pipelines=config.get("pipelines", PIPELINES),
        products=config.get("products", {}),
        assignments=config.get("invoices", {}),
        customer_rules=config.get("customer_rules", []),
        customer_references=config.get("customer_references", {}),
        facilitator_customers=config.get('facilitator_customers', {}),
        facilitator_customer_history=config.get('facilitator_customer_history', []),
        excluded_customers=config.get('excluded_customers', {}),
    )


@frappe.whitelist()
def target_data(month=None):
    require_access()
    month, start, _, _ = bounds(month)
    config = settings()
    return {
        "month": month,
        "targets": [t for t in config.get("targets", []) if t["period_start"] == str(start)],
        "revision": str(frappe.db.get_single_value(DT, "modified")),
    }


@frappe.whitelist(methods=["POST"])
def refresh(month=None):
    require_access()
    month, _, _, _ = bounds(month)
    if report(month)["busy"]:
        return {"queued": True, "already_running": True}
    set_job_state(month, "queued")
    frappe.enqueue(
        "saeenaria_portal.sales_reports.service.build",
        queue="long",
        timeout=900,
        month=month,
        enqueue_after_commit=True,
        job_id="sales-report-" + month,
        deduplicate=True,
    )
    return {"queued": True}


def build(month=None):
    from filelock import FileLock

    from .sources import load

    month, start, end, previous = bounds(month)
    root = folder()
    root.mkdir(parents=True, exist_ok=True)
    with FileLock(str(root / (month + ".lock")), timeout=0):
        config = settings()
        set_job_state(month, "running")
        try:
            sales, deals, activities, first, metadata, sellers = load(start, end, previous)
            save_directory(metadata, sellers)
            set_job_state(month, "running", "محاسبه گزارش و تطبیق داده‌ها")
            # Both Didar membership Id and UserId identify the same person.
            aliases = metadata.get("seller_aliases", {})
            calculation_config = calculation_settings(config, metadata)
            for assignment in calculation_config.get("invoices", {}).values():
                assignment["seller"] = aliases.get(
                    assignment.get("seller"), assignment.get("seller")
                )
            for target in calculation_config.get("targets", []):
                target["seller"] = aliases.get(target.get("seller"), target.get("seller"))
            for deal in deals:
                deal["seller"] = aliases.get(deal.get("seller"), deal.get("seller"))
            result = calculate(
                sales, deals, activities, calculation_config, start, end, previous, first
            )
            result.update(
                month=month,
                start=str(start),
                end=str(end),
                captured_at=str(frappe.utils.now_datetime()),
                policy=POLICY,
                config=config,
                crm_metadata=metadata,
                sellers=sellers,
                facts={"sales": sales, "deals": deals, "activities": activities, "first": first},
                suggestions=attribution_suggestions(
                    result["invoices"], deals, config.get("pipelines", PIPELINES), sales, sellers, calculation_config.get('customer_group_sellers', {})
                ),
                products=sorted({str(r["ItemCode"]) for r in sales}),
                product_titles={str(r["ItemCode"]): str(r["ItemTitle"]) for r in sales},
                provisional=True,
                notes=[
                    "کانال و کارشناس فاکتور از تطبیق تأییدشده پورتال؛ کاریز و مسئول معامله از دیدار.",
                    "دیدار فقط از API رسمی خوانده می‌شود؛ زمان‌ها به تهران تبدیل می‌شوند.",
                    "فاکتورهای بدون تطبیق در عملکرد هیچ کارشناس منظور نمی‌شوند.",
                    "واحد مبالغ ریال؛ تعداد کالا خالص پس از برگشت است.",
                ],
            )
            if not metadata["available"]:
                for row in result["rows"]:
                    row["conversion"] = row["followup"] = None
            for row in result["rows"]:
                row["seller_name"] = sellers.get(row["seller"], row["seller"])
            name = (
                month
                + "-"
                + frappe.utils.now_datetime().strftime("%Y%m%d%H%M%S%f")
                + "-"
                + uuid4().hex
            )
            temp = root / (name + ".tmp")
            temp.write_text(
                json.dumps(result, ensure_ascii=False, default=json_default), encoding="utf-8"
            )
            temp.replace(root / (name + ".json"))
            (root / (month + ".error")).unlink(missing_ok=True)
            set_job_state(month, "done")
            return {"rows": len(result["rows"]), "unmapped": result["unmapped_invoices"]}
        except Exception as exc:
            # Driver messages may contain credentials. Publish only a generic failure.
            from .didar import DidarError

            detail = str(exc) if isinstance(exc, DidarError) else type(exc).__name__
            (root / (month + ".error")).write_text(detail, encoding="utf-8")
            set_job_state(month, "failed")
            return {"error": "دریافت ناموفق بود؛ آخرین گزارش موفق حفظ شد"}


def remember_customer_reference(config, invoice, assignment):
    if assignment.get('confidence') == 'customer_relation':
        return  # Employment/customer relationships must be checked again for each invoice.
    customer = str(invoice.get("customer_id") or "")
    if not customer or invoice.get("is_repair") or assignment.get("channel") not in CHANNELS:
        return
    references = config.setdefault("customer_references", {})
    previous = references.get(customer)
    replacement = dict(
        customer_id=customer,
        customer_name=invoice.get("customer"),
        seller=assignment["seller"],
        channel=assignment["channel"],
        method="customer-reference",
        source_invoice=invoice["key"],
        confirmed_by=frappe.session.user,
        confirmed_at=str(frappe.utils.now_datetime()),
    )
    references[customer] = replacement
    config.setdefault("customer_reference_history", []).append(
        dict(customer_id=customer, previous=previous, replacement=replacement)
    )


@frappe.whitelist(methods=["POST"])
def save(kind, values, revision):
    require_access()
    # Serialize edits to the Single document, then compare the browser's revision.
    frappe.db.sql("SELECT name FROM `tabDocType` WHERE name=%s FOR UPDATE", (DT,))
    current_revision = str(frappe.db.get_single_value(DT, "modified"))
    if revision != current_revision:
        frappe.throw("تنظیمات توسط کاربر دیگری تغییر کرده؛ صفحه را دوباره دریافت کنید")
    values = frappe.parse_json(values)
    if not isinstance(values, dict):
        frappe.throw("ورودی نامعتبر")
    config = settings()
    reference_conflicts = []
    if kind in ('facilitator_rename', 'facilitator_transfer'):
        old = ' '.join(str(values.get('old_name') or '').split())
        new = ' '.join(str(values.get('new_name') or '').split())
        if not old or not new or len(new) > 140:
            frappe.throw('نام فعلی و نام جدید آسان‌ساز را وارد کنید')
        matches = [record for record in config.get('facilitator_customers', {}).values() if record.get('name') == old]
        if not matches:
            frappe.throw('آسان‌سازی با این نام پیدا نشد')
        for record in config.get('facilitator_customers', {}).values():
            if record.get('name') == old:
                record['name'] = new
        for record in config.get('facilitator_customer_history', []):
            if record.get('name') == old:
                record['name'] = new
        for record in config.get('facilitator_invoices', {}).values():
            if record.get('name') == old:
                record['name'] = new
        config.setdefault('facilitator_history', []).append(dict(kind=kind, previous=old, replacement=new,
            changed_by=frappe.session.user, changed_at=str(frappe.utils.now_datetime())))
    elif kind == 'facilitator_customer_dated':
        customer = str(values.get('customer_id') or '')
        from_date = str(values.get('from_date') or '')
        name = ' '.join(str(values.get('name') or '').split())
        from frappe.utils import getdate
        try:
            from_date = str(getdate(from_date))
            rate = Decimal(str(values.get('rate')))
        except Exception:
            frappe.throw('تاریخ شروع و درصد پورسانت معتبر وارد کنید')
        if not customer or not name or len(name) > 140 or not rate.is_finite() or not 0 <= rate <= 100:
            frappe.throw('مشتری، نام آسان‌ساز و درصد معتبر لازم است')
        record = dict(customer_id=customer, from_date=from_date, name=name, rate=float(rate),
                      changed_by=frappe.session.user, changed_at=str(frappe.utils.now_datetime()))
        config.setdefault('facilitator_customer_history', []).append(record)
        config.setdefault('facilitator_history', []).append(dict(kind=kind, key=customer, replacement=record,
            changed_by=frappe.session.user, changed_at=str(frappe.utils.now_datetime())))
    elif kind in ('facilitator_customer','facilitator_invoice'):
        from decimal import Decimal, InvalidOperation
        month, start, end, _ = bounds(values.get('month'))
        raw = read_latest(month) or {}
        customer = str(values.get('customer_id') or '')
        field = 'facilitator_customers' if kind == 'facilitator_customer' else 'facilitator_invoices'
        records = config.setdefault(field,{})
        if kind == 'facilitator_customer':
            identity = customer
            known = next((r for r in raw.get('facts',{}).get('sales',[]) if str(r.get('CustomerId'))==customer),None)
            # Match the customer selector: saved references and dated rules remain
            # valid even when the customer has no invoices in the selected month.
            saved_customer = next((r for r in [*config.get('customer_rules', []),
                *config.get('customer_references', {}).values(), *records.values()]
                if str(r.get('customer_id') or '') == customer), None)
            if not customer or (not known and not saved_customer):
                frappe.throw('مشتری معتبر را از گزارش انتخاب کنید')
        else:
            identity = str(values.get('key') or '')
            known = next((r for r in raw.get('facts',{}).get('sales',[]) if str(r.get('DocumentType'))+':'+str(r.get('DocumentId'))==identity and str(start)<=str(r.get('DocumentDate'))[:10]<=str(end)),None)
            if not known:
                frappe.throw('فاکتور در ماه انتخاب‌شده یافت نشد')
        original = records.get(identity)
        replacement = None
        if values.get('remove') is not True:
            name = ' '.join(str(values.get('name') or '').split())
            if not name or len(name)>140:
                frappe.throw('نام آسان ساز فروش لازم است (حداکثر ۱۴۰ حرف)')
            try:
                value = Decimal(str(values.get('rate' if kind=='facilitator_customer' else 'amount')))
            except (InvalidOperation, ValueError):
                frappe.throw('درصد یا مبلغ معتبر وارد کنید')
            if not value.is_finite():
                frappe.throw('درصد یا مبلغ معتبر وارد کنید')
            replacement = dict(name=name,changed_by=frappe.session.user,changed_at=str(frappe.utils.now_datetime()))
            if kind == 'facilitator_customer':
                if not 0<=value<=100:
                    frappe.throw('درصد باید بین صفر و صد باشد')
                customer_name = ' '.join(dict.fromkeys(str(known.get(k) or '').strip() for k in ('CustomerName','CustomerLastName'))).strip() if known else saved_customer.get('customer_name','')
                replacement.update(rate=float(value),customer_id=customer,customer_name=customer_name)
            else:
                if value != value.to_integral_value() or abs(value)>Decimal('1000000000000000') or (identity.startswith('Return:') and value>0) or (identity.startswith('Sale:') and value<0):
                    frappe.throw('مبلغ باید عدد صحیح ریال باشد؛ فروش نامنفی و برگشت نامثبت است')
                note=str(values.get('note') or '').strip()
                if len(note)>500:
                    frappe.throw('توضیح حداکثر ۵۰۰ حرف باشد')
                replacement.update(amount=float(value),note=note,customer_id=str(known.get('CustomerId')))
            records[identity]=replacement
        else:
            records.pop(identity,None)
        config.setdefault('facilitator_history',[]).append(dict(kind=kind,key=identity,previous=original,replacement=replacement,
            changed_by=frappe.session.user,changed_at=str(frappe.utils.now_datetime())))
    elif kind in ('repair_sales_seller','repair_sales_suggestions'):
        month, start, end, previous = bounds(values.get('month'))
        raw = read_latest(month)
        if not raw:
            frappe.throw('ابتدا گزارش ماه را دریافت کنید')
        snap = current_snapshot(raw,config,start,end,previous)
        invoices = {i['key']:i for i in snap['invoices'] if i.get('is_repair') and str(start)<=i['date']<=str(end)}
        keys = values.get('keys') if kind == 'repair_sales_suggestions' else [values.get('key')]
        if not isinstance(keys,list) or not keys or len(keys)>1000 or len(set(keys))!=len(keys):
            frappe.throw('فاکتورهای تعمیراتی معتبر انتخاب کنید')
        active = snap.get('crm_metadata',{}).get('seller_choices',{})
        aliases = snap.get('crm_metadata',{}).get('seller_aliases',{})
        records = config.setdefault('repair_sales_sellers',{})
        for key in keys:
            invoice = invoices.get(key)
            if not invoice:
                frappe.throw('فاکتور تعمیراتی در ماه انتخاب‌شده یافت نشد')
            proposal = invoice.get('repair_sales_proposal')
            if kind == 'repair_sales_suggestions':
                if not proposal or invoice.get('repair_sales_seller'):
                    frappe.throw('پیشنهاد تغییر کرده است؛ گزارش را دوباره باز کنید')
                seller, source = proposal['seller'], proposal['source']
            else:
                seller = str(values.get('seller') or '')
                source = 'انتخاب دستی برای همین فاکتور'
            seller = aliases.get(seller,seller)
            if seller and seller not in active:
                frappe.throw('یک کارشناس فروش فعال انتخاب کنید')
            original = records.get(key)
            replacement = dict(seller=seller,source=source,confirmed_by=frappe.session.user,
                               confirmed_at=str(frappe.utils.now_datetime())) if seller else None
            if replacement:
                records[key]=replacement
            else:
                records.pop(key,None)
            config.setdefault('repair_sales_seller_history',[]).append(dict(key=key,previous=original,replacement=replacement,
                changed_by=frappe.session.user,changed_at=str(frappe.utils.now_datetime())))
    elif kind == 'manual_deal':
        context = deal_candidates(values.get('month'), values.get('key'), values.get('days',30))
        invoice = context['invoice']
        deal = next((d for d in context['deals'] if d['id']==values.get('deal_id')), None)
        if not deal or values.get('reviewed') is not True:
            frappe.throw('معامله معتبر را انتخاب و بررسی آن را تأیید کنید')
        if invoice.get('quotation_status') in ('missing','unresolved') and values.get('reviewed_no_quotation') is not True:
            frappe.throw('نبود پیش‌فاکتور سپیدار باید جداگانه تأیید شود')
        key = invoice['key']
        original = config.setdefault('invoices',{}).get(key)
        replacement = dict(seller=deal['seller'],channel=deal['channel'],deal_ids=[deal['id']],
                           method='manual',confidence='manual_document',
                           reviewed_no_quotation=values.get('reviewed_no_quotation') is True,
                           confirmed_by=frappe.session.user,confirmed_at=str(frappe.utils.now_datetime()))
        config['invoices'][key] = replacement
        config.setdefault('assignment_history',[]).append(dict(key=key,previous=original,replacement=replacement,
            changed_by=frappe.session.user,changed_at=str(frappe.utils.now_datetime())))
        # This is an explicit document link, not a permanent person/company assignment.
    elif kind == 'customer_group_seller':
        month, _, _, _ = bounds(values.get('month'))
        group_id = str(values.get('group_id') or '')
        mappings = config.setdefault('customer_group_sellers', {})
        groups = customer_groups(read_latest(month))
        if group_id not in groups and group_id not in mappings:
            frappe.throw('گروه مشتری معتبر نیست؛ گزارش را دوباره دریافت کنید')
        directory = directory_cache()
        seller = str(values.get('seller') or '')
        seller = directory.get('seller_aliases', {}).get(seller, seller)
        if seller and seller not in directory.get('seller_choices', {}):
            frappe.throw('یک کارشناس فعال انتخاب کنید')
        original = mappings.get(group_id)
        replacement = None
        if seller:
            replacement = dict(seller=seller, group_title=groups.get(group_id) or (original or {}).get('group_title'),
                               changed_by=frappe.session.user, changed_at=str(frappe.utils.now_datetime()))
            mappings[group_id] = replacement
        else:
            mappings.pop(group_id, None)
        config.setdefault('customer_group_seller_history', []).append(dict(
            group_id=group_id, previous=original, replacement=replacement,
            changed_by=frappe.session.user, changed_at=str(frappe.utils.now_datetime())))
    elif kind == "target":
        month, start, _, _ = bounds(values.get("month"))
        seller, channel = str(values.get("seller") or "").strip(), values.get("channel")
        if not seller or len(seller) > 140 or channel not in CHANNELS:
            frappe.throw("کارشناس و کانال معتبر لازم است")
        target, limit = values.get("target"), values.get("discount_limit")
        target = float(num(target)) if target not in (None, "") else None
        limit = float(num(limit)) if limit not in (None, "") else None
        if (target is not None and target < 0) or (limit is not None and not 0 <= limit <= 100):
            frappe.throw("تارگت باید نامنفی و سقف تخفیف بین صفر و صد باشد")
        config["targets"] = [
            t
            for t in config.get("targets", [])
            if not (
                t["period_start"] == str(start)
                and t["seller"] == seller
                and t["channel"] == channel
            )
        ]
        config["targets"].append(
            dict(
                month=month,
                period_start=str(start),
                seller=seller,
                channel=channel,
                target=target,
                discount_limit=limit,
            )
        )
    elif kind == 'customer_exclusion':
        month, start, end, previous = bounds(values.get('month'))
        snapshot = current_snapshot(read_latest(month) or {}, config, start, end, previous)
        customer = str(values.get('customer_id') or '')
        exclude = values.get('excluded')
        if type(exclude) is not bool or not customer:
            frappe.throw('مشتری یا وضعیت خروج معتبر نیست')
        records = config.setdefault('excluded_customers', {})
        previous_record = records.get(customer)
        invoice = next((r for r in snapshot.get('invoices', []) if r['customer_id']==customer), None)
        if exclude and not invoice:
            frappe.throw('مشتری باید در گزارش موجود باشد')
        if not exclude and not previous_record:
            frappe.throw('مشتری در فهرست خارج از آمار نیست')
        replacement = None
        if exclude:
            from .matching import customer_name
            catalog = snapshot.get('crm_metadata', {}).get('customer_catalog') or []
            ids = {r['id'] for r in catalog if customer_name(r.get('name')) == customer_name(invoice['customer']) and customer_name(r.get('name'))}
            replacement = dict(customer_id=customer, customer_name=invoice['customer'], crm_ids=list(ids) if len(ids)==1 else [], changed_by=frappe.session.user, changed_at=str(frappe.utils.now_datetime()))
            records[customer] = replacement
        else:
            records.pop(customer)
        config.setdefault('customer_exclusion_history', []).append(dict(customer_id=customer, previous=previous_record, replacement=replacement, changed_by=frappe.session.user, changed_at=str(frappe.utils.now_datetime())))
    elif kind == 'document_type':
        month, start, end, previous = bounds(values.get('month'))
        snapshot = read_latest(month) or {}
        snapshot = current_snapshot(snapshot, config, start, end, previous)
        key = values.get('key')
        invoice = next((r for r in snapshot.get('invoices', []) if r['key']==key), None)
        category = values.get('type')
        description = str(values.get('description') or '').strip()
        if not invoice or category not in ('repair', 'auto') or len(description)>200:
            frappe.throw('فاکتور یا نوع سند معتبر نیست')
        records = config.setdefault('document_types', {})
        previous_type = records.get(key)
        replacement = dict(type=category, description=description, changed_by=frappe.session.user, changed_at=str(frappe.utils.now_datetime()))
        if category == 'auto':
            records.pop(key, None)
        else:
            records[key] = replacement
            customer = invoice.get('customer_id')
            reference = config.get('customer_references', {}).get(customer, {})
            if reference.get('source_invoice') == key:
                config['customer_references'].pop(customer)
                config.setdefault('customer_reference_history', []).append(dict(customer_id=customer, previous=reference, replacement=None, reason='source_invoice_marked_repair'))
        config.setdefault('document_type_history', []).append(dict(key=key, previous=previous_type, replacement=replacement))
    elif kind == "invoice":
        month, start, end, previous = bounds(values.get("month"))
        snap = read_latest(month) or {}
        if snap:
            snap = current_snapshot(snap, config, start, end, previous)
        key = values.get("key")
        invoice = next((r for r in snap.get("invoices", []) if r["key"] == key), None)
        if not invoice:
            frappe.throw("فاکتور باید در آخرین گزارش موجود باشد")
        if invoice.get('excluded'):
            frappe.throw('مشتری از آمار فروش خارج شده است؛ ابتدا او را به آمار بازگردانید')
        if invoice.get("is_repair"):
            frappe.throw("فاکتور خدمات پس از فروش از انتساب فروش جداست")
        quote_warning = invoice.get('quotation_status') in ('missing', 'unresolved')
        if quote_warning and values.get('reviewed_no_quotation') is not True:
            frappe.throw('انتساب این فاکتور نیازمند تأیید بررسی نبود پیش‌فاکتور است')
        seller, channel = str(values.get("seller") or "").strip(), values.get("channel")
        if not seller or len(seller) > 140 or channel not in CHANNELS:
            frappe.throw("کارشناس و کانال معتبر لازم است")
        previous_assignment = config.setdefault("invoices", {}).get(key)
        assignment = dict(
            seller=seller,
            channel=channel,
            method="manual",
            reviewed_no_quotation=quote_warning,
            confirmed_by=frappe.session.user,
            confirmed_at=str(frappe.utils.now_datetime()),
        )
        proposal = snap.get('suggestions', {}).get(key, {}) or previous_assignment or {}
        if proposal.get('confidence') == 'customer_relation':
            assignment.update({field: proposal[field] for field in (
                'confidence', 'related_customer_id', 'related_customer_name', 'related_person_id')})
        if previous_assignment and (
            previous_assignment.get("seller"), previous_assignment.get("channel")
        ) != (seller, channel):
            config.setdefault("assignment_history", []).append(
                dict(
                    key=key,
                    previous=previous_assignment,
                    replacement=assignment,
                    changed_by=frappe.session.user,
                    changed_at=str(frappe.utils.now_datetime()),
                )
            )
        config["invoices"][key] = assignment
        if not quote_warning:
            remember_customer_reference(config, invoice, assignment)
    elif kind in ("customer_rule", "customer_rule_delete"):
        month, _, _, _ = bounds(values.get("month"))
        snapshot = read_latest(month) or {}
        customer = str(values.get("customer_id") or "").strip()
        if not customer.isdigit() or not any(
            row.get("customer_id") == customer for row in snapshot.get("invoices", [])
        ) and not any(
            str(rule.get("customer_id")) == customer
            for rule in config.get("customer_rules", [])
        ):
            frappe.throw("مشتری باید در گزارش یا قواعد موجود باشد")
        date_value = str(values.get("from_date") or "").translate(
            str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
        )
        if not re.fullmatch(r"1[34]\d{2}-(0[1-9]|1[0-2])-([0-2]\d|3[01])", date_value):
            frappe.throw("تاریخ شروع را به شکل ۱۴۰۵-۰۸-۰۴ وارد کنید")
        try:
            year, m, d = map(int, date_value.split("-"))
            from_date = jdatetime.date(year, m, d).togregorian().isoformat()
        except ValueError:
            frappe.throw("تاریخ شروع معتبر نیست")
        rules = config.setdefault("customer_rules", [])
        existing = next(
            (
                rule
                for rule in rules
                if str(rule.get("customer_id")) == customer and rule.get("from_date") == from_date
            ),
            None,
        )
        rule_id = str(values.get("rule_id") or "")
        if rule_id:
            original = next((rule for rule in rules if rule.get("id") == rule_id), None)
            if not original:
                frappe.throw("قاعده تغییر کرده است؛ صفحه را دوباره دریافت کنید")
            if existing and existing is not original:
                frappe.throw("برای این مشتری و تاریخ قبلاً قاعده ثبت شده است")
            existing = original
        if kind == "customer_rule_delete":
            if not existing:
                frappe.throw("قاعده مشتری یافت نشد")
            rules.remove(existing)
            replacement = None
        else:
            seller, channel = str(values.get("seller") or "").strip(), values.get("channel")
            directory = directory_cache()
            known = {**directory.get("sellers", {}), **directory.get("seller_choices", {})}
            seller = directory.get("seller_aliases", {}).get(seller, seller)
            if seller not in known or channel not in CHANNELS:
                frappe.throw("کارشناس و کانال معتبر لازم است")
            customer_name = next(
                (
                    row.get("customer")
                    for row in snapshot.get("invoices", [])
                    if row.get("customer_id") == customer
                ),
                existing.get("customer_name") if existing else "",
            )
            replacement = dict(
                id=(existing or {}).get("id") or uuid4().hex,
                customer_id=customer,
                customer_name=customer_name,
                from_date=from_date,
                from_jalali=date_value,
                seller=seller,
                channel=channel,
                confirmed_by=frappe.session.user,
                confirmed_at=str(frappe.utils.now_datetime()),
            )
            if existing:
                rules.remove(existing)
            rules.append(replacement)
        config.setdefault("customer_rule_history", []).append(
            dict(
                customer_id=customer,
                from_date=from_date,
                previous=existing,
                replacement=replacement,
                changed_by=frappe.session.user,
                changed_at=str(frappe.utils.now_datetime()),
            )
        )
    elif kind == "suggestions":
        month, start, end, previous = bounds(values.get("month"))
        snapshot = read_latest(month)
        if not snapshot:
            frappe.throw("ابتدا گزارش این ماه را دریافت کنید")
        snapshot = current_snapshot(snapshot, config, start, end, previous)
        keys = values.get("keys", [])
        if not isinstance(keys, list) or not keys or len(keys) > 1000:
            frappe.throw("حداقل یک پیشنهاد انتخاب کنید")
        by_key = {r["key"]: r for r in snapshot.get("invoices", [])}
        customer_choices = {}
        for key in keys:
            proposal = snapshot.get("suggestions", {}).get(key)
            if not proposal:
                frappe.throw("پیشنهاد تغییر کرده است؛ دوباره گزارش را دریافت کنید")
            config.setdefault("invoices", {})[key] = {
                **proposal,
                "method": "suggestion",
                "confirmed_by": frappe.session.user,
                "confirmed_at": str(frappe.utils.now_datetime()),
            }
            invoice = by_key[key]
            customer = invoice.get("customer_id")
            if customer:
                customer_choices.setdefault(customer, {})[(proposal["seller"], proposal["channel"])] = (invoice, proposal)
        for customer, choices in customer_choices.items():
            if len(choices) == 1:
                invoice, proposal = next(iter(choices.values()))
                remember_customer_reference(config, invoice, proposal)
            else:
                reference_conflicts.append(customer)
    elif kind == "customer":
        month, start, end, previous = bounds(values.get("month"))
        snapshot = read_latest(month) or {}
        customer = str(values.get("customer_id") or "")
        seller, channel = str(values.get("seller") or ""), values.get("channel")
        if not customer or not seller or channel not in CHANNELS:
            frappe.throw("مشتری، کارشناس و کانال را تعیین کنید")
        matched = [
            r
            for r in snapshot.get("invoices", [])
            if r.get("customer_id") == customer
            and not config.get("invoices", {}).get(r["key"])
            and not r.get("mapped")
        ]
        if not matched:
            frappe.throw("فاکتور بدون انتسابی برای این مشتری در دوره موجود نیست")
        for row in matched:
            config.setdefault("invoices", {})[row["key"]] = dict(
                seller=seller,
                channel=channel,
                method="customer-bulk",
                confirmed_by=frappe.session.user,
            )
    elif kind == "product":
        month, _, _, _ = bounds(values.get("month"))
        snap = read_latest(month) or {}
        code, group = str(values.get("code") or ""), values.get("group")
        if code not in snap.get("products", []) or group not in {*GROUPS, "exclude"}:
            frappe.throw("کد کالا یا گروه معتبر نیست")
        config.setdefault("products", {})[code] = group
    else:
        frappe.throw("نوع تنظیم نامعتبر")
    save_config(config)
    return {"saved": True, "reference_conflicts": reference_conflicts}


@frappe.whitelist(methods=["POST"])
def configure_api(api_key):
    require_access()
    if not admin(frappe.session.user):
        frappe.throw("ثبت کلید فقط برای مدیر سامانه مجاز است", frappe.PermissionError)
    api_key = str(api_key or "").strip()
    if not 10 <= len(api_key) <= 512 or any(c.isspace() for c in api_key):
        frappe.throw("کلید API معتبر وارد کنید")
    doc = frappe.get_single(DT)
    doc.didar_api_key = api_key
    doc.save(ignore_permissions=True)
    return {"saved": True}


def connection_status():
    """Internal diagnostic; returns no key, URL, contacts or financial records."""
    from .didar import Client, DidarError

    key = frappe.get_single(DT).get_password("didar_api_key", raise_exception=False)
    if not key:
        return {"configured": False, "connected": False}
    try:
        pipelines = Client(key).request("pipelines")
        return {
            "configured": True,
            "connected": isinstance(pipelines, list),
            "pipeline_count": len(pipelines) if isinstance(pipelines, list) else None,
        }
    except DidarError as exc:
        return {"configured": True, "connected": False, "error": str(exc)}


def source_counts():
    """Internal diagnostic limited to counts and field names, without business values."""
    from .didar import Client

    key = frappe.get_single(DT).get_password("didar_api_key", raise_exception=False)
    client = Client(key)
    deals = client.request(
        "deals", {"Criteria": {"IsDeleted": False, "Sort": 0}, "From": 0, "Limit": 1}
    )
    activities = client.request(
        "activities",
        {
            "IsDone": True,
            "IsDeleted": False,
            "FromDate": "1800-01-01T00:00:00Z",
            "ToDate": "9999-01-01T00:00:00Z",
            "SortType": 1,
            "From": 0,
            "Limit": 1,
        },
    )
    return {
        "deal_count": deals.get("TotalCount"),
        "activity_count": activities.get("Total"),
        "deal_fields": sorted((deals.get("List") or [{}])[0]),
        "activity_fields": sorted((activities.get("List") or [{}])[0]),
    }


def auto_refresh():
    """Hourly current month and previous month; accounting sources remain read-only."""
    _, start, _, _ = bounds()
    previous = jdatetime.date.fromgregorian(date=start - timedelta(days=1))
    for month in (bounds()[0], f"{previous.year:04}-{previous.month:02}"):
        frappe.enqueue(
            "saeenaria_portal.sales_reports.service.build",
            queue="long",
            timeout=900,
            month=month,
            job_id="sales-report-" + month,
            deduplicate=True,
        )
