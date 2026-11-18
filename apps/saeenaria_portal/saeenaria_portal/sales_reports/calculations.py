"""Explicit attribution only: a won deal is never counted as an invoice."""

from decimal import Decimal
from .channels import deal_channel, tagged_customer_names
from .matching import customer_name

CHANNELS = {"consumer": "فروش به مصرف‌کننده", "reseller": "فروش به واسطه"}
DOCUMENT_CHANNELS = {**CHANNELS, "after_sales": "خدمات پس از فروش"}
GROUPS = {
    "drill": "دریل",
    "bevel": "پخ‌زن",
    "solid": "مته توپر",
    "annular": "گردبر",
    "insert": "اینسرت",
    "parts": "قطعات یدکی",
    "other": "سایر کالاها",
}
PIPELINES = {"فروش مستقیم": "consumer", "همکار و ابزار فروش": "reseller", "خدمات پس از فروش": "after_sales"}
POLICY = "sales-monthly-v1"


def num(value):
    result = Decimal(str(value or 0))
    if not result.is_finite():
        raise ValueError("عدد نامعتبر")
    return result


def pct(a, b):
    return float(num(a) * 100 / num(b)) if num(b) > 0 else None


def day(value):
    return str(value or "")[:10]


def document_key(row):
    return f"{row['DocumentType']}:{row['DocumentId']}"


def customer_rule_for(row, rules):
    customer = str(row.get("CustomerId") or "")
    date = day(row.get("DocumentDate"))
    eligible = [
        rule
        for rule in rules
        if str(rule.get("customer_id")) == customer and rule.get("from_date", "") <= date
    ]
    return max(eligible, key=lambda rule: rule["from_date"]) if eligible else {}


def assignment_for(row, config):
    explicit = config.get("invoices", {}).get(document_key(row), {})
    if row.get('QuotationStatus') in ('missing', 'unresolved'):
        return explicit  # Never propagate customer defaults onto a document needing review.
    method = explicit.get("method") or ("suggestion" if explicit.get("deal_ids") else "manual")
    if explicit and method == "manual":
        return explicit
    rule = customer_rule_for(row, config.get("customer_rules", []))
    reference = config.get("customer_references", {}).get(str(row.get("CustomerId") or ""), {})
    return rule or explicit or reference


def calculate(sales, deals, activities, config, start, end, previous_start, first_purchases):
    """All dates are source-local dates; source freshness is supplied separately."""
    start, end, previous_start = map(str, (start, end, previous_start))
    groups = config.get("products", {})
    group_labels = config.get("group_labels", GROUPS)
    buckets = {}
    evidence = {}
    excluded = config.get('excluded_customers', {})
    crm_excluded = {identity for record in excluded.values() for identity in record.get('crm_ids', [])}
    catalog = config.get('customer_catalog') or []
    for record in excluded.values():
        identities = {r['id'] for r in catalog if customer_name(r.get('name')) == customer_name(record.get('customer_name')) and customer_name(r.get('name'))}
        if len(identities) == 1:
            crm_excluded.update(identities)
    tagged_names = tagged_customer_names(config.get('customer_catalog') or [])
    repair_documents = {
        document_key(row): "وجود KH در نام ردیف فاکتور"
        for row in sales if "kh" in str(row.get("ItemTitle") or "").casefold()
    }
    for key, record in config.get('document_types', {}).items():
        if record.get('type') == 'repair':
            repair_documents[key] = 'تعمیرات ثبت‌شده دستی' + (': ' + record['description'] if record.get('description') else '')
    pipelines = {**PIPELINES, **config.get("pipelines", {})}
    deal_channels = {str(deal["source_id"]): deal_channel(deal, pipelines) for deal in deals}
    for key, assignment in config.get("invoices", {}).items():
        linked = assignment.get("deal_ids") or []
        if assignment.get("channel") == "after_sales" or (
            linked and all(deal_channels.get(str(identity)) == "after_sales" for identity in linked)
        ):
            repair_documents.setdefault(
                key,
                "کانال خدمات پس از فروش ثبت‌شده برای فاکتور"
                if assignment.get("channel") == "after_sales"
                else "کاریز خدمات پس از فروش معاملات مرتبط",
            )
    missing = set()
    unknown_groups = set()
    seen = set()

    def bucket(seller, channel):
        key = (seller, channel)
        if key not in buckets:
            buckets[key] = dict(
                seller=seller,
                channel=channel,
                actual=Decimal(0),
                gross=Decimal(0),
                discount=Decimal(0),
                sale_value=Decimal(0),
                invoices=set(),
                customers=set(),
                previous=set(),
                new=set(),
                groups={g: Decimal(0) for g in group_labels},
                unclassified=Decimal(0),
                won=set(),
                lost=set(),
                cohort=set(),
                followed=set(),
            )
        return buckets[key]

    for row in sales:
        identity = (row["DocumentType"], str(row["DocumentItemId"]))
        if identity in seen:
            raise ValueError("ردیف فاکتور تکراری در منبع")
        seen.add(identity)
        date = day(row["DocumentDate"])
        if not previous_start <= date <= end:
            continue
        key = document_key(row)
        assignment = assignment_for(row, config)
        seller, channel = assignment.get("seller"), assignment.get("channel")
        customer_name_value = ' '.join(dict.fromkeys(str(row.get(k) or '').strip() for k in ('CustomerName', 'CustomerLastName'))).strip()
        customer_reseller = customer_name(customer_name_value) in tagged_names
        linked = assignment.get('deal_ids') or []
        linked_reseller = bool(linked) and all(deal_channels.get(str(i)) == 'reseller' for i in linked)
        if channel != 'after_sales' and (customer_reseller or linked_reseller):
            channel = 'reseller'
        is_repair = key in repair_documents
        is_excluded = str(row.get('CustomerId') or '') in excluded
        if is_repair:
            # Customer sales rules must never turn a service invoice into a sale.
            explicit = config.get("invoices", {}).get(key, {})
            seller = explicit.get("seller") if explicit.get("channel") == "after_sales" else None
            channel = "after_sales"
        valid = bool(seller and channel in DOCUMENT_CHANNELS)
        group = groups.get(str(row.get("ItemCode")), "")
        if not is_repair and not is_excluded and date >= start and group not in {*group_labels, "exclude"}:
            unknown_groups.add(str(row.get("ItemCode")))
        if key not in evidence:
            evidence[key] = dict(
                key=key,
                number=str(row["DocumentNumber"]),
                date=date,
                customer_id=str(row.get("CustomerId") or ""),
                customer=" ".join(
                    dict.fromkeys(
                        str(row.get(k) or "").strip()
                        for k in ("CustomerName", "CustomerLastName")
                        if str(row.get(k) or "").strip()
                    )
                ),
                seller=seller,
                channel=channel,
                customer_reseller=customer_reseller,
                channel_reason='تگ همکار/ابزار فروش مشتری در دیدار' if customer_reseller and not is_repair else '',
                mapped=valid,
                is_repair=is_repair,
                excluded=is_excluded,
                manual_repair=config.get('document_types', {}).get(key, {}).get('type') == 'repair',
                repair_description=config.get('document_types', {}).get(key, {}).get('description', ''),
                quotation_status=row.get('QuotationStatus', 'unknown') if row['DocumentType']=='Sale' else 'not_applicable',
                quotation_number=str(row['QuotationNumber']) if row.get('QuotationNumber') is not None else None,
                repair_reason=repair_documents.get(key),
                previous_sales_assignment=(
                    config.get("invoices", {}).get(key)
                    if is_repair and config.get("invoices", {}).get(key, {}).get("channel") in CHANNELS
                    else None
                ),
                sale_type_title=row.get("SaleTypeTitle"),
                quotation_creator_seller=row.get("QuotationCreatorSeller"),
                related_customer_name=assignment.get('related_customer_name'),
                matched_deal_id=(assignment.get('deal_ids') or [None])[0]
                if assignment.get('confidence') in ('document', 'document_minor_difference', 'manual_document') or assignment.get('document_confidence') else None,
                amount=Decimal(0),
                gross=Decimal(0),
                discount=Decimal(0),
                tax=Decimal(0),
                total_amount=Decimal(0),
            )
        amount = num(row.get("GrossPrice")) - num(row.get("Discount"))
        evidence[key]["amount"] += amount
        evidence[key]["gross"] += num(row.get("GrossPrice"))
        evidence[key]["discount"] += num(row.get("Discount"))
        tax = num(row.get("Tax")) + num(row.get("Duty"))
        evidence[key]["tax"] += tax
        evidence[key]["total_amount"] += (
            num(row["NetPrice"]) if row.get("NetPrice") is not None
            else amount + tax + num(row.get("Addition"))
        )
        if is_repair or is_excluded:
            continue
        if not valid:
            if date >= start:
                missing.add(key)
            continue
        b = bucket(seller, channel)
        customer = str(row.get("CustomerId") or "")
        is_sale = row["DocumentType"] == "Sale"
        if date < start:
            if is_sale and customer:
                b["previous"].add(customer)
            continue
        b["actual"] += amount
        if is_sale:
            b["invoices"].add(key)
            b["sale_value"] += amount
            b["gross"] += num(row.get("GrossPrice"))
            b["discount"] += num(row.get("Discount"))
            if customer:
                b["customers"].add(customer)
                if start <= day(first_purchases.get(customer)) <= end:
                    b["new"].add(customer)
        if group == "exclude":
            continue
        if group not in group_labels:
            b["unclassified"] += num(row.get("Quantity"))
        else:
            b["groups"][group] += num(row.get("Quantity"))

    activity_deals = {
        str(a["source_id"])
        for a in activities
        if start <= day(a.get("done_at")) <= end and int(a.get("state", 0)) == 1
    }
    deal_seen = set()
    for row in deals:
        key = str(row["source_id"])
        if key in deal_seen:
            raise ValueError("معامله تکراری در منبع")
        deal_seen.add(key)
        if set(row.get('customer_ids') or []) & crm_excluded:
            continue
        if not row.get('customer_ids'):
            identities = {r['id'] for r in catalog if customer_name(r.get('name')) in {customer_name(n) for n in row.get('customer_names', [])}}
            if identities & crm_excluded:
                continue
        channel = deal_channel(row, pipelines)
        if channel not in CHANNELS or not row.get("seller"):
            continue
        if not any(
            start <= day(row.get(field)) <= end for field in ("registered_at", "won_at", "lost_at")
        ):
            continue
        b = bucket(row["seller"], channel)
        if int(row["state"]) == 1 and start <= day(row.get("won_at")) <= end:
            b["won"].add(key)
        if int(row["state"]) == 2 and start <= day(row.get("lost_at")) <= end:
            b["lost"].add(key)
        if start <= day(row.get("registered_at")) <= end:
            b["cohort"].add(key)
            if key in activity_deals:
                b["followed"].add(key)

    for target in config.get("targets", []):
        if target.get("period_start") == start:
            bucket(target["seller"], target["channel"])
    result = []
    for b in buckets.values():
        target = next(
            (
                t
                for t in config.get("targets", [])
                if t.get("period_start") == start
                and t["seller"] == b["seller"]
                and t["channel"] == b["channel"]
            ),
            {},
        )
        limit = target.get("discount_limit")
        discount = pct(b["discount"], b["gross"])
        result.append(
            dict(
                seller=b["seller"],
                channel=b["channel"],
                target=target.get("target"),
                actual=float(b["actual"]),
                achievement=pct(b["actual"], target.get("target")),
                invoice_count=len(b["invoices"]),
                average_invoice=float(b["sale_value"] / len(b["invoices"]))
                if b["invoices"]
                else None,
                new_customers=len(b["new"]),
                conversion=pct(len(b["won"]), len(b["won"] | b["lost"])),
                followup=pct(len(b["followed"]), len(b["cohort"])),
                retention=pct(len(b["customers"] & b["previous"]), len(b["previous"])),
                discount=discount,
                discount_limit=limit,
                discount_deviation=discount - float(limit)
                if discount is not None and limit is not None
                else None,
                groups={k: float(v) for k, v in b["groups"].items()},
                total_quantity=float(sum(b["groups"].values()) + b["unclassified"]),
                unclassified_quantity=float(b["unclassified"]),
                evidence=dict(
                    won=len(b["won"]),
                    lost=len(b["lost"]),
                    followed=len(b["followed"]),
                    cohort=len(b["cohort"]),
                    retained=len(b["customers"] & b["previous"]),
                    previous=len(b["previous"]),
                ),
                financial_complete=not missing,
            )
        )
    return dict(
        rows=sorted(result, key=lambda r: (r["channel"], r["seller"])),
        invoices=[{**v, **{k: float(v[k]) for k in ("amount", "gross", "discount", "tax", "total_amount")}} for v in evidence.values()],
        unmapped_invoices=len(missing),
        unclassified_products=sorted(unknown_groups),
        group_labels=group_labels,
    )


def apply_targets(rows, targets, aliases, start, names, group_labels):
    """Show current portal targets immediately, independently of slow source refreshes."""
    result = {(aliases.get(r["seller"], r["seller"]), r["channel"]): dict(r) for r in rows}
    for (seller, _), row in result.items():
        row["seller_name"] = (
            names.get(seller)
            or names.get(row["seller"])
            or row.get("seller_name")
            or "کارشناس بدون نام در دیدار"
        )
        row["seller"] = seller
    for target in targets:
        if target.get("period_start") != str(start):
            continue
        seller = aliases.get(target["seller"], target["seller"])
        key = (seller, target["channel"])
        row = result.setdefault(
            key,
            dict(
                seller=seller,
                seller_name=names.get(seller, seller),
                channel=target["channel"],
                actual=None,
                invoice_count=None,
                new_customers=None,
                groups={g: None for g in group_labels},
                financial_complete=False,
                total_quantity=None,
                unclassified_quantity=None,
            ),
        )
        row.update(
            target=target.get("target"),
            discount_limit=target.get("discount_limit"),
            achievement=pct(row.get("actual"), target.get("target"))
            if row.get("actual") is not None
            else None,
        )
        row["discount_deviation"] = (
            (row["discount"] - float(target["discount_limit"]))
            if row.get("discount") is not None and target.get("discount_limit") is not None
            else None
        )
    return list(result.values())


def attribution_suggestions(invoices, deals, pipelines=PIPELINES, sales=None, sellers=None, group_sellers=None):
    """Exact-name suggestions require review; never silently attribute accounting sales."""
    import unicodedata

    def normalized(value):
        return " ".join(
            unicodedata.normalize("NFKC", str(value or ""))
            .translate(dict.fromkeys(map(ord, "\u061c\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069\ufeff")))
            .translate(str.maketrans("يك", "یک"))
            .split()
        ).casefold()

    def company_name(value):
        value = normalized(value)
        if value.startswith("شرکت ") and len(value.split()) >= 3:
            return value[len("شرکت "):]
        return value

    candidates = {}
    company_candidates = {}
    for deal in deals:
        channel = deal_channel(deal, pipelines)
        if int(deal.get("state", 0)) != 1 or channel not in CHANNELS or not deal.get("seller"):
            continue
        for name in deal.get("customer_names", []):
            key = normalized(name)
            if key:
                candidates.setdefault(key, {}).setdefault((deal["seller"], channel), []).append(
                    deal["source_id"]
                )
                company_candidates.setdefault(company_name(name), {}).setdefault(
                    (deal["seller"], channel), []
                ).append(deal["source_id"])
    contact_candidates = {}
    for deal in deals:
        channel = deal_channel(deal, pipelines)
        if channel not in CHANNELS:
            continue
        for contact in deal.get("customer_owners", []):
            name = normalized(contact.get("name"))
            if name and contact.get("active") and contact.get("customer_id"):
                contact_candidates.setdefault(name, set()).add(
                    (contact["customer_id"], contact["seller"], channel)
                )
    from .matching import document_matches, related_customer_proposal
    suggestions, blocked, notes = document_matches(invoices, deals, sales or [], pipelines, sellers, group_sellers)
    for invoice in invoices:
        invoice['match_note'] = notes.get(invoice['key'], '')
        if invoice.get('excluded'):
            suggestions.pop(invoice['key'], None)
            continue
        if invoice.get('quotation_status') in ('missing', 'unresolved'):
            suggestions.pop(invoice['key'], None)
            invoice['match_note'] = 'هشدار: پیش‌فاکتور سپیدار ندارد یا ارتباط آن قابل تأیید نیست؛ بررسی دستی لازم است'
            continue
        if invoice['key'] in blocked:
            continue
        if invoice.get("mapped") or invoice.get("is_repair"):
            continue
        related = related_customer_proposal(invoice, deals, pipelines, sellers)
        if related:
            suggestions[invoice['key']] = related
            continue
        matches = candidates.get(normalized(invoice.get("customer")), {})
        creator = invoice.get("quotation_creator_seller")
        company_prefix_match = False
        if not matches and creator:
            # Ignore only a leading legal label, and require independent salesperson evidence.
            matches = company_candidates.get(company_name(invoice.get("customer")), {})
            company_prefix_match = bool(matches)
        if creator:
            matches = {key: value for key, value in matches.items() if key[0] == creator}
        if len(matches) == 1:
            (seller, channel), evidence = next(iter(matches.items()))
            suggestions[invoice["key"]] = dict(
                seller=seller,
                channel=channel,
                deal_ids=evidence,
                reason=(
                    "نام مشتری با یکسان‌سازی پیشوند شرکت، ایمیل ثبت‌کننده پیش‌فاکتور و کانال یکتا؛ نیازمند تأیید"
                    if company_prefix_match
                    else
                    "نام دقیق مشتری، ایمیل ثبت‌کننده پیش‌فاکتور و کانال یکتا؛ نیازمند تأیید"
                    if creator
                    else "نام دقیق مشتری و مسئول/کانال یکتا در معاملات موفق؛ نیازمند تأیید"
                ),
            )
        elif not matches:
            contacts = contact_candidates.get(normalized(invoice.get("customer")), set())
            # Same-name contacts or multiple sales pipelines must be reviewed manually.
            if len(contacts) == 1:
                contact_id, seller, channel = next(iter(contacts))
                if creator and seller != creator:
                    continue
                suggestions[invoice["key"]] = dict(
                    seller=seller, channel=channel, deal_ids=[],
                    customer_owner_id=contact_id,
                    reason="نام دقیق مشتری، مسئول فعلی مشتری در دیدار و کانال یکتا؛ نیازمند تأیید",
                )
    for invoice in invoices:
        proposal = suggestions.get(invoice['key'])
        if proposal and invoice.get('customer_reseller'):
            proposal['channel'] = 'reseller'
            proposal['reason'] += '؛ کانال همکار بر اساس تگ مشتری'
    return suggestions
