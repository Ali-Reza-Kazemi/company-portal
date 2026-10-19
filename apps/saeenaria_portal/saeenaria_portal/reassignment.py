"""Scoped, previewed reassignment; completed work and employee memberships stay intact."""
import hashlib
import json
import frappe
from frappe.utils import cint
from saeenaria_portal.permissions import manage_people,managed_domains,can_domain,roles


def allowed_domains():
    user=frappe.session.user
    if user=='Guest':frappe.throw('ورود لازم است',frappe.PermissionError)
    domains=frappe.get_all('Portal Domain',fields=['name','title'])
    if manage_people(user):return domains
    permitted=managed_domains(user)
    result=[d for d in domains if d.name in permitted]
    if not result:frappe.throw('انتقال وظایف فقط برای مدیر یا منابع انسانی مجاز است',frappe.PermissionError)
    return result

@frappe.whitelist()
def options():
    domains=allowed_domains()
    users=frappe.get_all('User',filters={'name':['not in',['Guest','Administrator']],'user_type':'System User'},fields=['name','full_name','enabled'],order_by='full_name asc',limit_page_length=0)
    return {'domains':domains,'users':users}


def plan(source,target,domain=None,external=0):
    domains=[d.name for d in allowed_domains()]
    if domain:
        if domain not in domains:frappe.throw('حوزه مجاز نیست',frappe.PermissionError)
        domains=[domain]
    if source==target:frappe.throw('مسئول قبلی و جدید باید متفاوت باشند')
    target_user=frappe.db.get_value('User',target,['enabled','user_type','full_name'],as_dict=True)
    if target in ('Guest','Administrator') or not target_user or not target_user.enabled or target_user.user_type!='System User':frappe.throw('مسئول جدید باید حساب فعال سامانه داشته باشد')
    if not (roles(target)&{'Portal Contributor','Domain Officer','Company Director','System Manager','Portal Administrator'}):frappe.throw('مسئول جدید هنوز دسترسی پایه پورتال ندارد')
    rows=[]
    for dt in ['Portal Template','Portal Action']:
        filters={'responsible':source,'domain':['in',domains]}
        if dt=='Portal Action':filters['status']=['not in',['Completed','Cancelled']]
        fields=['name','title','domain','modified']+(['enabled'] if dt=='Portal Template' else ['status','is_demo'])
        docs=frappe.get_all(dt,filters=filters,fields=fields,order_by='name asc',limit_page_length=1001)
        if len(docs)>1000:frappe.throw('حجم زیاد است؛ هر حوزه را جدا منتقل کنید')
        for row in docs:
            row['doctype']=dt;row['external']=not can_domain(target,row.domain,write=True)
            row['eligible']=not row.external or bool(cint(external));rows.append(row)
    payload={'source':source,'target':target,'domain':domain,'external':cint(external),'rows':[dict(r) for r in rows]}
    token=hashlib.sha256(frappe.as_json(payload).encode()).hexdigest()
    return rows,token

@frappe.whitelist()
def preview(source,target,domain=None,external=0):
    rows,token=plan(source,target,domain,external)
    return {'rows':rows,'token':token}

@frappe.whitelist(methods=['POST'])
def transfer(source,target,selected,token,domain=None,external=0):
    selected=frappe.parse_json(selected)
    if not isinstance(selected,list) or not selected:frappe.throw('حداقل یک وظیفه انتخاب کنید')
    rows,current_token=plan(source,target,domain,external)
    if current_token!=token:frappe.throw('وظایف یا دسترسی‌ها تغییر کرده‌اند؛ دوباره پیش‌نمایش بگیرید',frappe.TimestampMismatchError)
    available={r.doctype+':'+r.name:r for r in rows}
    if len(set(selected))!=len(selected) or any(key not in available or not available[key].eligible for key in selected):frappe.throw('انتخاب وظایف معتبر نیست',frappe.PermissionError)
    counts={'templates':0,'actions':0}
    frappe.db.savepoint('bulk_reassign')
    try:
        for key in sorted(selected):
            row=available[key]
            # Lock each selected record; compare again after taking the lock.
            modified=frappe.db.get_value(row.doctype,row.name,'modified',for_update=True)
            if str(modified)!=str(row.modified):frappe.throw('یکی از وظایف تغییر کرده است؛ پیش‌نمایش را تکرار کنید',frappe.TimestampMismatchError)
            doc=frappe.get_doc(row.doctype,row.name)
            if doc.responsible!=source:frappe.throw('مسئول وظیفه تغییر کرده است')
            changes=[['responsible',source,target]]
            values={'responsible':target}
            if row.doctype=='Portal Template':
                values['responsible_name']=frappe.db.get_value('User',target,'full_name')
                values['allow_external_responsible']=int(row.external)
                if cint(doc.allow_external_responsible)!=int(row.external):changes.append(['allow_external_responsible',doc.allow_external_responsible,int(row.external)])
                counts['templates']+=1
            else:counts['actions']+=1
            # Only assignment fields change; progress, results and due dates are preserved.
            doc.db_set(values,notify=True)
            if doc.doctype=="Portal Action":
                from saeenaria_portal.reviews import sync
                sync(doc)
            frappe.get_doc({'doctype':'Version','ref_doctype':row.doctype,'docname':row.name,'data':json.dumps({'changed':changes,'added':[],'removed':[],'row_changed':[]},ensure_ascii=False)}).insert(ignore_permissions=True)
    except Exception:
        frappe.db.rollback(save_point='bulk_reassign');raise
    return counts
