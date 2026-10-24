import frappe
from saeenaria_portal.training import PREFIX
no_cache=1

def get_context(context):
    from saeenaria_portal.account_header import add_context
    add_context(context)
    if frappe.session.user=="Guest":
        frappe.local.flags.redirect_location="/login?redirect-to=/portal-training"
        raise frappe.Redirect
    context.no_cache=1
    from saeenaria_portal.user_names import display_name
    tasks=frappe.get_list("Portal Action",filters={"is_demo":1,"title":["like",PREFIX+"%"]},fields=["responsible","status"],limit_page_length=500)
    by_user={}
    for task in tasks:
        row=by_user.setdefault(task.responsible,dict(name=display_name(task.responsible),total=0,completed=0,active=0,pending=0))
        row["total"]+=1
        row["completed" if task.status=="Completed" else "pending" if task.status=="Open" else "active"]+=1
    context.employees=list(by_user.values())
    series=[]
    for metric in frappe.get_list("Portal Metric",filters={"title":["like",PREFIX+"%"]},fields=["name","title","unit"],limit_page_length=100):
        rows=frappe.get_list("Portal Metric Value",filters={"metric":metric.name,"is_demo":1},fields=["actual","target","period_start","period_end"],order_by="period_end asc",limit_page_length=100)
        maximum=max([v.actual for v in rows]+[v.target for v in rows]+[1])
        for row in rows:
            row["width"]=round(100*row.actual/maximum)
        series.append(dict(title=metric.title,unit=metric.unit,rows=rows))
    context.series=series
