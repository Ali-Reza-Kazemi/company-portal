"""Rollback-only live test of customer group mapping and requested conflict."""
from test_support import init_site
init_site()
import frappe
from saeenaria_portal.sales_reports import service

try:
    view = service.report('1405-07')
    raw = service.read_latest('1405-07')
    row = next(r for r in raw['facts']['sales'] if str(r['DocumentId']) == '56258' and r['DocumentType'] == 'Sale')
    group_id = str(row['CustomerGroupId'])
    assert group_id in view['customer_groups']
    seller = next(iter(view['directory']['seller_choices']))
    service.save('customer_group_seller', dict(month='1405-07',group_id=group_id,seller=seller), view['revision'])
    updated = service.report('1405-07')
    assert updated['customer_group_sellers'][group_id]['seller'] == seller
    assert updated['snapshot']['suggestions']['Sale:56258']['seller'] == seller
    assert updated['snapshot']['suggestions']['Sale:56258']['channel'] == 'reseller'
    assert service.settings()['customer_group_seller_history'][-1]['group_id'] == group_id
    service.save('customer_group_seller', dict(month='1405-07',group_id=group_id,seller=''), updated['revision'])
    assert group_id not in service.report('1405-07')['customer_group_sellers']
    print({'group_id':group_id, 'group_title':row['CustomerGroupTitle'], 'save_resolve_delete':'passed (rolled back)'})
finally:
    frappe.db.rollback()
    frappe.destroy()
