"""Parameter-bound reads against schema inspected on the actual Sepidar/CRM sources."""
from datetime import timedelta
from .sources import connection, credentials, rows, QUERIES
from .workflow_math import month_ends


def balance_sql(dates, priced=False):
    values = ",".join("(CONVERT(date,%s))" for _ in dates)
    sql = """WITH D(SnapshotDate) AS (SELECT x.d FROM (VALUES """ + values + """) x(d)),
F AS (SELECT d.SnapshotDate,fy.FiscalYearId FROM D d OUTER APPLY
 (SELECT TOP(1) FiscalYearId FROM FMK.FiscalYear WHERE StartDate<=d.SnapshotDate ORDER BY StartDate DESC) fy),
B AS (SELECT f.SnapshotDate,s.StockRef,s.ItemRef,MAX(s.UnitRef) UnitRef,COUNT(DISTINCT s.UnitRef) UnitCount,
 SUM(COALESCE(s.Quantity,COALESCE(s.InputQuantity,0)-COALESCE(s.OutputQuantity,0))) Qty
 FROM F f JOIN INV.ItemStockSummary s ON s.FiscalYearRef=f.FiscalYearId GROUP BY f.SnapshotDate,s.StockRef,s.ItemRef),
M AS (SELECT f.SnapshotDate,r.StockRef,i.ItemRef,i.Quantity Qty FROM F f
 JOIN INV.InventoryReceipt r ON r.FiscalYearRef=f.FiscalYearId AND r.Date>=DATEADD(day,1,f.SnapshotDate)
 JOIN INV.InventoryReceiptItem i ON i.InventoryReceiptRef=r.InventoryReceiptID
 UNION ALL SELECT f.SnapshotDate,r.StockRef,i.ItemRef,-i.Quantity FROM F f
 JOIN INV.InventoryDelivery r ON r.FiscalYearRef=f.FiscalYearId AND r.Date>=DATEADD(day,1,f.SnapshotDate)
 JOIN INV.InventoryDeliveryItem i ON i.InventoryDeliveryRef=r.InventoryDeliveryID),
A AS (SELECT SnapshotDate,StockRef,ItemRef,SUM(Qty) Qty FROM M GROUP BY SnapshotDate,StockRef,ItemRef)
SELECT b.SnapshotDate,b.StockRef StockId,st.Title StockTitle,it.Code ItemCode,it.Title ItemTitle,
 b.Qty-COALESCE(a.Qty,0) ClosingQty,b.Qty-COALESCE(a.Qty,0) Quantity,b.UnitCount
"""
    if priced:
        sql += ",CASE WHEN b.UnitCount=1 THEN p.Fee END UnitPrice,p.Date PriceDate"
    sql += """ FROM B b LEFT JOIN A a ON a.SnapshotDate=b.SnapshotDate AND a.StockRef=b.StockRef AND a.ItemRef=b.ItemRef
 JOIN INV.Item it ON it.ItemID=b.ItemRef JOIN INV.Stock st ON st.StockID=b.StockRef """
    if priced:
        sql += """ OUTER APPLY (SELECT TOP(1) pi.Fee,pn.Date FROM SLS.PriceNoteItem pi JOIN SLS.PriceNote pn
 ON pn.PriceNoteID=pi.PriceNoteRef WHERE pi.ItemRef=b.ItemRef AND pi.UnitRef=b.UnitRef AND pi.SaleTypeRef=8
 AND pn.Date<DATEADD(day,1,b.SnapshotDate)
 ORDER BY CASE WHEN pi.CustomerGroupingRef IS NULL AND pi.TracingRef IS NULL THEN 0 ELSE 1 END,
 pn.Date DESC,pi.PriceNoteItemID DESC) p """
    return sql


def load_inventory(end, sales_start):
    cfg = credentials()
    with connection("sqlserver", cfg) as conn:
        inventory = rows(conn, balance_sql([end], priced=True), (end,))
        snapshots = month_ends(end)
        monthly = rows(conn, balance_sql(snapshots), tuple(snapshots))
        sales_sql = QUERIES["FactSales"]["sql"].rstrip(";")
        sales = rows(conn, "SELECT src.ItemCode,src.StockId,src.StockTitle,src.Quantity,src.DocumentDate,src.JalaliYear,src.JalaliMonthNumber FROM (" + sales_sql + ") src WHERE src.DocumentDate >= %s AND src.DocumentDate < %s", (sales_start, end + timedelta(days=1)))
        items = rows(conn, QUERIES["SepidarItems"]["sql"])
    return inventory, sales, monthly, items


def crm_deals(start, end):
    cfg = credentials()
    # The real schema has one tenant; retain the tenant key in the stable source ID.
    with connection("mysql", cfg) as conn:
        columns={r["COLUMN_NAME"] for r in rows(conn,"SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA='analytics' AND TABLE_NAME='Deal'")}
        title_column=next((name for name in ("Deal_Title","Deal_Name") if name in columns),None)
        title_sql="d."+title_column if title_column else "NULL"
        data = rows(conn, """SELECT CONCAT(d.Bussines_Key,':',d.Deal_Key) source_id,d.Deal_Stats state,
 d.Deal_Won_Date_Time won_at,d.Deal_Loss_Date_Time lost_at,d.Deal_Lost_Reason_Title reason,
 d.Deal_Register_Date_Time registered_at,"""+title_sql+""" deal_title,
 d.Deal_Code deal_code,d.Deal_Owner_Name salesperson,
 COALESCE((SELECT c.Company_Title FROM analytics.Company c WHERE c.Company_Key=d.Deal_Company_Key AND c.Company_Bussines_Key=d.Bussines_Key LIMIT 1),
 (SELECT p.Person_Name FROM analytics.Person p WHERE p.Person_Key=d.Deal_Person_Key AND p.Person_Bussines_Key=d.Bussines_Key LIMIT 1)) customer,
 (SELECT GROUP_CONCAT(DISTINCT p.DealProduct_Product_Title ORDER BY p.DealProduct_Product_Title SEPARATOR '، ')
 FROM analytics.DealProduct p WHERE p.Deal_Key=d.Deal_Key AND p.Bussines_Key=d.Bussines_Key) products
 FROM analytics.Deal d WHERE (d.Deal_Stats=1 AND d.Deal_Won_Date_Time >= %s AND d.Deal_Won_Date_Time < %s)
 OR (d.Deal_Stats=2 AND d.Deal_Loss_Date_Time >= %s AND d.Deal_Loss_Date_Time < %s)""",
                    (start, end + timedelta(days=1), start, end + timedelta(days=1)))
        metadata = rows(conn, "SELECT MAX(Deal_Last_Update_Date_Time) last_record_update,COUNT(*) row_count,COUNT(DISTINCT Bussines_Key) tenants FROM analytics.Deal")
    return data, metadata


def receipt_options(code, since):
    codes = code if isinstance(code, list) else [code]
    placeholders = ",".join(["%s"] * len(codes))
    with connection("sqlserver", credentials()) as conn:
        return rows(conn, """SELECT TOP(100) i.InventoryReceiptItemID receipt_item,r.Date receipt_date,r.StockRef stock,
 it.Code item_code,i.Quantity quantity FROM INV.InventoryReceipt r
 JOIN INV.InventoryReceiptItem i ON i.InventoryReceiptRef=r.InventoryReceiptID
 JOIN INV.Item it ON it.ItemID=i.ItemRef WHERE it.Code IN ("""+placeholders+""") AND r.Date>=%s AND r.IsReturn=0 AND i.Quantity>0
 ORDER BY r.Date DESC,i.InventoryReceiptItemID DESC""", (*codes, str(since)[:10]))


def item_exists(code):
    with connection("sqlserver", credentials()) as conn:
        return bool(rows(conn,"SELECT TOP(1) ItemID FROM INV.Item WHERE Code=%s",(code,)))


def current_book(code, stock):
    with connection("sqlserver", credentials()) as conn:
        return rows(conn, """SELECT SUM(COALESCE(s.Quantity,COALESCE(s.InputQuantity,0)-COALESCE(s.OutputQuantity,0))) quantity
 FROM INV.ItemStockSummary s JOIN INV.Item it ON it.ItemID=s.ItemRef
 WHERE it.Code=%s AND s.StockRef=%s AND s.FiscalYearRef=(SELECT TOP(1) FiscalYearId FROM FMK.FiscalYear
 WHERE StartDate<=GETDATE() ORDER BY StartDate DESC)""", (code, stock))
