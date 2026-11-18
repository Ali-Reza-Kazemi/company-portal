"""Rollback-only manual document linking and global reservation checks."""
from test_support import init_site
init_site()
import frappe
from saeenaria_portal.sales_reports import service
from saeenaria_portal.sales_reports.manual_matching import reserved_deals, item_overlap
try:
    items=[dict(ItemCode=' A ',Quantity=2),dict(ItemCode='a',Quantity=3),
           dict(ItemCode='B',Quantity=1),dict(ItemCode='C',Quantity=4)]
    overlap=item_overlap(items,[dict(ProductCode='A',Quantity=5),dict(ProductCode='b',Quantity=2),dict(ProductCode='D',Quantity=1)])
    assert (overlap['matched'],overlap['total'],overlap['equal_quantity'],overlap['extra'])==(2,3,1,1)
    assert not item_overlap(items,None)['available']
    assert item_overlap(items,[dict(ProductCode='X',Quantity=1)])['matched']==0
    assert item_overlap(items,[dict(ProductCode='A',Quantity=None)])['equal_quantity']==0
    context=service.deal_candidates('1405-07','Sale:56224',30)
    assert context['deals']
    assert context['invoice']['items']
    assert all(d['item_match']['total']>0 for d in context['deals'])
    deal=context['deals'][0]
    before=service.settings().get('customer_references',{}).copy()
    service.save('manual_deal',dict(month='1405-07',key='Sale:56224',deal_id=deal['id'],days=30,reviewed=True),context['revision'])
    config=service.settings()
    assert config['invoices']['Sale:56224']['deal_ids']==[deal['id']]
    assert config['invoices']['Sale:56224']['method']=='manual'
    assert config.get('customer_references',{})==before
    assert deal['id'] in reserved_deals(config,'Sale:another')
    assert deal['id'] not in reserved_deals(config,'Sale:56224')
    changed=service.report('1405-07')
    invoice=next(i for i in changed['snapshot']['invoices'] if i['key']=='Sale:56224')
    assert invoice['matched_deal_id']==deal['id'] and invoice['mapped']
    try:
        service.save('manual_deal',dict(month='1405-07',key='Sale:56224',deal_id='nonexistent',days=30,reviewed=True),changed['revision'])
        raise AssertionError('Unknown deal accepted')
    except frappe.ValidationError:
        pass
    print('PASS manual link, per-invoice scope, reservation, history, invalid deal (rolled back)')
finally:
    frappe.db.rollback()
    frappe.destroy()
