"""Rollback-only live snapshot checks; no requests mutate Didar or Sepidar."""
from test_support import init_site
init_site()
import json
import frappe
from saeenaria_portal.sales_reports import service
key=frappe.get_single(service.DT).get_password('didar_api_key',raise_exception=False)
try:
    view=service.report('1405-08')
    snap=view['snapshot']
    assert snap and snap['crm_metadata']['available']
    assert 'facts' not in snap
    assert all(r.get('seller_name') for r in snap['rows'])
    choices=snap['crm_metadata']['seller_choices']
    inactive=snap['crm_metadata']['inactive_sellers']
    assert not (set(choices)&set(inactive))
    assert 'انواع دریل' in view['groups'] and 'drill' not in view['groups']
    seller=next(iter(choices))
    service.save('target',dict(month='1405-08',seller=seller,channel='consumer',target=123456789,discount_limit=1.23),view['revision'])
    updated=service.report('1405-08')
    row=next(r for r in updated['snapshot']['rows'] if r['seller']==seller and r['channel']=='consumer')
    assert row['target']==123456789 and row['discount_limit']==1.23
    assert frappe.get_single(service.DT).get_password('didar_api_key',raise_exception=False)==key
    suggestions=updated['snapshot'].get('suggestions',{})
    if suggestions:
        selected=list(suggestions)[:2]
        service.save('suggestions',dict(month='1405-08',keys=selected),updated['revision'])
        confirmed=service.report('1405-08')
        assert confirmed['snapshot']['unmapped_invoices']<=updated['snapshot']['unmapped_invoices']-len(selected)
    print(json.dumps({'passed':True,'active_choices':len(choices),'inactive_identities':len(inactive),'purchase_groups':len(view['groups']),'suggestions':len(suggestions),'live_target_overlay':True,'key_preserved':True},ensure_ascii=False))
finally:
    frappe.db.rollback()
    assert frappe.get_single(service.DT).get_password('didar_api_key',raise_exception=False)==key
    frappe.destroy()
