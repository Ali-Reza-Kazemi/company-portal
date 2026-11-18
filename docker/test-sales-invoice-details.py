"""Read-only invoice detail reconciliation and access checks."""
from test_support import init_site
init_site()
import frappe
from saeenaria_portal.sales_reports import service
try:
    snapshot=service.read_latest('1405-07')
    key=next(i['key'] for i in snapshot['invoices'] if i['number']=='13568' and i['customer_id']=='6702')
    detail=service.invoice_details('1405-07',key)
    assert len(detail['items'])==5
    assert detail['totals']['total']==1276176550
    assert abs(sum(i['total'] for i in detail['items'])-detail['totals']['total'])<0.01
    assert detail['customer_id']=='6702'
    assert detail['creator_name']
    assert detail['quotation_creator_status']=='present'
    assert detail['quotation_creator_name']
    try:
        service.invoice_details('1405-08',key)
        raise AssertionError('Wrong-month invoice exposed')
    except frappe.ValidationError:
        pass
    frappe.set_user('Guest')
    try:
        service.invoice_details('1405-07',key)
        raise AssertionError('Guest access allowed')
    except frappe.PermissionError:
        pass
    print('PASS detail rows, totals, month boundary and authorization')
finally:
    frappe.db.rollback()
    frappe.destroy()
