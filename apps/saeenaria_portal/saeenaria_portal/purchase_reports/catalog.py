"""Report fields and Persian labels derived from the supplied PurchaseOrder model."""

LABELS = {
    "StockTitle": "انبار", "Category": "دسته‌بندی", "ItemCode": "کد کالا", "ItemTitle": "نام کالا",
    "ReferenceCode": "کد مرجع", "ReferenceTitle": "نام کالای مرجع", "MismatchSide": "نوع مغایرت",
    "AverageMonthlyNetSales": "میانگین فروش خالص ماهانه", "ReferenceInventoryQty": "موجودی گروه مرجع",
    "ReferenceIncomingQty": "تعداد در راه", "ActiveMonthsRecent": "ماه‌های فعال اخیر",
    "OrderEligibility": "مجوز سفارش", "SuggestedOrderQty": "تعداد پیشنهادی سفارش",
    "OfficialPriceRial": "قیمت رسمی (ریال)", "SuggestedOrderValueRial": "ارزش سفارش (ریال)",
    "CoverageMonths": "پوشش موجودی (ماه)", "MaxAllowedCoverage": "حداکثر پوشش مجاز (ماه)",
    "SedimentReason": "علت رسوب", "IdealQty": "تعداد موجودی ایده‌آل", "IdealValueRial": "ارزش ایده‌آل (ریال)",
    "CurrentStock": "موجودی فعلی", "AverageMonthlySales": "میانگین فروش ماهانه",
    "CurrentItemStock": "موجودی فعلی کالا",
    "OfficialUnitPriceRial": "قیمت رسمی (ریال)", "ExcessInventoryQty": "تعداد مازاد",
    "ExcessInventoryValueRial": "ارزش مازاد (ریال)", "PreviousSaleJalali": "فروش پیش از پنجره تأیید",
    "OrderControl": "کنترل سفارش", "NetSalesQty12M": "فروش خالص ۱۲ماهه",
    "AverageInventoryQty12M": "متوسط موجودی ۱۲ماهه", "TurnoverRate": "گردش موجودی (مرتبه)",
    "InventoryDays": "روزهای موجودی", "TurnoverStatus": "وضعیت گردش", "ExcessValueRial": "ارزش مازاد (ریال)",
    "DormancyMonths": "ماه‌های رکود", "CustomerName": "مشتری", "ExpertGroup": "کارشناس",
    "CustomerTemperature": "وضعیت مشتری", "PurchasedItems": "کالاهای خریداری‌شده",
    "LastPurchaseDate": "آخرین خرید", "InvoiceCount": "تعداد فاکتور", "HistoricalNetQty": "تعداد خالص خرید",
    "HistoricalNetSalesRial": "خرید خالص (ریال)", "WeekStart": "ابتدای هفته", "NetQty": "تعداد خالص فروش",
    "NetSalesRial": "فروش خالص (ریال)",
}

COMMON = ["StockTitle", "Category", "ItemCode", "ItemTitle"]
IDEAL = COMMON + ["AverageMonthlyNetSales", "IdealQty", "OfficialPriceRial", "IdealValueRial"]
REPORTS = {
    "orders": {"title": "پیشنهاد سفارش خرید", "source": "sqlserver + portal", "fields": COMMON + [
        "AverageMonthlyNetSales", "ReferenceInventoryQty", "ReferenceIncomingQty", "ActiveMonthsRecent",
        "OrderEligibility", "SuggestedOrderQty", "OfficialPriceRial", "SuggestedOrderValueRial",
        "CoverageMonths", "MaxAllowedCoverage", "SedimentReason"]},
    "budget": {"title": "بودجه و موجودی ایده‌آل", "source": "sqlserver + portal", "fields": IDEAL},
    "ideal": {"title": "جزئیات موجودی ایده‌آل", "source": "sqlserver + portal", "fields": COMMON + ["CurrentItemStock"] + IDEAL[len(COMMON):]},
    "reconcile": {"title": "مغایرت و کالاهای نیازمند تکمیل", "source": "sqlserver + portal", "fields": ["MismatchSide", "ItemCode", "ItemTitle"]},
    "sediment": {"title": "کالاهای رسوبی", "source": "sqlserver + portal", "fields": COMMON + [
        "CurrentStock", "AverageMonthlySales", "CoverageMonths", "MaxAllowedCoverage", "ActiveMonthsRecent",
        "SedimentReason", "OfficialUnitPriceRial", "ExcessInventoryQty", "ExcessInventoryValueRial", "PreviousSaleJalali", "OrderControl"]},
    "targets": {"title": "مشتریان هدف کالاهای رسوبی", "source": "sqlserver + portal", "fields": [
        "StockTitle", "Category", "ReferenceCode", "ReferenceTitle", "CurrentStock", "ExcessValueRial",
        "DormancyMonths", "SedimentReason", "CustomerName", "ExpertGroup", "CustomerTemperature",
        "PurchasedItems", "LastPurchaseDate", "InvoiceCount", "HistoricalNetQty", "HistoricalNetSalesRial"]},
    "turnover": {"title": "گردش موجودی", "source": "sqlserver + portal", "fields": IDEAL + [
        "NetSalesQty12M", "AverageInventoryQty12M", "TurnoverRate", "InventoryDays", "TurnoverStatus"]},
    "weekly": {"title": "فروش هفتگی کالاهای رسوبی", "source": "sqlserver + portal", "fields": [
        "WeekStart", "StockTitle", "Category", "ExpertGroup", "CustomerName", "ReferenceCode", "ReferenceTitle", "NetQty", "NetSalesRial"]},
}

# Each metric is calculated over the whole filtered dataset, before pagination.
METRICS = {
    "orders": [("References", "تعداد کالای مرجع", "references", None), ("NeedsOrder", "کالای نیازمند سفارش", "positive", "SuggestedOrderQty"), ("OrderValue", "ارزش سفارش (ریال)", "sum", "SuggestedOrderValueRial"), ("MissingPrices", "قیمت رسمی ناموجود", "missing", "OfficialPriceRial")],
    "budget": [("Items", "تعداد ردیف کالا و انبار", "count", None), ("IdealQty", "تعداد ایده‌آل", "sum", "IdealQty"), ("IdealValue", "بودجه ایده‌آل (ریال)", "sum", "IdealValueRial"), ("MissingPrices", "قیمت رسمی ناموجود", "missing", "OfficialPriceRial")],
    "ideal": [("IdealValue", "ارزش ایده‌آل (ریال)", "sum", "IdealValueRial"), ("MissingPrices", "قیمت رسمی ناموجود", "missing", "OfficialPriceRial")],
    "reconcile": [("Pending", "نیازمند تکمیل اطلاعات", "side", "نیازمند تکمیل اطلاعات"), ("Portal", "فقط در پورتال", "side", "فقط در پورتال"), ("Sepidar", "فقط در سپیدار", "side", "فقط در سپیدار")],
    "sediment": [("Items", "تعداد ردیف رسوبی", "count", None), ("ExcessValue", "ارزش مازاد (ریال)", "sum", "ExcessInventoryValueRial")],
    "targets": [("Customers", "مشتری یکتا", "distinct", "CustomerId"), ("ExcessValue", "ارزش مازاد بدون تکرار مشتری (ریال)", "excess", "ExcessValueRial")],
    "turnover": [("Rate", "گردش کل (مرتبه)", "rate", None), ("Days", "روزهای موجودی کل", "days", None)],
    "weekly": [("Qty", "تعداد خالص فروش", "sum", "NetQty"), ("Sales", "فروش خالص (ریال)", "sum", "NetSalesRial"), ("Customers", "مشتری یکتا", "distinct", "CustomerId")],
}
