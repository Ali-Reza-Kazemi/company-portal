import frappe
from frappe.utils import getdate


def ratio(numerator, denominator, percent=True):
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator * (100 if percent else 1)

def forecast_error(forecast, actual):
    if len(forecast) != len(actual) or any(v is None for v in [*forecast, *actual]):
        return None
    return ratio(sum(abs(f-a) for f,a in zip(forecast, actual)),sum(actual))

def signal(actual, target, direction, status, metric):
    if status == "Missing" or actual is None:
        return "Missing"
    if target is None:
        return "No Target"
    if status == "Provisional":
        return "Provisional"
    if not metric.thresholds_configured:
        return "No Thresholds"
    if direction == "Higher":
        return "Green" if actual >= metric.green_threshold else "Red" if actual <= metric.red_threshold else "Amber"
    return "Green" if actual <= metric.green_threshold else "Red" if actual >= metric.red_threshold else "Amber"

@frappe.whitelist()
def overview(domain=None, start=None, end=None, is_demo=0):
    filters = {"is_demo": int(is_demo or 0)}
    if domain: filters["domain"] = domain
    if start: filters["period_start"] = [">=", getdate(start)]
    if end: filters["period_end"] = ["<=", getdate(end)]
    rows = frappe.get_list("Portal Metric Value", filters=filters, fields=["*"], order_by="period_end desc",limit_page_length=500)
    output = []
    for row in rows:
        metric = frappe.get_doc("Portal Metric", row.metric)
        metric.check_permission("read")
        actual = None if row.data_status == "Missing" else row.actual
        target = row.target if row.has_target else None
        previous = frappe.get_list("Portal Metric Value", filters={"metric":row.metric,"period_end":["<",row.period_start],"is_demo":row.is_demo},fields=["actual","data_status"],order_by="period_end desc",limit_page_length=1)
        prior = previous[0].actual if previous and previous[0].data_status != "Missing" else None
        output.append(dict(name=row.name,title=metric.title,domain=row.domain,unit=metric.unit,actual=actual,target=target,
            change=None if actual is None or prior is None else actual-prior,
            signal=signal(actual,target,metric.direction,row.data_status,metric),data_status=row.data_status,
            source=row.source or metric.source,updated_at=row.source_updated_at,period_start=row.period_start,period_end=row.period_end))
    return output
