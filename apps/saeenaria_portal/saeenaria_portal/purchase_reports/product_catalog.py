"""Portal-owned enrichment; Sepidar is the read-only authority for item identity."""
import json

import frappe
from frappe.utils import now_datetime, cint
from .calculations import key, text
from .sources import connection, credentials, rows, QUERIES

DT = 'Portal Product Catalog'
SETTINGS = 'Portal Product Catalog Settings'
FIELDS = ['name', 'item_code', 'item_title', 'category', 'reference_code', 'review_status', 'order_control', 'orderable', 'notes', 'source_present', 'needs_completion', 'source_conflict', 'source_titles', 'is_planned', 'modified']


def active():
    return bool(frappe.db.get_single_value(SETTINGS, 'initialized'))


def can_edit():
    from saeenaria_portal.permissions import admin, managed_domains, roles
    from .workflow import owner
    user = frappe.session.user
    if user == 'Guest':
        return False
    return admin(user) or 'Company Director' in roles(user) or (frappe.conf.get('purchase_order_domain') or 'inventory') in managed_domains(user) or user == owner()


def require_edit():
    if not can_edit():
        frappe.throw('تکمیل اطلاعات کالا فقط برای مسئول موجودی و مدیر مجاز است', frappe.PermissionError)


def source_index(items):
    result = {}
    for row in items:
        code = text(row.get('ItemCode'))
        if not code:
            continue
        k = key(code)
        if k not in result:
            result[k] = {**row, 'titles': [text(row.get('ItemTitle'))], 'conflict': False}
        else:
            result[k]['titles'].append(text(row.get('ItemTitle')))
            result[k]['conflict'] = True
    if not result:
        frappe.throw('فهرست سپیدار خالی است؛ همگام‌سازی اعمال نشد')
    return result


def read_items():
    with connection('sqlserver', credentials()) as conn:
        return rows(conn, QUERIES['SepidarItems']['sql'])


def mapping_rows():
    records = frappe.get_all(DT, fields=FIELDS, order_by='item_code', limit_page_length=0)
    return [{'کد کالا': r.item_code, 'نام کالا': r.item_title, 'دسته‌بندی اختصاصی': r.category,
             'کد مرجع دستی': r.reference_code, 'کد مرجع مؤثر': r.reference_code,
             'وضعیت بررسی': r.review_status, 'کنترل سفارش': r.order_control,
             'کالای سفارش‌پذیر': r.orderable, 'توضیحات': r.notes,
             'CatalogPending': bool(r.needs_completion or r.source_conflict), 'CatalogPlanned':bool(r.is_planned), 'CatalogSourcePresent': bool(r.source_present)} for r in records]


def insert_many(records):
    if not records:
        return
    stamp = now_datetime()
    columns = ['name','owner','creation','modified','modified_by','docstatus','idx','item_code','item_title','category','reference_code','review_status','order_control','orderable','notes','source_present','needs_completion','source_updated_at','source_conflict','source_titles','is_planned']
    values = []
    for r in records:
        values.append([r['item_code'], frappe.session.user, stamp, stamp, frappe.session.user, 0, 0,
                       r['item_code'], r.get('item_title'), r.get('category'), r.get('reference_code'),
                       r.get('review_status') or 'نیازمند بررسی', r.get('order_control') or 'خودکار',
                       r.get('orderable'), r.get('notes'), r.get('source_present', 1), r.get('needs_completion', 1), stamp, r.get('source_conflict',0), r.get('source_titles'), r.get('is_planned',0)])
    frappe.db.bulk_insert(DT, fields=columns, values=values, chunk_size=500)


def sync_items(items=None):
    """Internal worker API. Full source read must succeed before any local changes."""
    if not active():
        return {'initialized': False}
    items = read_items() if items is None else items
    source = source_index(items)
    with frappe.cache.lock('product-catalog-sync:'+frappe.local.site, timeout=300):
        existing = {key(r.item_code): r for r in frappe.get_all(DT, fields=['name','item_code','item_title','source_present','source_conflict','source_titles','is_planned'], limit_page_length=0)}
        fresh = [dict(item_code=text(r['ItemCode']), item_title=text(r['ItemTitle']) if not r['conflict'] else 'کد تکراری در سپیدار — نیازمند اصلاح',source_conflict=int(r['conflict']),source_titles=' / '.join(r['titles'])) for k,r in source.items() if k not in existing]
        insert_many(fresh)
        updated = 0
        for k, old in existing.items():
            present = k in source
            title = text(source[k]['ItemTitle']) if present and not source[k]['conflict'] else old.item_title
            conflict = int(source[k]['conflict']) if present else old.source_conflict
            titles = ' / '.join(source[k]['titles']) if present else old.source_titles
            planned = int(bool(old.is_planned) and not present)
            if title != old.item_title or bool(old.source_present) != present or conflict!=old.source_conflict or titles!=old.source_titles or planned!=old.is_planned:
                # Enrichment columns are deliberately absent from this update.
                frappe.db.set_value(DT, old.name, {'item_title': title, 'source_present': int(present), 'source_updated_at': now_datetime(), 'source_conflict':conflict,'source_titles':titles,'is_planned':planned})
                updated += 1
        result = {'added': len(fresh), 'source_updated': updated, 'source_items': len(source),'conflicts':sum(r['conflict'] for r in source.values())}
        frappe.db.set_single_value(SETTINGS, {'last_sync': now_datetime(), 'last_result': json.dumps(result)})
        return result


def initialize(items=None):
    from saeenaria_portal.permissions import admin
    if not admin(frappe.session.user):
        frappe.throw('راه‌اندازی اولیه فقط برای مدیر سامانه است', frappe.PermissionError)
    if active():
        return sync_items(items)
    items=read_items() if items is None else items
    source=source_index(items)
    with frappe.cache.lock('product-catalog-sync:'+frappe.local.site,timeout=300):
        if active():return {'initialized':True}
        if frappe.db.count(DT):
            frappe.throw('فهرست موجود است؛ برای جلوگیری از بازنویسی، راه‌اندازی متوقف شد')
        insert_many([dict(item_code=text(row['ItemCode']),item_title=text(row['ItemTitle']),
            source_present=1,needs_completion=1,source_conflict=int(row['conflict']),source_titles=' / '.join(row['titles']))
            for row in source.values()])
        frappe.db.set_single_value(SETTINGS,{'initialized':1,'last_sync':now_datetime(),'last_result':'راه‌اندازی مستقیم از سپیدار'})
    return {'catalog_items':len(source)}


def auto_sync():
    if active():
        frappe.enqueue('saeenaria_portal.purchase_reports.product_catalog.sync_worker',queue='long',timeout=600,job_id='product-catalog:'+frappe.local.site,deduplicate=True)


def sync_worker():
    try:
        result = sync_items()
        frappe.db.commit()
        return result
    except Exception:
        frappe.db.rollback()
        frappe.log_error('Product catalog sync failed; existing catalog preserved', 'Product catalog synchronization')
        raise


@frappe.whitelist(methods=['POST'])
def refresh():
    require_edit()
    auto_sync()
    return {'queued': True}


@frappe.whitelist()
def listing(search='', status='all', page=1):
    from .service import require_access
    require_access()
    page = max(1,cint(page))
    filters = {'needs_completion': 1} if status == 'pending' else {'source_present': 0,'is_planned':0} if status == 'missing' else {'is_planned':1} if status=='planned' else {'review_status':'تأیید شده'} if status=='reviewed' else {}
    if status=='issues':
        filters={'name':['in',frappe.get_all(DT,or_filters={'needs_completion':1,'source_conflict':1},pluck='name',limit_page_length=0)+frappe.get_all(DT,filters={'source_present':0,'is_planned':0},pluck='name',limit_page_length=0)]}
    if status=='new':filters={'needs_completion':1,'reference_code':['is','not set']}
    if status=='pending':
        filters={}
        filters['name']=['in',frappe.get_all(DT,or_filters={'needs_completion':1,'source_conflict':1},pluck='name',limit_page_length=0)]
    or_filters = {field: ['like','%'+text(search)[:100]+'%'] for field in ['item_code','item_title']} if text(search) else None
    matched = frappe.get_all(DT,filters=filters,or_filters=or_filters,fields=[{'COUNT':'name','as':'matches'}])[0].matches
    pages = max(1,(matched+49)//50)
    page = min(page,pages)
    records = frappe.get_list(DT,filters=filters,or_filters=or_filters,fields=FIELDS,order_by='needs_completion desc,item_code',start=(page-1)*50,page_length=50,ignore_permissions=True)
    return {'rows': records, 'has_next': page<pages, 'page':page,'pages':pages,'matched':matched,'row_start':(page-1)*50+1 if matched else 0,'row_end':min(page*50,matched), 'pending': len(frappe.get_all(DT,or_filters={'needs_completion':1,'source_conflict':1},pluck='name',limit_page_length=0)), 'new':frappe.db.count(DT,{'needs_completion':1,'reference_code':['is','not set']}), 'total': frappe.db.count(DT), 'last_sync': frappe.db.get_single_value(SETTINGS,'last_sync'), 'can_edit': can_edit(),
            'categories': sorted({r.category for r in frappe.get_all(DT,fields=['category'],distinct=True) if r.category})}


@frappe.whitelist()
def references(search=''):
    from .service import require_access
    require_access()
    if len(text(search)) < 2:
        return []
    return frappe.get_all(DT,filters={'needs_completion':0,'source_conflict':0},or_filters={'item_code':['like','%'+text(search)[:100]+'%'],'item_title':['like','%'+text(search)[:100]+'%']},fields=['item_code','item_title','reference_code','is_planned'],limit_page_length=25)


@frappe.whitelist(methods=['POST'])
def save(name, category, reference_code, order_control='خودکار', notes='', expected_modified=None, review_status='تأیید شده'):
    require_edit()
    category, reference_code = text(category), text(reference_code)
    if not category or len(category)>140 or not reference_code or len(reference_code)>100 or any(ord(c)<32 or c in '<>' for c in reference_code) or order_control not in ['خودکار','ممنوع دستی','مجاز دستی'] or review_status not in ['تأیید شده','نیازمند بررسی','غیرفعال']:
        frappe.throw('گروه، کد مرجع و وضعیت معتبر لازم است')
    with frappe.cache.lock('product-catalog-sync:'+frappe.local.site, timeout=60):
        doc = frappe.get_doc(DT,name)
        if str(doc.modified) != str(expected_modified):
            frappe.throw('کالا تغییر کرده؛ فهرست را تازه کنید',frappe.TimestampMismatchError)
        target = frappe.db.get_value(DT,{'item_code':reference_code},['name','item_code','reference_code','source_present','needs_completion','source_conflict'],as_dict=True)
        if not target:
            # This is an orderable brand reference, not a fictitious Sepidar item.
            target_doc = frappe.get_doc(dict(doctype=DT,item_code=reference_code,item_title='مرجع سفارش برند — '+reference_code,category=category,reference_code=reference_code,review_status=review_status,order_control=order_control,source_present=0,is_planned=1,needs_completion=0,source_conflict=0,notes='مرجع سفارش ثبت‌شده در پورتال؛ هنوز در سپیدار تعریف نشده است.'))
            target_doc.insert(ignore_permissions=True,ignore_links=True,set_name=reference_code)
            target = frappe._dict(name=target_doc.name,item_code=target_doc.item_code,reference_code=target_doc.reference_code,needs_completion=0,source_conflict=0)
        if target.source_conflict and target.name != doc.name:
            frappe.throw('کد مرجع انتخاب‌شده در سپیدار تکراری است؛ یک مرجع بدون تعارض انتخاب کنید')
        if target.name != doc.name and (target.needs_completion or key(target.reference_code)!=key(target.item_code)):
            frappe.throw('مرجع را از کالاهای تکمیل‌شده و مرجع اصلی انتخاب کنید؛ زنجیره مرجع مجاز نیست')
        if target.name != doc.name and frappe.db.exists(DT,{'reference_code':doc.item_code,'name':['!=',doc.name]}):
            frappe.throw('این کالا مرجع کالاهای دیگر است؛ ابتدا مرجع کالاهای وابسته را اصلاح کنید تا زنجیره مرجع ایجاد نشود')
        doc.update({'category': category, 'reference_code':target.item_code,'order_control':order_control,'notes':text(notes)[:2000],'review_status':review_status,'needs_completion':0})
        doc.save(ignore_permissions=True)
        frappe.db.commit()
    from .service import _enqueue
    from .workflow import enqueue_daily
    _enqueue()
    enqueue_daily()
    return {'saved': True}
