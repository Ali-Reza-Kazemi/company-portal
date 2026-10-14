"""Two-phase CSV import. Validation and insertion share the same document rules."""
import csv
import io
import frappe

FIELDS = {
 "Portal Action": {"title","domain","responsible","priority","start_date","due_date","status","progress","obstacle","result","is_demo","schedule_key"},
 "Portal Metric Value": {"domain","metric","period_start","period_end","data_status","actual","has_target","target","source","source_updated_at","is_demo"},
 "Portal Record": {"domain","title","record_type","external_id","record_date","period_start","period_end","responsible","status","channel","item_code","customer_code","service","quantity","amount","cost","planned_at","ordered_at","promised_at","actual_at","rating","details","baseline_snapshot","is_demo"},
}

@frappe.whitelist(methods=["POST"])
def import_csv(doctype, content, confirm=0):
    if doctype not in FIELDS:
        frappe.throw("نوع فایل پشتیبانی نمی‌شود")
    frappe.has_permission(doctype,"create",throw=True)
    if len(content.encode("utf-8")) > 1_000_000:
        frappe.throw("حداکثر حجم فایل یک مگابایت است")
    reader = csv.DictReader(io.StringIO(content.lstrip("\ufeff")))
    if not reader.fieldnames or set(reader.fieldnames) - FIELDS[doctype]:
        frappe.throw("نام ستون‌ها معتبر نیست؛ از قالب نمونه استفاده کنید")
    records = list(reader)
    if not records or len(records) > 200:
        frappe.throw("فایل باید بین یک تا دویست سطر داشته باشد")
    errors, docs, seen = [], [], set()
    frappe.db.savepoint("csv_preview")
    try:
        for number, row in enumerate(records,2):
            try:
                if None in row or any(v is None for v in row.values()):
                    raise ValueError("تعداد ستون‌های سطر با سرستون یکسان نیست")
                if doctype == "Portal Metric Value" and row.get("data_status") != "Missing" and not row.get("actual", "").strip():
                    raise ValueError("برای داده معتبر یا موقت مقدار واقعی لازم است")
                if doctype == "Portal Action":
                    # File must provide a stable, source-generated identifier.
                    if not row.get("schedule_key", "").strip():
                        raise ValueError("ستون schedule_key با شناسه یکتای منبع الزامی است")
                    row["schedule_key"] = "csv:" + row["schedule_key"]
                doc = frappe.get_doc({"doctype":doctype, **{k:v for k,v in row.items() if v != ""}})
                doc.insert()
                key = doc.get("dedup_key") or doc.get("schedule_key")
                if key in seen:
                    raise ValueError("سطر تکراری در فایل")
                seen.add(key)
                docs.append({"doctype":doctype, **{k:v for k,v in row.items() if v != ""}})
            except Exception as exc:
                errors.append({"row":number,"error":str(exc)[:400]})
    finally:
        frappe.db.rollback(save_point="csv_preview")
    if errors:
        return {"valid":False,"errors":errors,"created":0}
    if not int(confirm):
        return {"valid":True,"rows":len(records),"errors":[],"created":0,"preview":records[:10]}
    for values in docs:
        frappe.get_doc(values).insert()
    return {"valid":True,"rows":len(records),"created":len(docs),"errors":[]}
