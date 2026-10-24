"""Machine-calculated inventory outputs are information, not employee work."""
AUTO_CODES={'cancel','capital','slow','turnover','cash'}

def automatic_template(name):
    return name in {'INVPLAN-'+code for code in AUTO_CODES}

def automatic_action(key):
    return automatic_template((key or '').rsplit(':',1)[0])

def automatic_source(doc):
    if doc.get('is_demo'):return False
    if doc.doctype=='Portal Metric Value':return (doc.get('source') or '').startswith('پایش خودکار موجودی / ')
    if doc.doctype=='Portal Report':return bool(doc.get('inventory_snapshot'))
    if doc.doctype=='Portal Action':return automatic_action(doc.get('schedule_key'))
    return False

def automatic_review(review):
    import frappe
    if review.source_type not in ('Portal Action','Portal Metric Value','Portal Report'):return False
    if not frappe.db.exists(review.source_type,review.source_name):return False
    return automatic_source(frappe.get_doc(review.source_type,review.source_name))

def retire_automatic_work():
    import frappe
    from saeenaria_portal.reviews import save_review
    counts={'templates_disabled':0,'open_actions_archived':0,'pending_reviews_archived':0}
    for code in AUTO_CODES:
        name='INVPLAN-'+code
        if frappe.db.exists('Portal Template',name):
            d=frappe.get_doc('Portal Template',name)
            if d.enabled:d.enabled=0;d.save(ignore_permissions=True);counts['templates_disabled']+=1
    for name in frappe.get_all('Portal Action',filters={'is_demo':0,'status':['not in',['Completed','Cancelled']]},pluck='name'):
        d=frappe.get_doc('Portal Action',name)
        if not automatic_source(d):continue
        d.status='Cancelled';d.obstacle='محاسبه و دریافت خودکار است؛ تکلیف انسانی و تأیید لازم ندارد';d.save(ignore_permissions=True)
        d.add_comment('Info','حذف از تکالیف انسانی طبق درخواست مدیریت؛ سابقه حفظ شد');counts['open_actions_archived']+=1
    for row in frappe.get_all('Portal Activity Review',filters={'status':['in',['Pending','Returned']]},fields=['name','source_type','source_name']):
        if not automatic_review(row):continue
        d=frappe.get_doc('Portal Activity Review',row.name);d.status='Cancelled';d.review_note='خروجی خودکار؛ از گردش تأیید انسانی خارج شد';save_review(d)
        d.add_comment('Info','خروج از صف بررسی خودکار؛ تأیید انسانی ثبت نشد و سوابق حفظ شدند');counts['pending_reviews_archived']+=1
    return counts
