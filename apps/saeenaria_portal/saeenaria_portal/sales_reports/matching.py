"""Conservative document evidence matching, independent of customer ownership defaults."""

from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
import unicodedata


def customer_name(value):
    text = unicodedata.normalize('NFKC', str(value or ''))
    text = text.translate(dict.fromkeys(map(ord, '\u061c\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069\ufeff')))
    text = ' '.join(text.translate(str.maketrans('يك', 'یک')).split()).casefold()
    return text[5:] if text.startswith('شرکت ') and len(text.split()) >= 3 else text


def invoice_customer_names(invoices, deals, catalog, assignments, suggestions):
    """Resolve display names without changing assignment or customer identity."""
    by_id = {r['id']: r.get('name') for r in catalog if r.get('id') and r.get('name')}
    by_deal = {d['source_id']: d for d in deals}
    compact = lambda value: ''.join(customer_name(value).replace('\u200c', '').split())
    names = defaultdict(set)
    for identity, name in by_id.items():
        names[compact(name)].add(identity)
    for invoice in invoices:
        evidence = suggestions.get(invoice['key']) or assignments.get(invoice['key']) or {}
        identities = set()
        for deal_id in evidence.get('deal_ids', []):
            deal = by_deal.get(deal_id, {})
            identities.update(deal.get('customer_ids', []))
            for owner in deal.get('customer_owners', []):
                if owner.get('name') and owner.get('customer_id'):
                    by_id.setdefault(owner['customer_id'], owner['name'])
        if evidence.get('related_customer_id'):
            identities = {evidence['related_customer_id']}
        if not identities:
            identities = names.get(compact(invoice.get('customer')), set())
        resolved = by_id.get(next(iter(identities))) if len(identities) == 1 else None
        invoice['didar_customer_name'] = resolved or evidence.get('related_customer_name') or ''


def nearby(invoice_date, deal):
    try:
        target = date.fromisoformat(str(invoice_date)[:10])
        return any(abs((target - date.fromisoformat(str(deal.get(k))[:10])).days) <= 45
                   for k in ('won_at', 'registered_at') if deal.get(k))
    except ValueError:
        return False


def identity_matches(invoice, deal):
    creator = invoice.get('quotation_creator_seller')
    return (bool(creator and creator == deal.get('seller')) or
            customer_name(invoice.get('customer')) in
            {customer_name(n) for n in deal.get('customer_names', []) if n})


def signature(items, crm=False):
    fields = ('ProductCode', 'Quantity', 'UnitPrice', 'Price', 'Discount', 'TaxPrice') if crm else (
        'ItemCode', 'Quantity', 'Fee', 'GrossPrice', 'Discount', 'Tax')
    result = []
    for row in items:
        if any(row.get(k) is None for k in fields):
            return None
        code = str(row[fields[0]]).strip().casefold()
        if not code:
            return None
        try:
            values = tuple(Decimal(str(row[k])) for k in fields[1:])
            if not all(v.is_finite() for v in values):
                return None
        except (InvalidOperation, ValueError):
            return None
        result.append((code, *values))
    return Counter(result) if result else None


def related_customer_proposal(invoice, deals, pipelines, sellers=None):
    """Review-only ownership proposal through an explicit deal contact/primary link."""
    from .channels import deal_channel
    from .calculations import DOCUMENT_CHANNELS
    sellers = sellers or {}
    name = customer_name(invoice.get('customer'))
    links = set()
    for deal in deals:
        if not nearby(invoice.get('date'), deal) or deal.get('state') == 2:
            continue
        primary_ids = deal.get('customer_ids', [])
        if len(primary_ids) != 1:
            continue
        primary = primary_ids[0]
        for contact in deal.get('customer_owners', []):
            if contact.get('customer_id') != primary and customer_name(contact.get('name')) == name:
                links.add((contact.get('customer_id'), primary))
    if len(links) != 1:
        return None
    person_id, primary_id = next(iter(links))
    if not person_id:
        return None
    candidates = []
    ownership = set()
    for deal in deals:
        if primary_id not in deal.get('customer_ids', []):
            continue
        for contact in deal.get('customer_owners', []):
            if contact.get('customer_id') == primary_id and contact.get('active') and contact.get('seller'):
                ownership.add((contact['seller'], contact.get('name') or ''))
        if deal.get('state') == 1 and nearby(invoice.get('date'), deal):
            candidates.append(deal)
    channels = {deal_channel(d, pipelines) for d in candidates}
    if len(ownership) != 1 or len(channels) != 1 or not channels <= {'consumer', 'reseller'}:
        return None
    seller, primary_name = next(iter(ownership))
    channel = next(iter(channels))
    if not primary_name:
        return None
    reason = (
        f'ارتباط شخص «{invoice.get("customer")}» با مشتری اصلی «{primary_name}» در دیدار؛ '
        f'مسئول مشتری اصلی: {sellers.get(seller) or "نامشخص"}؛ '
        f'کانال فروش: {DOCUMENT_CHANNELS[channel]}؛ '
        'پیشنهاد بر اساس ارتباط مشتری و مسئول فعلی؛ تطبیق کامل سند تأیید نشده است'
    )
    creator = invoice.get('quotation_creator_seller')
    if creator and creator != seller:
        reason += f'؛ ثبت‌کنندهٔ پیش‌فاکتور سپیدار: {sellers.get(creator) or "نامشخص"} (متفاوت با مسئول مشتری)'
    return dict(seller=seller, channel=channel, deal_ids=[], confidence='customer_relation',
                related_customer_id=primary_id, related_customer_name=primary_name,
                related_person_id=person_id, reason=reason + '؛ فقط برای این فاکتور، بدون ایجاد مرجع دائمی مشتری؛ نیازمند تأیید')


def minor_amount_difference(left, right):
    """At most 0.1 percent and 10,000 rials; zero amounts must stay zero."""
    return abs(left - right) <= min(abs(left) * Decimal('0.001'), Decimal('10000'))


def items_with_minor_rounding(financial, crm):
    left, right = signature(financial), signature(crm, crm=True)
    if not left or not right:
        return False
    # Preserve repeated lines; compare each code/quantity and all monetary components.
    a, b = sorted(left.elements()), sorted(right.elements())
    return len(a) == len(b) and all(
        x[:2] == y[:2] and all(minor_amount_difference(v, w) for v, w in zip(x[2:], y[2:]))
        for x, y in zip(a, b))


def document_matches(invoices, deals, sales, pipelines, sellers=None, group_sellers=None):
    from .channels import deal_channel
    from .calculations import DOCUMENT_CHANNELS
    sellers = sellers or {}
    group_sellers = group_sellers or {}
    rows = defaultdict(list)
    for row in sales:
        if row.get('DocumentType') == 'Sale':
            rows['Sale:' + str(row['DocumentId'])].append(row)
    matches, blocked, notes = {}, set(), {}
    for invoice in invoices:
        if invoice.get('excluded') or invoice.get('mapped') or invoice.get('is_repair') or invoice.get('quotation_status') in ('missing', 'unresolved'):
            continue
        key = invoice['key']
        wanted = signature(rows.get(key, []))
        if not wanted:
            continue
        candidates = []
        precision = {}
        for deal in deals:
            if deal.get('state') == 2 or not nearby(invoice['date'], deal) or not identity_matches(invoice, deal):
                continue
            exact_items = signature(deal.get('items', []), crm=True) == wanted
            if not exact_items and not items_with_minor_rounding(rows.get(key, []), deal.get('items', [])):
                continue
            try:
                total = Decimal(str(deal.get('document_total')))
                expected = Decimal(str(invoice['total_amount']))
                if not total.is_finite() or not minor_amount_difference(expected, total):
                    continue
            except (InvalidOperation, ValueError):
                continue
            candidates.append(deal)
            precision[deal['source_id']] = (exact_items and abs(total - expected) <= Decimal('0.01'), abs(total - expected))
        if not candidates:
            continue
        blocked.add(key)  # Strong conflicting evidence must not fall through to name-only suggestions.
        if len(candidates) != 1:
            notes[key] = 'چند معامله با اقلام و مبلغ یکسان؛ نیازمند بررسی سند'
            continue
        deal = candidates[0]
        exact, difference = precision[deal['source_id']]
        confidence = 'document' if exact else 'document_minor_difference'
        amount_note = '' if exact else f'؛ اقلام و تعداد منطبق، اختلاف جزئی مبلغ نهایی: {difference:,.0f} ریال؛ سقف اختلاف ۰٫۱٪ و حداکثر ۱۰٬۰۰۰ ریال'
        channel = deal_channel(deal, pipelines)
        creator = invoice.get('quotation_creator_seller')
        if channel not in ('consumer', 'reseller'):
            notes[key] = 'سند مشابه در کاریز خدمات یا خارج از فروش؛ نیازمند بررسی کانال'
            continue
        if not deal.get('seller') or (creator and creator != deal['seller']):
            responsible = sellers.get(deal.get('seller')) or deal.get('seller_name') or 'نامشخص'
            created_by = sellers.get(creator) or 'نامشخص'
            notes[key] = (
                ('اقلام و مبلغ منطبق است؛ ' if exact else 'اقلام منطبق است و مبلغ اختلاف جزئی دارد؛ ') + 'انتساب نیازمند بررسی کارشناس است. '
                f'کارشناس مسئول معامله در دیدار: {responsible}؛ '
                f'ثبت‌کنندهٔ پیش‌فاکتور در سپیدار: {created_by}؛ '
                f'کانال فروش: {DOCUMENT_CHANNELS.get(channel, "نامشخص")}؛ '
                f'کاریز دیدار: {deal.get("pipeline") or "نامشخص"}'
            )
            groups = {str(r['CustomerGroupId']): r.get('CustomerGroupTitle') or 'بدون نام'
                      for r in rows[key] if r.get('CustomerGroupId') is not None}
            if len(groups) == 1:
                group_id, group_title = next(iter(groups.items()))
                mapped_seller = group_sellers.get(group_id, {}).get('seller')
                if mapped_seller and mapped_seller in sellers:
                    matches[key] = dict(
                        seller=mapped_seller, channel=channel, deal_ids=[deal['source_id']],
                        confidence=confidence,
                        reason=notes[key] + amount_note + f'؛ مبنای پیشنهاد: گروه مشتری سپیدار «{group_title}» ← {sellers[mapped_seller]}؛ نیازمند تأیید',
                        customer_group_id=group_id,
                    )
                else:
                    notes[key] += f'؛ گروه مشتری سپیدار: {group_title} (تطبیق کارشناس ثبت نشده است)'
            if key not in matches:
                related = related_customer_proposal(invoice, deals, pipelines, sellers)
                if related:
                    related.update(deal_ids=[deal['source_id']], document_confidence=confidence)
                    related['reason'] += amount_note
                    matches[key] = related
            notes[key] += amount_note
            continue
        matches[key] = dict(seller=deal['seller'], channel=channel,
                            deal_ids=[deal['source_id']], confidence=confidence,
                            reason=('تطبیق کامل اقلام، تعداد، قیمت، تخفیف، مالیات و جمع سند' if exact else 'تطبیق اقلام با اختلاف جزئی مبالغ') + amount_note + '؛ مشتری یا کارشناس مشترک و تاریخ نزدیک؛ نیازمند تأیید')
    for invoice in invoices:
        proposal = matches.get(invoice['key'])
        if proposal and proposal.get('confidence') != 'customer_relation':
            related = related_customer_proposal(invoice, deals, pipelines, sellers)
            if related:
                proposal.update({k:related[k] for k in ('related_customer_id','related_customer_name','related_person_id')})
                proposal['document_confidence'] = proposal['confidence']
                proposal['confidence'] = 'customer_relation'
                proposal['reason'] += f'؛ مشتری مرتبط در دیدار: {related["related_customer_name"]}؛ فقط برای این فاکتور، بدون مرجع دائمی مشتری'
    uses = defaultdict(list)
    # Already-confirmed document matches also reserve their specific CRM document.
    for invoice in invoices:
        if invoice.get('mapped') and invoice.get('matched_deal_id'):
            uses[invoice['matched_deal_id']].append(invoice['key'])
    for key, proposal in matches.items():
        uses[proposal['deal_ids'][0]].append(key)
    for keys in uses.values():
        if len(keys) > 1:
            for key in keys:
                matches.pop(key, None)
                notes[key] = 'یک معامله برای چند فاکتور مشابه است؛ نیازمند بررسی سند'
    return matches, blocked, notes
