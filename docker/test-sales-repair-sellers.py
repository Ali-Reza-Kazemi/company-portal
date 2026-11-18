"""Rollback-only repair sales responsibility and financial isolation checks."""
from test_support import init_site
init_site()
import frappe
from saeenaria_portal.sales_reports import service
from saeenaria_portal.sales_reports.repair_sellers import annotate
try:
    metadata=dict(seller_choices={'s1':'گروه','s2':'دیدار'},seller_aliases={},customer_catalog=[dict(id='c',name='مشتری')])
    inv=dict(key='Sale:1',customer='مشتری',is_repair=True)
    sales=[dict(DocumentType='Sale',DocumentId=1,CustomerGroupId=7,CustomerGroupTitle='گروه')]
    deals=[dict(customer_owners=[dict(customer_id='c',name='مشتری',seller='s2',active=True)])]
    config=dict(customer_group_sellers={'7':dict(seller='s1')})
    annotate([inv],sales,deals,config,metadata)
    assert inv['repair_sales_proposal']['seller']=='s1'
    annotate([inv],sales,deals,{},metadata)
    assert inv['repair_sales_proposal']['seller']=='s2'
    config['repair_sales_sellers']={'Sale:1':dict(seller='s2',source='manual')}
    annotate([inv],sales,deals,config,metadata)
    assert inv['repair_sales_seller']=='s2' and inv['repair_sales_proposal'] is None
    ambiguous={**metadata,'customer_catalog':metadata['customer_catalog']+[dict(id='other',name='مشتری')]}
    annotate([inv],sales,deals,{},ambiguous)
    assert inv['repair_sales_proposal'] is None
    view=service.report('1405-08')
    initial_rows=view['snapshot']['rows']
    invoice=next(i for i in view['snapshot']['invoices'] if i['is_repair'] and view['start']<=i['date']<=view['end'])
    seller=next(iter(view['snapshot']['crm_metadata']['seller_choices']))
    before=service.settings()
    service.save('repair_sales_seller',dict(month=view['month'],key=invoice['key'],seller=seller),view['revision'])
    updated=service.report(view['month'])
    saved=next(i for i in updated['snapshot']['invoices'] if i['key']==invoice['key'])
    assert saved['repair_sales_seller']==seller and saved['channel']=='after_sales'
    assert updated['snapshot']['rows']==initial_rows
    assert service.settings().get('customer_references')==before.get('customer_references')
    assert service.settings().get('invoices')==before.get('invoices')
    service.save('repair_sales_seller',dict(month=view['month'],key=invoice['key'],seller=''),updated['revision'])
    assert invoice['key'] not in service.settings()['repair_sales_sellers']
    latest=service.report(view['month'])
    proposals=[i for i in latest['snapshot']['invoices'] if i.get('repair_sales_proposal') and latest['start']<=i['date']<=latest['end']]
    if proposals:
        service.save('repair_sales_suggestions',dict(month=view['month'],keys=[proposals[0]['key']]),latest['revision'])
        assert service.settings()['repair_sales_sellers'][proposals[0]['key']]['seller']==proposals[0]['repair_sales_proposal']['seller']
    assert service.report(view['month'])['snapshot']['rows']==initial_rows
    print('PASS group priority, CRM fallback, ambiguity, frozen assignment, manual/bulk save/delete, financial isolation (rolled back)')
finally:
    frappe.db.rollback()
    frappe.destroy()
