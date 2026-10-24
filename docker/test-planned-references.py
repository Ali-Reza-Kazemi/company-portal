"""Transactional checks for planned brand references and exact pagination."""
import os
from datetime import date
from unittest.mock import patch
import frappe
from test_support import init_site
init_site()
from saeenaria_portal.purchase_reports import product_catalog as c
from saeenaria_portal.purchase_reports.calculations import calculate
try:
 c.insert_many([dict(item_code='PLANNED-TEST-'+str(i).zfill(3),item_title='fixture',category='گروه آزمون',reference_code='PLANNED-TEST-'+str(i).zfill(3),needs_completion=0,review_status='تأیید شده') for i in range(61)])
 first=c.listing(search='PLANNED-TEST-',status='all',page=1);last=c.listing(search='PLANNED-TEST-',status='all',page=99)
 assert first['matched']==61 and first['pages']==2 and len(first['rows'])==50 and first['has_next']
 assert last['page']==2 and len(last['rows'])==11 and last['row_start']==51 and last['row_end']==61 and not last['has_next']
 empty=c.listing(search='NO-MATCH-567823',status='all');assert empty['matched']==0 and empty['row_start']==0 and empty['pages']==1
 code='PLANNED-TEST-000';reference='PLANNED-TEST-BRAND';doc=frappe.get_doc(c.DT,code)
 with patch.object(frappe.db,'commit'),patch('saeenaria_portal.purchase_reports.service._enqueue'),patch('saeenaria_portal.purchase_reports.workflow.enqueue_daily'):
  c.save(code,'گروه آزمون',reference,order_control='مجاز دستی',expected_modified=str(doc.modified));doc.reload()
  target=frappe.get_doc(c.DT,reference);assert target.is_planned and not target.source_present and target.reference_code==reference and target.category=='گروه آزمون'
  assert doc.reference_code==reference
  c.save(code,'گروه ویرایش‌شده',reference,expected_modified=str(doc.modified));doc.reload();assert doc.category=='گروه ویرایش‌شده'
  assert c.references('PLANNED-TEST-BRAND')[0].is_planned
 baseline=[{'ItemCode':r.item_code,'ItemTitle':r.item_title} for r in frappe.get_all(c.DT,filters={'source_present':1},fields=['item_code','item_title'],limit_page_length=0)]
 c.sync_items(baseline);target.reload();assert target.is_planned and not target.source_present
 count=frappe.db.count(c.DT)
 c.sync_items(baseline+[{'ItemCode':reference,'ItemTitle':'نام واقعی از سپیدار'}]);target.reload()
 assert not target.is_planned and target.source_present and target.item_title=='نام واقعی از سپیدار' and target.category=='گروه آزمون' and frappe.db.count(c.DT)==count
 # A brand reference with no Sepidar inventory still aggregates real demand and orders.
 mapping=[{'کد کالا':'SRC-TEST','نام کالا':'Source','کد مرجع دستی':'BRAND-TEST','دسته‌بندی اختصاصی':'گردبر'}, {'کد کالا':'BRAND-TEST','نام کالا':'Brand','کد مرجع دستی':'BRAND-TEST','دسته‌بندی اختصاصی':'گردبر','کنترل سفارش':'مجاز دستی','وضعیت بررسی':'تأیید شده'}]
 reports=calculate(mapping,[],[],[{'ItemCode':'SRC-TEST','StockId':1,'StockTitle':'test','Quantity':0,'UnitPrice':None}],[{'ItemCode':'SRC-TEST','StockId':1,'StockTitle':'test','DocumentDate':'2026-10-01','JalaliYear':1405,'JalaliMonthNumber':7,'Quantity':360}],[],[{'ItemCode':'SRC-TEST'}],today=date(2026,10,22))
 root=next(r for r in reports['orders'] if r['ItemCode']=='BRAND-TEST' and r['StockId'] is None)
 assert root['AverageMonthlyNetSales']==10 and root['SuggestedOrderQty']>0 and root['OfficialPriceRial'] is None
 print('PASS: exact filtered page totals, last-page clamp, empty results, planned reference creation, editing reviewed items, reference search, sync preservation, future Sepidar merge without duplication, demand aggregation and unknown-price handling.')
finally:frappe.db.rollback();frappe.destroy()
