"""Only read from existing, privately configured connections."""

from datetime import timedelta

from saeenaria_portal.purchase_reports.sources import (
    QUERIES,
    connection,
    credentials,
    rows,
)


def load(start, end, previous_start):
    import jdatetime

    from .service import set_job_state

    jalali = jdatetime.date.fromgregorian(date=start)
    month = f"{jalali.year:04}-{jalali.month:02}"
    set_job_state(month, "running", "دریافت فاکتورها و کالاهای سپیدار")
    config = credentials()
    with connection("sqlserver", config) as conn:
        query = QUERIES["FactSales"]["sql"].rstrip(";")
        sales = rows(
            conn,
            "SELECT s.* FROM (" + query + ") s WHERE s.DocumentDate >= %s AND s.DocumentDate < %s",
            (previous_start, end + timedelta(days=1)),
        )
        first = rows(
            conn,
            "SELECT CustomerPartyRef customer_id,MIN(CAST(Date AS date)) first_date FROM SLS.Invoice WHERE State=1 AND Date<%s GROUP BY CustomerPartyRef",
            (end + timedelta(days=1),),
        )
        # A final invoice retains its quotation; the quotation's creator may
        # be the Didar salesperson even when the invoice creator is accounting.
        quotation_creators = rows(
            conn,
            "SELECT i.InvoiceId, i.QuotationRef, q.QuotationId, q.Number QuotationNumber, u.UserName FROM SLS.Invoice i "
            "LEFT JOIN SLS.Quotation q ON q.QuotationId=i.QuotationRef "
            "LEFT JOIN FMK.[User] u ON u.UserID=q.Creator "
            "WHERE i.State=1 AND i.Date>=%s AND i.Date<%s",
            (previous_start, end + timedelta(days=1)),
        )
        sale_types = {}
        for kind, table, identity in [('Sale','Invoice','InvoiceId'),('Return','ReturnedInvoice','ReturnedInvoiceId')]:
            for record in rows(conn, f'SELECT i.{identity} document_id, t.Title title FROM SLS.{table} i '
                               'LEFT JOIN SLS.SaleType t ON t.SaleTypeId=i.SaleTypeRef '
                               'WHERE i.Date>=%s AND i.Date<%s', (previous_start,end+timedelta(days=1))):
                sale_types[kind+':'+str(record['document_id'])] = record['title']
    quotation_by_invoice = {str(r['InvoiceId']): r for r in quotation_creators}
    for row in sales:
        row['SaleTypeTitle'] = sale_types.get(str(row['DocumentType'])+':'+str(row['DocumentId']))
        if row['DocumentType'] == 'Sale':
            quote = quotation_by_invoice.get(str(row['DocumentId']), {})
            row['QuotationStatus'] = ('present' if quote.get('QuotationId') else
                                      'missing' if quote and not quote.get('QuotationRef') else 'unresolved')
            row['QuotationNumber'] = quote.get('QuotationNumber')
    import frappe

    from .didar import Client, DidarError

    key = frappe.get_single("Portal Sales Settings").get_password(
        "didar_api_key", raise_exception=False
    )
    metadata = {"source": "didar-api", "available": False, "message": "کلید API دیدار ثبت نشده است"}
    deals, activities, sellers = [], [], {}
    if key:
        try:
            client = Client(
                key, progress=lambda message: set_job_state(month, "running", message)
            )
            deals, activities, sellers, pipelines, directory = client.load(start, end)
            customer_catalog = client.enrich_customer_channels(deals)
            email_to_seller = directory.pop("emails", {})
            creator_by_invoice = {
                str(r["InvoiceId"]): email_to_seller.get(
                    str(r.get("UserName") or "").strip().casefold()
                )
                for r in quotation_creators
            }
            for row in sales:
                if row["DocumentType"] == "Sale":
                    row["QuotationCreatorSeller"] = creator_by_invoice.get(
                        str(row["DocumentId"])
                    )
            from .service import folder
            for deal in deals:
                deal['seller'] = directory['aliases'].get(deal.get('seller'), deal.get('seller'))
            document_count = client.enrich_documents(deals, sales, folder() / 'document-cache.json')
            metadata = {
                "document_details_count": document_count,
                "customer_catalog": customer_catalog,
                "source": "didar-api",
                "available": True,
                "pipelines": pipelines,
                "seller_choices": directory["choices"],
                "seller_aliases": directory["aliases"],
                "inactive_sellers": directory["inactive"],
            }
        except DidarError:
            # Never replace a successful report with incomplete CRM after a source outage.
            raise
    return (
        sales,
        deals,
        activities,
        {str(r["customer_id"]): r["first_date"] for r in first},
        metadata,
        sellers,
    )


def quotation_creators_for_export(invoices):
    """Read linked quotation authors in batches, including for older snapshots."""
    ids = sorted({int(row['key'].split(':', 1)[1]) for row in invoices
                  if row['key'].startswith('Sale:')})
    result = {}
    if not ids:
        return result
    with connection('sqlserver', credentials()) as conn:
        for offset in range(0, len(ids), 500):
            batch = ids[offset:offset + 500]
            records = rows(conn,
                'SELECT i.InvoiceId, i.QuotationRef, q.QuotationId, u.Name creator_name, u.UserName creator_username '
                'FROM SLS.Invoice i LEFT JOIN SLS.Quotation q ON q.QuotationId=i.QuotationRef '
                'LEFT JOIN FMK.[User] u ON u.UserID=q.Creator WHERE i.InvoiceId IN ('
                + ','.join(['%s'] * len(batch)) + ')', tuple(batch))
            for record in records:
                name = str(record.get('creator_name') or '').strip() or str(record.get('creator_username') or '').strip()
                result['Sale:' + str(record['InvoiceId'])] = name or (
                    'بدون پیش‌فاکتور سپیدار' if not record.get('QuotationRef') else 'نام ثبت‌کننده در دسترس نیست')
    return result


def invoice_creator(document_type, document_id):
    """Read actual document and linked quotation creators as distinct identities."""
    tables = {'Sale': ('SLS.Invoice', 'InvoiceId'), 'Return': ('SLS.ReturnedInvoice', 'ReturnedInvoiceId')}
    if document_type not in tables:
        return None
    table, column = tables[document_type]
    quotation_fields = ', q.QuotationId quotation_id, qu.Name quotation_creator_name, qu.UserName quotation_creator_username' if document_type == 'Sale' else ''
    quotation_join = ' LEFT JOIN SLS.Quotation q ON q.QuotationId=i.QuotationRef LEFT JOIN FMK.[User] qu ON qu.UserID=q.Creator ' if document_type == 'Sale' else ''
    with connection('sqlserver', credentials()) as conn:
        result = rows(conn, f'SELECT u.Name creator_name, u.UserName creator_username{quotation_fields} FROM {table} i '
                      f'LEFT JOIN FMK.[User] u ON u.UserID=i.Creator {quotation_join} WHERE i.{column}=%s', (document_id,))
    return result[0] if result else None
