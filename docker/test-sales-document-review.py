"""Rollback-only verification of manual document type and no-quotation acknowledgement."""
from copy import deepcopy
from unittest.mock import patch
from test_support import init_site
init_site()
import frappe
from saeenaria_portal.sales_reports import service
try:
    view=service.report('1405-08')
    invoice=next(r for r in view['snapshot']['invoices'] if r['key'].startswith('Sale:') and not r['is_repair'])
    key=invoice['key']
    original=deepcopy(service.settings())
    service.save('document_type',dict(month=view['month'],key=key,type='repair',description='آزمون برگشت‌پذیر'),view['revision'])
    updated=service.report(view['month'])
    record=next(r for r in updated['snapshot']['invoices'] if r['key']==key)
    assert record['is_repair'] and record['manual_repair'] and record['channel']=='after_sales'
    assert key not in updated['snapshot']['suggestions']
    service.save('document_type',dict(month=view['month'],key=key,type='auto'),updated['revision'])
    assert not next(r for r in service.report(view['month'])['snapshot']['invoices'] if r['key']==key)['is_repair']
    service.save_config(original)
    snap=deepcopy(service.read_latest(view['month']))
    for row in snap['facts']['sales']:
        if 'Sale:'+str(row['DocumentId'])==key and row['DocumentType']=='Sale':
            row['QuotationStatus']='missing'
    with patch.object(service,'read_latest',return_value=snap):
        current=service.report(view['month'])
        values=dict(month=view['month'],key=key,seller=next(iter(current['snapshot']['sellers'])),channel='consumer')
        rejected=False
        try:
            service.save('invoice',values,current['revision'])
        except frappe.ValidationError:
            rejected=True
        assert rejected
        references=deepcopy(service.settings().get('customer_references',{}))
        service.save('invoice',{**values,'reviewed_no_quotation':True},service.report(view['month'])['revision'])
        assert service.settings()['invoices'][key]['reviewed_no_quotation']
        assert service.settings().get('customer_references',{})==references
    print('PASS repair classification, undo, quotation warning enforcement and no customer-reference propagation')
finally:
    frappe.db.rollback()
    frappe.destroy()
