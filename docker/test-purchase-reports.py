"""Run inside bench; all report fixtures live in a disposable temporary directory."""
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import frappe
from test_support import init_site
init_site()
from saeenaria_portal.purchase_reports import service as report
from saeenaria_portal import permissions

try:
    with patch.object(permissions, 'admin', return_value=False), patch.object(permissions, 'roles', return_value=set()), patch.object(permissions, 'managed_domains', return_value=[]):
        assert not report.allowed('Guest')
        assert not report.allowed('test-employee')
        with patch.object(permissions, 'managed_domains', return_value=['marketing']):
            assert not report.allowed('test-other-manager')
        with patch.object(permissions, 'managed_domains', return_value=['inventory']):
            assert report.allowed('test-inventory-manager')
        with patch.object(permissions, 'roles', return_value={'Company Director'}):
            assert report.allowed('test-director')
        with patch.object(permissions, 'roles', return_value={'Portal HR Manager'}):
            assert not report.allowed('test-hr')
    frappe.set_user('Guest')
    for fn, args in [(report.overview, {}), (report.report, {'name':'orders'}), (report.export_csv, {'name':'orders'})]:
        try:
            fn(**args)
            raise AssertionError('Guest report access')
        except frappe.PermissionError:
            pass
    frappe.set_user('Administrator')
    with TemporaryDirectory(prefix='purchase-report-test-') as folder, patch.object(report, 'storage', return_value=Path(folder)), patch.object(report, 'credentials', return_value={}):
        assert not report.report('orders')['available']
        assert report.report('orders')['metrics'] == []
        data = [{'ItemCode':str(i), 'ItemTitle':'کالا', 'EffectiveReference':str(i), 'StockTitle':'همه انبارها', 'Category':'A', 'SuggestedOrderQty':2, 'SuggestedOrderValueRial':100, 'OfficialPriceRial':50} for i in range(120)]
        data += [dict(data[0], StockTitle='مرکزی')]
        report.write_snapshot('combined', {'updated_at':'2026-10-19T00:00:00+00:00', 'reports':{'orders':data}})
        result = report.report('orders', page=2, page_size=50)
        assert result['total']==120 and len(result['rows'])==50
        assert next(m['value'] for m in result['metrics'] if m['name']=='OrderValue')==12000
        assert report.report('orders',filters={'StockTitle':'مرکزی'})['total']==1
        assert report.report('orders',filters={'search':'ناموجود'})['total']==0
        assert report.report('orders',sort_by='DROP TABLE User')['total']==120
        targets=[dict(StockId=1,ReferenceCode='A',CustomerId=i,ExcessValueRial=1000) for i in (1,2,3)]
        assert next(m['value'] for m in report.metrics('targets',targets) if m['name']=='ExcessValue')==1000
        assert next(m['value'] for m in report.metrics('targets',targets) if m['name']=='Customers')==3
        turnover=[dict(NetSalesQty12M=100,AverageInventoryQty12M=10),dict(NetSalesQty12M=100,AverageInventoryQty12M=90)]
        assert next(m['value'] for m in report.metrics('turnover',turnover) if m['name']=='Rate')==2
        before=(Path(folder)/'combined.json').read_bytes()
        with patch.object(report,'extract_sqlserver',side_effect=RuntimeError('not printed sensitive error')):
            report.refresh_data()
        assert (Path(folder)/'combined.json').read_bytes()==before
        assert report.read_snapshot('state')['errors']=={'portal':'RuntimeError'}
        assert not report.read_snapshot('state')['running']
        data[0]['ItemTitle']='=HYPERLINK("unsafe")'
        report.write_snapshot('combined', {'reports':{'orders':data}})
        report.export_csv('orders')
        content=frappe.local.response['filecontent'].decode('utf-8-sig')
        assert "'=HYPERLINK" in content
        assert len(content.splitlines())==121
    print('PASS purchase reports: permission matrix, Guest denial, pagination, full-filter totals, filters, safe sort, customer deduplication, weighted turnover, failure preservation and CSV formula protection. No real source data changed.')
finally:
    frappe.db.rollback()
    frappe.destroy()
