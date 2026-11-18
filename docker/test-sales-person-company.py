from test_support import init_site
init_site()
import json
import frappe
from saeenaria_portal.sales_reports import service
try:
    snap=service.report('1405-07')['snapshot']
    raw=service.read_latest('1405-07')
    proposal=snap['suggestions']['Sale:56224']
    assert proposal['related_customer_name']=='سازه های فلزی صارمی'
    assert proposal['seller']=='7a084dd2-bae7-4a27-978a-54444958553c'
    config=service.settings()
    before=config.get('customer_references',{}).copy()
    invoice=next(r for r in snap['invoices'] if r['key']=='Sale:56224')
    service.remember_customer_reference(config,invoice,proposal)
    assert config.get('customer_references',{})==before
    view=service.report('1405-07')
    service.save('invoice',dict(month='1405-07',key='Sale:56224',seller=proposal['seller'],channel=proposal['channel']),view['revision'])
    assert service.settings().get('customer_references',{})==before
    assert service.settings()['invoices']['Sale:56224']['related_customer_name']==proposal['related_customer_name']
    print(json.dumps({'proposal':proposal,'manual_save_no_customer_reference':'passed, rolled back'},ensure_ascii=False))
finally:
    frappe.db.rollback()
    frappe.destroy()
