"""Read-only validation of the application's attribution XLSX download."""
from io import BytesIO
from openpyxl import load_workbook
from test_support import init_site
init_site()
import frappe
from saeenaria_portal.sales_reports import service
from saeenaria_portal.sales_reports.excel import export, TABS
try:
    view=service.report('1405-07')
    book=load_workbook(BytesIO(export(view)))
    assert book.sheetnames==list(TABS.values())
    expected={r['key']:r for r in view['snapshot']['invoices'] if view['start']<=r['date']<=view['end']}
    actual={}
    for sheet in book:
        assert sheet.sheet_view.rightToLeft and sheet.freeze_panes=='E5'
        for row in sheet.iter_rows(min_row=5,values_only=True):
            key=row[20]
            assert key not in actual
            actual[key]=row[10]
            r=expected[key]
            tab='excluded' if r['excluded'] else 'repair' if r['is_repair'] else 'assigned' if r['mapped'] else 'unassigned'
            assert sheet.title==TABS[tab]
            assert isinstance(row[10],(float,int))
            assert abs(row[10]-r['total_amount'])<0.01
    assert set(actual)==set(expected)
    # The download enriches old snapshots without a CRM refresh or one query per row.
    service.export_invoices('1405-07')
    downloaded = load_workbook(BytesIO(frappe.local.response.filecontent))
    from saeenaria_portal.sales_reports.sources import invoice_creator
    verified = 0
    for sheet in downloaded:
        assert sheet.cell(4,32).value == 'ثبت‌کننده پیش‌فاکتور سپیدار'
        for values in sheet.iter_rows(min_row=5, values_only=True):
            key = values[20]
            assert values[31]
            if key.startswith('Sale:') and expected[key].get('quotation_status') == 'present' and verified < 3:
                creator = invoice_creator('Sale', key.split(':')[1]) or {}
                name = str(creator.get('quotation_creator_name') or '').strip() or str(creator.get('quotation_creator_username') or '').strip()
                assert values[31] == (name or 'نام ثبت‌کننده در دسترس نیست')
                verified += 1
    assert verified == 3
    assert load_workbook(BytesIO(export(view,'repair'))).sheetnames==['تعمیرات']
    # Repair sales ownership belongs in the main salesperson column, not only far-right extras.
    repair_view={**view,'snapshot':{**view['snapshot'],'sellers':{'service':'مسئول خدمات'},'crm_metadata':{},'invoices':[
        dict(key='Sale:test',number='test',date=view['start'],customer='نمونه',is_repair=True,
             seller='service',channel='after_sales',repair_sales_seller='alias',mapped=True,
             repair_sales_proposal=None,amount=10,tax=1,total_amount=11,quotation_creator_name='ثبت‌کننده پیش‌فاکتور آزمایشی')]},
        'directory':{'sellers':{'sales':'کارشناس فروش'},'seller_aliases':{'alias':'sales'}}}
    repair_book=load_workbook(BytesIO(export(repair_view,'repair')))
    repair_sheet=repair_book['تعمیرات']
    assert repair_sheet.cell(5,13).value=='کارشناس فروش'
    assert repair_sheet.cell(5,12).value=='انتساب ثبت‌شده'
    assert repair_sheet.cell(5,26).value=='مسئول خدمات'
    assert repair_sheet.cell(4,32).value=='ثبت‌کننده پیش‌فاکتور سپیدار'
    assert repair_sheet.cell(5,32).value=='ثبت‌کننده پیش‌فاکتور آزمایشی'
    repair_view['snapshot']['invoices'][0].update(repair_sales_seller=None,repair_sales_proposal={'seller':'alias'})
    pending=load_workbook(BytesIO(export(repair_view,'repair')))['تعمیرات']
    assert pending.cell(5,13).value is None and pending.cell(5,15).value=='کارشناس فروش'
    assert pending.cell(5,12).value=='پیشنهاد نیازمند تأیید'
    row=next(iter(expected.values()))
    row['customer']='=1+1'
    view['snapshot']['invoices']=[row]
    check=load_workbook(BytesIO(export(view)))
    cells=[sheet.cell(5,4) for sheet in check if sheet.max_row>=5]
    assert cells[0].value=='=1+1' and cells[0].data_type=='s'
    frappe.set_user('Guest')
    try:
        service.export_invoices('1405-07')
        raise AssertionError('Guest export allowed')
    except frappe.PermissionError:
        pass
    print('PASS four tabs, month scope, unique rows, Sepidar amounts, single tab, text safety, access control')
finally:
    frappe.db.rollback()
    frappe.destroy()
