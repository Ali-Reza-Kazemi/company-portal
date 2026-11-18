"""Customer reseller classification overrides sales pipelines, never after-sales."""
from .matching import customer_name


def deal_channel(deal, pipelines):
    channel = pipelines.get(deal.get('pipeline'))
    if channel in ('consumer', 'reseller') and deal.get('customer_reseller'):
        return 'reseller'
    return channel


def tagged_customer(name, customers):
    return customer_name(name) in tagged_customer_names(customers)


def tagged_customer_names(customers):
    names = {}
    for record in customers:
        key = customer_name(record.get('name'))
        if key:
            names.setdefault(key, {})[record['id']] = record.get('reseller')
    return {name for name, identities in names.items() if len(identities) == 1 and any(identities.values())}
