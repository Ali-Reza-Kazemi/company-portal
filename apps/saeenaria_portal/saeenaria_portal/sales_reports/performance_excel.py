"""Monthly performance and repair invoice workbook with a column guide."""
from io import BytesIO

import xlsxwriter


PERFORMANCE = [
    ('seller_name', 'کارشناس', 'نام کارشناس منتسب.'),
    ('channel_label', 'کانال', 'کانال مصرف‌کننده یا واسطه.'),
    ('target', 'تارگت ماه (ریال)', 'هدف فروش ثبت‌شده.'),
    ('actual', 'فروش واقعی با تعمیرات (ریال)', 'فروش پس از تخفیف با احتساب تعمیرات منتسب.'),
    ('repair_sales', 'مبلغ تعمیرات (ریال)', 'مبلغ فاکتورهای تعمیرات منتسب.'),
    ('repair_invoice_count', 'تعداد فاکتور تعمیرات', 'تعداد فاکتورهای تعمیراتی منتسب.'),
    ('facilitator_cost', 'پورسانت آسان‌ساز (ریال)', 'پورسانت فاکتورهای فروش و تعمیرات.'),
    ('achievement', 'تحقق تارگت (%)', 'فروش واقعی با احتساب تعمیرات تقسیم بر تارگت.'),
    ('average_invoice', 'میانگین فاکتور (ریال)', 'فروش تقسیم بر تعداد فاکتورها.'),
    ('new_customers', 'مشتری جدید', 'تعداد مشتریان جدید در ماه.'),
    ('conversion', 'نرخ تبدیل (%)', 'نرخ تبدیل فرصت‌های فروش.'),
    ('followup', 'نرخ پیگیری (%)', 'نرخ پیگیری فرصت‌ها.'),
    ('retention', 'نرخ حفظ مشتری (%)', 'نرخ حفظ مشتریان.'),
    ('discount', 'میانگین تخفیف (%)', 'میانگین تخفیف فروش.'),
    ('discount_limit', 'حد مجاز تخفیف (%)', 'سقف تخفیف ثبت‌شده.'),
    ('discount_deviation', 'انحراف تخفیف (واحد درصد)', 'اختلاف تخفیف با سقف مجاز.'),
    ('unclassified_quantity', 'تعداد بدون گروه خرید', 'مقدار فروش کالاهای بدون گروه.'),
    ('total_quantity', 'جمع کالای فروخته‌شده', 'مجموع تعداد فروش کالا.'),
    ('coverage', 'پوشش مالی', 'وضعیت کامل بودن انتساب مالی.'),
]
REPAIRS = [
    ('repair_seller_name', 'کارشناس', 'کارشناس فروش تأییدشده برای تعمیرات.'),
    ('channel_label', 'نوع مشتری / کانال', 'مصرف‌کننده یا واسطه بر اساس مشخصات مشتری.'),
    ('repair_invoice_count', 'تعداد فاکتور تعمیرات', 'تعداد فاکتورهای تعمیراتی منتسب به کارشناس در کانال.'),
    ('gross', 'جمع مبلغ قبل از تخفیف (ریال)', 'مجموع مبلغ تعمیرات پیش از تخفیف.'),
    ('discount', 'جمع تخفیف (ریال)', 'مجموع تخفیف فاکتورهای تعمیرات.'),
    ('discount_percent', 'میانگین تخفیف (%)', 'مجموع تخفیف تقسیم بر مبلغ پیش از تخفیف.'),
    ('repair_sales', 'فروش پس از تخفیف (ریال)', 'مجموع مبلغ پیش از مالیات پس از تخفیف.'),
    ('tax', 'مالیات و عوارض (ریال)', 'مجموع مالیات و عوارض فاکتورها.'),
    ('total_amount', 'جمع نهایی (ریال)', 'مجموع مبالغ نهایی فاکتورها.'),
    ('repair_facilitator_amount', 'پورسانت آسان‌ساز (ریال)', 'مجموع پورسانت محاسبه‌شده یا مبالغ دستی.'),
]
FACILITATORS = [
    ('name', 'آسان‌ساز فروش', 'نام آسان‌ساز فروش.'),
    ('sales', 'پورسانت فروش منتسب (ریال)', 'مجموع پورسانت فروش‌های منتسب.'),
    ('repairs', 'پورسانت تعمیرات (ریال)', 'مجموع پورسانت تعمیرات.'),
    ('unassigned', 'پورسانت اسناد بدون انتساب (ریال)', 'پورسانت اسناد بدون کارشناس.'),
    ('amount', 'پورسانت آسان‌ساز ـ جمع (ریال)', 'مجموع پورسانت آسان‌ساز.'),
    ('documents', 'تعداد اسناد', 'تعداد اسناد محاسبه‌شده.'),
]


def export(view):
    snapshot = view['snapshot']
    rows = []
    groups = snapshot.get('group_labels', {})
    performance_definitions = PERFORMANCE + [
        ('group_' + key, label + ' (تعداد خالص)', 'تعداد خالص فروش این گروه کالا.')
        for key, label in groups.items()
    ]
    for source in snapshot.get('rows', []):
        row = {**source, 'channel_label': view['channels'].get(source['channel'])}
        row.update({'group_' + key: value for key, value in source.get('groups', {}).items()})
        row['coverage'] = 'انتساب اسناد ماه کامل است' if row.get('financial_complete') else 'انتساب ناقص یا داده مالی موجود نیست'
        rows.append(row)
    repair_totals = {}
    for row in snapshot.get('repair_rows', []):
        seller = row.get('repair_seller')
        if not seller or row.get('excluded'):
            continue
        key = (seller, row['repair_channel'])
        summary = repair_totals.setdefault(key, {
            'repair_seller_name': row['repair_seller_name'],
            'channel_label': view['channels'].get(row['repair_channel']),
            'repair_invoice_count': 0, 'gross': 0, 'discount': 0, 'repair_sales': 0,
            'tax': 0, 'total_amount': 0, 'repair_facilitator_amount': 0,
        })
        summary['repair_invoice_count'] += 1
        for field in ('gross', 'discount', 'tax', 'total_amount'):
            summary[field] += row.get(field) or 0
        summary['repair_sales'] += row.get('amount') or 0
        summary['repair_facilitator_amount'] += row.get('repair_facilitator_amount') or 0
    repair_rows = list(repair_totals.values())
    for row in repair_rows:
        row['discount_percent'] = row['discount'] * 100 / row['gross'] if row['gross'] else None
    facilitator_definitions = FACILITATORS
    facilitator_rows = snapshot.get('facilitator_totals', [])

    stream = BytesIO()
    workbook = xlsxwriter.Workbook(stream, {'in_memory': True})
    heading = workbook.add_format({'bold': True, 'bg_color': '#244195', 'font_color': '#FFFFFF', 'text_wrap': True})
    cell = workbook.add_format({'text_wrap': True, 'valign': 'top'})
    money = workbook.add_format({'num_format': '#,##0;[Red](#,##0);0'})
    for title, definitions, data, money_fields in (
        ('عملکرد', performance_definitions, rows, {'target', 'actual', 'repair_sales', 'facilitator_cost'}),
        ('خلاصه تعمیرات', REPAIRS, repair_rows, {'gross', 'discount', 'repair_sales', 'tax', 'total_amount', 'repair_facilitator_amount'}),
        ('پورسانت آسان‌ساز', facilitator_definitions, facilitator_rows, {'sales', 'repairs', 'unassigned', 'amount'}),
    ):
        sheet = workbook.add_worksheet(title)
        sheet.right_to_left()
        sheet.merge_range(0, 0, 0, len(definitions)-1, title + ' · ماه ' + view['month'], heading)
        sheet.write_row(2, 0, [column[1] for column in definitions], heading)
        for index, row in enumerate(data, 3):
            for col, (field, _, _) in enumerate(definitions):
                sheet.write(index, col, row.get(field), money if field in money_fields else cell)
        sheet.freeze_panes(3, 1)
        sheet.autofilter(2, 0, 2 + len(data), len(definitions)-1)
        sheet.set_column(0, len(definitions)-1, 22)
        for col, (field, _, _) in enumerate(definitions):
            if field in ('customer', 'repair_description', 'repair_reason'):
                sheet.set_column(col, col, 38)

    guide = workbook.add_worksheet('راهنمای ستون‌ها')
    guide.right_to_left()
    guide.write_row(0, 0, ['برگه', 'ستون', 'توضیح'], heading)
    index = 1
    for sheet_name, definitions in (('عملکرد', performance_definitions), ('خلاصه تعمیرات', REPAIRS), ('پورسانت آسان‌ساز', FACILITATORS)):
        for _, label, description in definitions:
            guide.write_row(index, 0, [sheet_name, label, description], cell)
            index += 1
    guide.set_column(0, 1, 30)
    guide.set_column(2, 2, 85)
    workbook.close()
    return stream.getvalue()
