"""Facilitator costs and rollback-only configuration verification."""
from copy import deepcopy
from unittest.mock import patch
from test_support import init_site
init_site()
import frappe
from saeenaria_portal.sales_reports import service
from saeenaria_portal.sales_reports.facilitators import annotate, cost
try:
    config=dict(facilitator_customers={'1':dict(name='آسان‌ساز',rate=10)})
    invoice=dict(key='Sale:1',customer_id='1',date='2026-10-25',amount=105, mapped=True,seller='s',channel='consumer')
    assert cost(invoice,config)['amount']==11  # whole rials, half up
    config['facilitator_invoices']={'Sale:1':dict(name='آسان‌ساز',amount=0,note='بدون پورسانت')}
    assert cost(invoice,config)['amount']==0 and cost(invoice,config)['manual']
    config['facilitator_invoices']={}
    snapshot=dict(invoices=[invoice,{**invoice,'key':'Return:1','amount':-50},{**invoice,'key':'Sale:2','is_repair':True},
                            {**invoice,'key':'Sale:3','mapped':False},{**invoice,'key':'Sale:4','excluded':True}],
                  rows=[dict(seller='s',channel='consumer',actual=55)])
    annotate(snapshot,config,'2026-10-23','2026-11-21')
    assert snapshot['rows'][0]['actual']==55
    assert snapshot['rows'][0]['facilitator_cost']==6
    assert snapshot['rows'][0]['after_facilitator']==49
    assert snapshot['facilitator_totals'][0]['amount']==28
    assert snapshot['facilitator_totals'][0]['repairs']==11
    assert snapshot['facilitator_totals'][0]['unassigned']==11
    view=service.report('1405-08')
    inv=next(i for i in view['snapshot']['invoices'] if i['key'].startswith('Sale:') and view['start']<=i['date']<=view['end'] and not i['is_repair'] and not i['excluded'])
    original=deepcopy(service.settings())
    values=dict(month=view['month'],customer_id=inv['customer_id'],name='آزمون آسان‌ساز',rate=2)
    service.save('facilitator_customer',values,view['revision'])
    refreshed=service.report(view['month'])
    assert service.settings()['facilitator_customers'][inv['customer_id']]['rate']==2
    service.save('facilitator_invoice',dict(month=view['month'],key=inv['key'],name='آزمون آسان‌ساز',amount=123,note='آزمون'),refreshed['revision'])
    refreshed=service.report(view['month'])
    current=next(i for i in refreshed['snapshot']['invoices'] if i['key']==inv['key'])
    assert current['facilitator']['amount']==123 and current['facilitator']['manual']
    assert service.settings()['facilitator_customers'][inv['customer_id']]['rate']==2
    service.save('facilitator_invoice',dict(month=view['month'],key=inv['key'],remove=True),refreshed['revision'])
    assert inv['key'] not in service.settings()['facilitator_invoices']
    assert service.settings().get('invoices')==original.get('invoices')
    assert service.settings().get('customer_references')==original.get('customer_references')
    # Customers offered from earlier saved references/rules need no current invoice.
    for field in ('customer_references', 'customer_rules'):
        config = service.settings()
        customer = 'facilitator-regression-' + field
        record = dict(customer_id=customer, customer_name='مشتری ماه دیگر')
        if field == 'customer_rules':
            config.setdefault(field, []).append(record)
        else:
            config.setdefault(field, {})[customer] = record
        service.save_config(config)
        revision = str(frappe.db.get_single_value(service.DT, 'modified'))
        with patch.object(service, 'read_latest', return_value={'facts': {'sales': []}}):
            service.save('facilitator_customer', dict(month=view['month'], customer_id=customer,
                         name='آسان ساز آزمایشی', rate=5), revision)
        assert service.settings()['facilitator_customers'][customer]['customer_name'] == record['customer_name']
    revision = str(frappe.db.get_single_value(service.DT, 'modified'))
    with patch.object(service, 'read_latest', return_value={'facts': {'sales': []}}):
        try:
            service.save('facilitator_customer', dict(month=view['month'], customer_id='unknown-customer',
                         name='آسان ساز آزمایشی', rate=5), revision)
        except frappe.ValidationError:
            pass
        else:
            raise AssertionError('Unknown customer accepted')
    print('PASS percent base, rounding, zero override, return, repair/exclusion isolation, save/delete, audit (rolled back)')
finally:
    frappe.db.rollback()
    frappe.destroy()
