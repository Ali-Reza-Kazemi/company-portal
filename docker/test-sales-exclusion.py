"""Rollback-only check of persistent customer exclusion, no mutation of source documents."""
from test_support import init_site
init_site()
import frappe
from saeenaria_portal.sales_reports import service
try:
    view=service.report('1405-07')
    invoice=next(r for r in view['snapshot']['invoices'] if r['customer_id'] and not r.get('excluded'))
    customer=invoice['customer_id']
    service.save('customer_exclusion',dict(month=view['month'],customer_id=customer,excluded=True),view['revision'])
    changed=service.report(view['month'])
    assert all(r['excluded'] for r in changed['snapshot']['invoices'] if r['customer_id']==customer)
    assert not any(r['key'] in changed['snapshot']['suggestions'] for r in changed['snapshot']['invoices'] if r['customer_id']==customer)
    later=service.report('1405-08')
    assert customer in later['excluded_customers']
    assert all(r['excluded'] for r in later['snapshot']['invoices'] if r['customer_id']==customer)
    service.save('customer_exclusion',dict(month=later['month'],customer_id=customer,excluded=False),later['revision'])
    restored=service.report(view['month'])
    assert all(not r['excluded'] for r in restored['snapshot']['invoices'] if r['customer_id']==customer)
    print('PASS customer exclusion, all-month scope, proposal removal and restoration')
finally:
    frappe.db.rollback()
    frappe.destroy()
