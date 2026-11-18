"""Per-customer facilitator accruals with explicit per-document overrides, in rials."""
from decimal import Decimal, ROUND_HALF_UP
from collections import defaultdict


def cost(invoice, config):
    history = [record for record in config.get('facilitator_customer_history', [])
               if str(record.get('customer_id')) == str(invoice.get('customer_id'))
               and str(record.get('from_date', '')) <= str(invoice.get('date', ''))]
    rule = max(history, key=lambda record: record.get('from_date', '')) if history else config.get('facilitator_customers', {}).get(str(invoice.get('customer_id')), {})
    override = config.get('facilitator_invoices', {}).get(invoice['key'])
    base = Decimal(str(invoice.get('amount') or 0))
    rate = Decimal(str(rule.get('rate') or 0))
    calculated = (base * rate / 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    return dict(name=(override or rule).get('name',''),rate=float(rate),base=float(base),
                calculated=float(calculated),amount=float(Decimal(str(override['amount']))) if override is not None else float(calculated),
                manual=override is not None, note=(override or {}).get('note',''))


def annotate(snapshot, config, start, end):
    by_seller = defaultdict(Decimal)
    totals = {}
    for invoice in snapshot.get('invoices', []):
        value = cost(invoice, config)
        invoice['facilitator'] = value
        if not str(start)<=invoice['date']<=str(end) or invoice.get('excluded') or not value['name']:
            continue
        amount = Decimal(str(value['amount']))
        total = totals.setdefault(value['name'],dict(name=value['name'],amount=Decimal(0),sales=Decimal(0),repairs=Decimal(0),unassigned=Decimal(0),documents=0))
        total['amount'] += amount
        total['documents'] += 1
        if invoice.get('is_repair'):
            total['repairs'] += amount
        elif not invoice.get('mapped'):
            total['unassigned'] += amount
        else:
            total['sales'] += amount
            by_seller[(invoice.get('seller'),invoice.get('channel'))] += amount
    for row in snapshot.get('rows', []):
        row['facilitator_cost'] = float(by_seller[(row['seller'],row['channel'])])
        row['after_facilitator'] = float(Decimal(str(row['actual']))-Decimal(str(row['facilitator_cost']))) if row.get('actual') is not None else None
    snapshot['facilitator_totals'] = [{k:float(v) if isinstance(v,Decimal) else v for k,v in total.items()} for _,total in sorted(totals.items())]
