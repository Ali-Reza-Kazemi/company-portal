"""Reviewable per-invoice links; never infer a permanent employment relationship."""
from datetime import date
from decimal import Decimal, InvalidOperation
from .channels import deal_channel
from .calculations import PIPELINES, CHANNELS


def item_overlap(invoice_items, deal_items):
    """Compare unique product codes and summed quantities, independently of price."""
    def collect(items, code_field):
        result = {}
        for item in items or []:
            code = str(item.get(code_field) or '').strip().casefold()
            if not code:
                continue
            entry = result.setdefault(code, dict(quantity=Decimal(0), valid=True,
                                                title=item.get('ItemTitle') or code))
            try:
                quantity = Decimal(str(item.get('Quantity')))
                if not quantity.is_finite():
                    raise ValueError()
                entry['quantity'] += quantity
            except (InvalidOperation, ValueError):
                entry['valid'] = False
        return result
    source, target = collect(invoice_items, 'ItemCode'), collect(deal_items, 'ProductCode')
    shared = source.keys() & target.keys()
    details = [dict(code=code, title=item['title'], present=code in target,
                    invoice_quantity=float(item['quantity']) if item['valid'] else None,
                    deal_quantity=float(target[code]['quantity']) if code in target and target[code]['valid'] else None,
                    equal_quantity=bool(code in target and item['valid'] and target[code]['valid']
                                        and item['quantity'] == target[code]['quantity']))
               for code, item in source.items()]
    return dict(available=bool(deal_items), matched=len(shared), total=len(source),
                equal_quantity=sum(item['equal_quantity'] for item in details),
                extra=len(target.keys() - source.keys()), details=details)


def reserved_deals(config, except_key=None):
    result = set()
    for key, assignment in config.get('invoices', {}).items():
        if key != except_key and (assignment.get('confidence') in ('document', 'document_minor_difference', 'manual_document') or assignment.get('document_confidence')):
            result.update(assignment.get('deal_ids', []))
    return result


def candidates(invoice, deals, config, sellers, days):
    used = reserved_deals(config, invoice['key'])
    target = date.fromisoformat(invoice['date'])
    result = []
    for deal in deals:
        if deal['source_id'] in used or deal.get('state') == 2:
            continue
        channel = deal_channel(deal, config.get('pipelines', PIPELINES))
        if channel not in CHANNELS or not deal.get('seller'):
            continue
        dates = []
        for field in ('registered_at', 'won_at'):
            if deal.get(field):
                try:
                    dates.append(date.fromisoformat(str(deal[field])[:10]))
                except ValueError:
                    pass
        if not dates or min(abs((value-target).days) for value in dates) > days:
            continue
        result.append(dict(id=deal['source_id'], title=deal.get('title') or ' / '.join(deal.get('customer_names', [])),
                           code=deal.get('code'), customer=' / '.join(deal.get('customer_names', [])),
                           seller=deal['seller'], seller_name=sellers.get(deal['seller']) or deal.get('seller_name') or 'نامشخص',
                           channel=channel, channel_name=CHANNELS[channel], pipeline=deal.get('pipeline'),
                           date=str(deal.get('registered_at') or '')[:10], won_date=str(deal.get('won_at') or '')[:10],
                           state='موفق' if deal.get('state') == 1 else 'باز', total=deal.get('document_total'),
                           distance=min(abs((value-target).days) for value in dates),
                           item_match=item_overlap(invoice.get('items'), deal.get('items'))))
    return sorted(result, key=lambda row:(row['distance'], row['title']))
