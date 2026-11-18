"""Sales contact for a repair invoice; independent of financial attribution."""
from collections import defaultdict
from .matching import customer_name


def annotate(invoices, sales, deals, config, metadata):
    aliases = metadata.get('seller_aliases', {})
    active = metadata.get('seller_choices', {})
    groups = defaultdict(dict)
    for row in sales:
        if row.get('CustomerGroupId') is not None:
            groups[str(row['DocumentType'])+':'+str(row['DocumentId'])][str(row['CustomerGroupId'])] = row.get('CustomerGroupTitle') or ''
    identities = defaultdict(set)
    owners = defaultdict(set)
    for contact in metadata.get('customer_catalog', []):
        if contact.get('id') and contact.get('name'):
            identities[customer_name(contact['name'])].add(contact['id'])
    for deal in deals:
        for contact in deal.get('customer_owners', []):
            if not contact.get('customer_id') or not contact.get('name'):
                continue
            identity = contact['customer_id']
            identities[customer_name(contact['name'])].add(identity)
            seller = aliases.get(contact.get('seller'),contact.get('seller'))
            if contact.get('active') and seller in active:
                owners[identity].add(seller)
    saved = config.get('repair_sales_sellers', {})
    for invoice in invoices:
        if not invoice.get('is_repair'):
            continue
        record = saved.get(invoice['key'], {})
        invoice['repair_sales_seller'] = aliases.get(record.get('seller'),record.get('seller'))
        invoice['repair_sales_source'] = record.get('source', '')
        invoice['repair_sales_proposal'] = None
        if record.get('seller'):
            continue
        choices = groups[invoice['key']]
        if len(choices) == 1:
            group_id, title = next(iter(choices.items()))
            seller = config.get('customer_group_sellers', {}).get(group_id, {}).get('seller')
            seller = aliases.get(seller,seller)
            if seller in active:
                invoice['repair_sales_proposal'] = dict(seller=seller,source='گروه مشتری سپیدار: '+title)
                continue
        ids = identities.get(customer_name(invoice.get('customer')),set())
        if len(ids) == 1:
            candidates = owners[next(iter(ids))]
            if len(candidates) == 1:
                invoice['repair_sales_proposal'] = dict(seller=next(iter(candidates)),source='مسئول فعلی مشتری در دیدار؛ نیازمند بررسی برای تاریخ فاکتور')
