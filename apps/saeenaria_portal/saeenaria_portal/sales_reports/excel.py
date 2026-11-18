"""Application XLSX export of the four monthly attribution tabs."""
from io import BytesIO
from datetime import date as gregorian_date
import jdatetime
import xlsxwriter

TABS = {'unassigned':'بدون انتساب', 'assigned':'انتساب‌شده', 'repair':'تعمیرات', 'excluded':'خارج از آمار'}


def export(view, scope='all'):
    if scope not in {'all', *TABS}:
        raise ValueError('Invalid invoice export scope')
    snap = view.get('snapshot') or {}
    directory = view.get('directory', {})
    metadata = snap.get('crm_metadata', {})
    names = {**directory.get('sellers', {}), **directory.get('seller_choices', {}),
             **snap.get('sellers', {}), **metadata.get('seller_choices', {})}
    aliases = {**directory.get('seller_aliases', {}), **metadata.get('seller_aliases', {})}
    seller_name = lambda seller: names.get(aliases.get(seller,seller)) or names.get(seller) or ''
    channels = view['document_channels']
    headers = ['شماره سند','نوع سند','تاریخ شمسی','مشتری سپیدار','کد مشتری سپیدار','مشتری دیدار',
               'وضعیت پیش‌فاکتور','شماره پیش‌فاکتور','قبل از مالیات (ریال)','مالیات و عوارض (ریال)',
               'جمع نهایی سپیدار (ریال)','وضعیت انتساب کارشناس فروش','کارشناس فروش تأییدشده','کانال فعلی','کارشناس فروش پیشنهادی',
               'کانال پیشنهادی','شناسه معامله متصل','توضیحات تطبیق','علت تعمیرات','شرح تعمیرات','شناسه سند',
               'کارشناس فروش مرتبط با تعمیرات','وضعیت تأیید کارشناس فروش تعمیرات','منبع انتساب کارشناس تعمیرات','کارشناس فروش پیشنهادی تعمیرات','مسئول خدمات',
               'آسان ساز فروش','درصد پورسانت آسان‌ساز','پورسانت آسان ساز فروش (ریال)','روش پورسانت آسان‌ساز','توضیح مبلغ دستی','ثبت‌کننده پیش‌فاکتور سپیدار','نوع فاکتور سپیدار']
    grouped = {key:[] for key in TABS}
    for row in snap.get('invoices', []):
        if not view['start'] <= row['date'] <= view['end']:
            continue
        tab = 'excluded' if row.get('excluded') else 'repair' if row.get('is_repair') else 'assigned' if row.get('mapped') else 'unassigned'
        proposal = snap.get('suggestions', {}).get(row['key'], {})
        repair = row.get('is_repair')
        sales_seller = row.get('repair_sales_seller') if repair else row.get('seller')
        sales_proposal = row.get('repair_sales_proposal') or {} if repair else proposal
        assigned = bool(sales_seller) if repair else row.get('mapped')
        date = jdatetime.date.fromgregorian(date=gregorian_date.fromisoformat(row['date'])).strftime('%Y/%m/%d')
        quotation = {'present':'دارای پیش‌فاکتور','missing':'بدون پیش‌فاکتور سپیدار','unresolved':'ارتباط پیش‌فاکتور نامشخص','not_applicable':'برگشت از فروش'}
        grouped[tab].append([str(row['number']), 'برگشت از فروش' if row['key'].startswith('Return:') else 'فروش', date,
            row.get('customer'), str(row.get('customer_id') or ''), row.get('didar_customer_name') or row.get('related_customer_name') or proposal.get('related_customer_name'),
            quotation.get(row.get('quotation_status'),'بررسی نشده'),row.get('quotation_number'),row.get('amount'),row.get('tax'),row.get('total_amount'),
            'انتساب ثبت‌شده' if assigned else 'پیشنهاد نیازمند تأیید' if sales_proposal else 'بدون انتساب',
            seller_name(sales_seller),channels.get(row.get('channel'),''),seller_name(sales_proposal.get('seller')),channels.get(proposal.get('channel'),''),
            row.get('matched_deal_id'), '؛ '.join(filter(None,[proposal.get('reason') or row.get('match_note'),row.get('channel_reason')])),
            row.get('repair_reason'),row.get('repair_description'),row['key'],seller_name(row.get('repair_sales_seller')),
            'تأییدشده' if row.get('repair_sales_seller') else 'پیشنهاد نیازمند تأیید' if row.get('repair_sales_proposal') else 'بدون انتساب' if row.get('is_repair') else '',
            row.get('repair_sales_source') or (row.get('repair_sales_proposal') or {}).get('source'),
            seller_name((row.get('repair_sales_proposal') or {}).get('seller')),seller_name(row.get('seller')) if repair else '',
            (row.get('facilitator') or {}).get('name'),(row.get('facilitator') or {}).get('rate'),(row.get('facilitator') or {}).get('amount'),
            'دستی' if (row.get('facilitator') or {}).get('manual') else 'درصدی',(row.get('facilitator') or {}).get('note'),
            'برای برگشت از فروش کاربرد ندارد' if row['key'].startswith('Return:') else row.get('quotation_creator_name') or 'نام ثبت‌کننده در دسترس نیست',row.get('sale_type_title') or 'دریافت مجدد لازم است'])
    stream = BytesIO()
    book = xlsxwriter.Workbook(stream, {'in_memory':True,'strings_to_formulas':False,'strings_to_urls':False})
    heading = book.add_format({'bold':True,'bg_color':'#244195','font_color':'#FFFFFF','text_wrap':True,'valign':'vcenter'})
    text = book.add_format({'valign':'top','text_wrap':True})
    amount = book.add_format({'num_format':'#,##0.##;[Red](#,##0.##);0','valign':'top'})
    for key, title in TABS.items():
        if scope != 'all' and scope != key:
            continue
        sheet = book.add_worksheet(title)
        sheet.right_to_left()
        sheet.merge_range(0,0,0,len(headers)-1,'انتساب فاکتورها — '+title+' — ماه '+view['month'],heading)
        sheet.merge_range(1,0,1,len(headers)-1,'همه اسناد این تب در ماه انتخاب‌شده؛ مستقل از جستجوی صفحه. مبالغ از سپیدار. پیشنهادها تأییدشده نیستند. آخرین دریافت: '+str(snap.get('captured_at') or '—'),text)
        sheet.write_row(3,0,headers,heading)
        for index, values in enumerate(grouped[key],4):
            for col,value in enumerate(values):
                sheet.write(index,col,value,amount if col in (8,9,10,27,28) else text)
        sheet.freeze_panes(4,4)
        sheet.autofilter(3,0,3+len(grouped[key]),len(headers)-1)
        sheet.set_column(0,len(headers)-1,22)
        sheet.set_column(3,3,32)
        sheet.set_column(5,5,32)
        sheet.set_column(17,19,48)
        sheet.set_row(0,28)
        sheet.set_row(1,34)
        sheet.set_row(3,42)
    book.close()
    return stream.getvalue()
