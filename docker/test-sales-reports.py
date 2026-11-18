"""Sales arithmetic and official API contract regression fixtures; no real API calls."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "saeenaria_portal"))
from saeenaria_portal.sales_reports.calculations import (
    assignment_for,
    apply_targets,
    attribution_suggestions,
    calculate,
)
from saeenaria_portal.sales_reports.didar import Client, DidarError, local_time


class SalesTests(unittest.TestCase):
    def test_previous_month_unassigned_invoice_does_not_reduce_current_financial_coverage(self):
        self.config['invoices'].pop('Sale:2')
        result=self.run_report()
        self.assertEqual(result['unmapped_invoices'],0)
        self.assertTrue(all(row['financial_complete'] for row in result['rows']))
        self.config['invoices'].pop('Sale:1')
        result=self.run_report()
        self.assertEqual(result['unmapped_invoices'],1)
        self.assertTrue(all(not row['financial_complete'] for row in result['rows']))

    def test_minor_amount_tolerance_requires_same_products_quantities_and_components(self):
        from saeenaria_portal.sales_reports.matching import items_with_minor_rounding, minor_amount_difference
        from decimal import Decimal
        row=dict(ItemCode='A',Quantity=2,Fee=100000,GrossPrice=200000,Discount=0,Tax=20000)
        item=dict(ProductCode='A',Quantity=2,UnitPrice=100001,Price=200002,Discount=0,TaxPrice=20000)
        self.assertTrue(items_with_minor_rounding([row],[item]))
        for override in ({'Quantity':3},{'ProductCode':'B'},{'Discount':1},{'Price':201000}):
            self.assertFalse(items_with_minor_rounding([row],[{**item,**override}]))
        self.assertFalse(items_with_minor_rounding([row,row],[item]))
        self.assertTrue(minor_amount_difference(Decimal('1276176550'),Decimal('1276175066')))
        self.assertFalse(minor_amount_difference(Decimal('1276176550'),Decimal('1276166549')))

    def test_related_customer_is_checked_for_each_invoice_date(self):
        from saeenaria_portal.sales_reports.matching import related_customer_proposal
        invoice = dict(key='Sale:1',customer='شخص',date='2026-10-04',quotation_creator_seller='other')
        deal = dict(source_id='d',customer_ids=['company'],state=1,registered_at='2026-10-04',pipeline='فروش مستقیم',
                    customer_owners=[dict(customer_id='person',name='شخص',seller='s',active=True),dict(customer_id='company',name='شرکت اول',seller='s',active=True)])
        pipelines={'فروش مستقیم':'consumer'}
        proposal=related_customer_proposal(invoice,[deal],pipelines,{'s':'مسئول'})
        self.assertEqual(proposal['related_customer_name'],'شرکت اول')
        self.assertEqual(proposal['deal_ids'],[])
        moved={**deal,'customer_ids':['next'], 'registered_at':'2027-05-01', 'customer_owners':[deal['customer_owners'][0],dict(customer_id='next',name='شرکت دوم',seller='s2',active=True)]}
        self.assertEqual(related_customer_proposal({**invoice,'date':'2027-05-01'},[deal,moved],pipelines)['related_customer_name'],'شرکت دوم')
        self.assertIsNone(related_customer_proposal(invoice,[deal,{**moved,'registered_at':'2026-10-04'}],pipelines))
        self.assertIsNone(related_customer_proposal(invoice,[{**deal,'state':2}],pipelines))

    def test_excluded_customer_removes_sales_returns_crm_and_suggestions_until_restored(self):
        self.config['excluded_customers']={'1':dict(customer_name='نمونه',crm_ids=['crm1'])}
        deals=[dict(source_id='d1',customer_ids=['crm1'],seller='s1',pipeline='فروش مستقیم',state=1,registered_at='2026-10-24',won_at='2026-10-24')]
        result=self.run_report(deals)
        self.assertEqual(sum(r['actual'] for r in result['rows']),0)
        self.assertTrue(all(r['excluded'] for r in result['invoices']))
        self.assertEqual(result['unmapped_invoices'],0)
        self.assertEqual(result['unclassified_products'],[])
        self.assertTrue(all(r['invoice_count']==0 and r['new_customers']==0 and r['evidence']['won']==0 and r['evidence']['previous']==0 for r in result['rows']))
        self.assertFalse(attribution_suggestions([dict(key='Sale:9',customer='نمونه',excluded=True)], [{**deals[0],'customer_names':['نمونه']}]))
        self.config['excluded_customers']={}
        self.assertEqual(sum(r['actual'] for r in self.run_report(deals)['rows']),390)

    def test_manual_repair_excludes_all_lines_and_preserves_original_assignment(self):
        self.config['document_types']={'Sale:1':dict(type='repair',description='تعمیر موتور')}
        report=self.run_report()
        invoice=next(r for r in report['invoices'] if r['key']=='Sale:1')
        self.assertTrue(invoice['manual_repair'])
        self.assertEqual(invoice['channel'],'after_sales')
        self.assertEqual(invoice['repair_description'],'تعمیر موتور')
        self.assertEqual(report['rows'][0]['actual'],-90)
        self.assertEqual(self.config['invoices']['Sale:1']['channel'],'consumer')
        del self.config['document_types']['Sale:1']
        self.assertEqual(self.run_report()['rows'][0]['actual'],390)

    def test_no_quotation_blocks_proposals_and_inherited_customer_assignments(self):
        row=dict(DocumentType='Sale',DocumentId=9,CustomerId=1,DocumentDate='2026-10-26',QuotationStatus='missing')
        config=dict(customer_references={'1':dict(seller='s1',channel='consumer')})
        self.assertEqual(assignment_for(row,config),{})
        config['invoices']={'Sale:9':dict(seller='s1',channel='consumer',method='manual')}
        self.assertEqual(assignment_for(row,config)['seller'],'s1')
        invoice=dict(key='Sale:9',customer='نمونه',quotation_status='missing')
        deal=dict(source_id='d1',seller='s1',pipeline='فروش مستقیم',state=1,customer_names=['نمونه'])
        self.assertFalse(attribution_suggestions([invoice],[deal]))
        self.assertTrue(invoice['match_note'])
        self.assertIn('Sale:9',attribution_suggestions([{**invoice,'quotation_status':'present'}],[deal]))

    def test_reseller_tag_overrides_direct_sales_but_not_services(self):
        from saeenaria_portal.sales_reports.channels import deal_channel
        from saeenaria_portal.sales_reports.calculations import PIPELINES
        self.config['customer_catalog'] = [dict(id='c1', name='مشتری نمونه', reseller=True)]
        for r in self.rows:
            r['CustomerName'] = 'مشتری نمونه'
        report = self.run_report()
        self.assertEqual(next(r for r in report['rows'] if r['actual'])['channel'], 'reseller')
        self.assertTrue(all(r['channel']=='reseller' for r in report['invoices']))
        self.assertEqual(deal_channel(dict(pipeline='فروش مستقیم', customer_reseller=True), PIPELINES),'reseller')
        self.assertEqual(deal_channel(dict(pipeline='همکار و ابزار فروش', customer_reseller=False), PIPELINES),'reseller')
        self.assertEqual(deal_channel(dict(pipeline='خدمات پس از فروش', customer_reseller=True), PIPELINES),'after_sales')
        self.rows[0]['ItemTitle'] = 'kh تعمیرات'
        self.assertEqual(self.run_report()['invoices'][0]['channel'],'after_sales')

    def test_customer_segments_are_read_from_customer_not_deal_label(self):
        client = Client('fixture')
        client.request = lambda resource, body: ([dict(Id='group', Title='نوع مشتری', Segments=[dict(Id='reseller', Title='همکار/ابزار فروش')])]
            if resource == 'segments' else dict(TotalCount=1,List=[dict(Id='c1', DisplayName='نمونه', Segments=[dict(Id='reseller')])]))
        deals=[dict(customer_ids=['c1'], pipeline='فروش مستقیم'),dict(customer_ids=['c2'])]
        # Unknown customer detail must be read, not silently classified as untagged.
        deals.pop()
        catalog=client.enrich_customer_channels(deals)
        self.assertTrue(catalog[0]['reseller'])
        self.assertTrue(deals[0]['customer_reseller'])

    def test_document_match_resolves_customer_with_two_sales_channels(self):
        from saeenaria_portal.sales_reports.matching import document_matches
        invoice = dict(key='Sale:9', customer='خریدار', date='2026-10-26', quotation_creator_seller='s1', total_amount=220)
        sales = [dict(DocumentType='Sale', DocumentId=9, ItemCode='A', Quantity=2, Fee=100, GrossPrice=200, Discount=0, Tax=20)]
        item = dict(ProductCode='A', Quantity=2, UnitPrice=100, Price=200, Discount=0, TaxPrice=20)
        deal = dict(source_id='d1', state=1, pipeline='همکار و ابزار فروش', seller='s1', customer_names=['خریدار'], won_at='2026-10-26', items=[item], document_total=220)
        older = {**deal, 'source_id':'d2', 'pipeline':'فروش مستقیم', 'items':[{**item, 'Quantity':3}]}
        result = attribution_suggestions([invoice], [deal, older], sales=sales)
        self.assertEqual(result['Sale:9']['channel'], 'reseller')
        self.assertEqual(result['Sale:9']['deal_ids'], ['d1'])
        self.assertEqual(result['Sale:9']['confidence'], 'document')
        self.assertFalse(attribution_suggestions([invoice], [deal, {**deal, 'source_id':'duplicate'}], sales=sales))
        self.assertTrue(invoice['match_note'])
        self.assertFalse(document_matches([invoice], [{**deal, 'document_total':221}], sales, {'همکار و ابزار فروش':'reseller'})[0])
        self.assertFalse(document_matches([invoice], [{**deal, 'items':[item,item]}], sales, {'همکار و ابزار فروش':'reseller'})[0])
        self.assertFalse(attribution_suggestions([invoice], [{**deal, 'seller':'s2'}], sales=sales))
        grouped_sales = [{**sales[0], 'CustomerGroupId':7, 'CustomerGroupTitle':'گروه نمونه'}]
        names = {'s1':'ثبت‌کننده', 's2':'مسئول معامله', 's3':'مسئول گروه'}
        mapping = {'7':{'seller':'s3'}}
        proposal = attribution_suggestions([invoice], [{**deal, 'seller':'s2'}], sales=grouped_sales, sellers=names, group_sellers=mapping)['Sale:9']
        self.assertEqual(proposal['seller'], 's3')
        self.assertEqual(proposal['channel'], 'reseller')
        self.assertIn('گروه نمونه', proposal['reason'])
        self.assertIn('ثبت‌کننده', proposal['reason'])
        self.assertIn('مسئول معامله', proposal['reason'])
        for protected in ({'mapped':True}, {'excluded':True}, {'is_repair':True}, {'quotation_status':'missing'}):
            self.assertFalse(attribution_suggestions([{**invoice, **protected}], [{**deal, 'seller':'s2'}], sales=grouped_sales, sellers=names, group_sellers=mapping))
        self.assertFalse(attribution_suggestions([invoice], [{**deal,'seller':'s2'}, {**deal,'source_id':'duplicate'}], sales=grouped_sales, sellers=names, group_sellers=mapping))
        self.assertFalse(attribution_suggestions([invoice], [{**deal,'seller':'s2'}], sales=grouped_sales, sellers=names, group_sellers={}))
        self.assertFalse(attribution_suggestions([invoice], [{**deal, 'pipeline':'خدمات پس از فروش'}], sales=sales))
        second = {**invoice, 'key':'Sale:10'}
        self.assertFalse(attribution_suggestions([invoice, second], [deal], sales=sales + [{**sales[0], 'DocumentId':10}]))

    def test_detail_enrichment_scopes_requests_and_preserves_only_matching_fields(self):
        client = Client('fixture')
        deal = dict(source_id='d1', state=1, seller='s1', registered_at='2026-10-26')
        sales = [dict(DocumentType='Sale', DocumentId=1, DocumentDate='2026-10-26', QuotationCreatorSeller='s1')]
        calls = []
        def request(resource, body):
            calls.append(body)
            return dict(Id='d1', FinalAdjustmentPrice=100, Items=[dict(ProductCode='A', Quantity=1, Description='private')])
        client.request = request
        self.assertEqual(client.enrich_documents([deal, {**deal, 'source_id':'old', 'registered_at':'2025-01-01'}], sales), 1)
        self.assertEqual(calls, [{'Id':'d1'}])
        self.assertNotIn('Description', deal['items'][0])

    def test_bidi_marks_do_not_prevent_customer_match(self):
        invoice = dict(key="Sale:9", customer="\u202a\u202aتهران آریسمان", quotation_creator_seller="s1")
        deal = dict(source_id="d1", state=1, pipeline="فروش مستقیم", seller="s1", customer_names=["تهران آریسمان"])
        self.assertEqual(attribution_suggestions([invoice], [deal])["Sale:9"]["seller"], "s1")
        self.assertFalse(attribution_suggestions([{**invoice, "quotation_creator_seller": "s2"}], [deal]))
        self.assertFalse(attribution_suggestions([invoice], [deal, {**deal, "pipeline": "همکار و ابزار فروش"}]))
        self.assertFalse(attribution_suggestions([{**invoice, "customer": "تهران آریسمان شرق"}], [deal]))

    def test_company_prefix_requires_creator_and_unique_channel(self):
        invoice = dict(key="Sale:9", customer="شرکت سازه صنعت فرتاک", quotation_creator_seller="s1")
        deal = dict(source_id="d1", state=1, pipeline="فروش مستقیم", seller="s1", customer_names=["سازه صنعت فرتاک"])
        self.assertEqual(attribution_suggestions([invoice], [deal])["Sale:9"]["seller"], "s1")
        self.assertFalse(attribution_suggestions([{**invoice, "quotation_creator_seller": None}], [deal]))
        self.assertFalse(attribution_suggestions([{**invoice, "quotation_creator_seller": "s2"}], [deal]))
        self.assertFalse(attribution_suggestions([invoice], [deal, {**deal, "pipeline": "همکار و ابزار فروش"}]))
        self.assertFalse(attribution_suggestions([{**invoice, "customer": "شرکت فرتاک صنعت شریف"}], [deal]))

    def test_invoice_total_tax_additions_and_signed_returns(self):
        self.rows[0].update(Tax=18, Duty=2, Addition=5, NetPrice=205)
        self.rows[2].update(Tax=-9, Duty=-1, Addition=-2, NetPrice=-102)
        report = self.run_report()
        invoices = {r["key"]: r for r in report["invoices"]}
        self.assertEqual(invoices["Sale:1"]["amount"], 480)
        self.assertEqual(invoices["Sale:1"]["tax"], 20)
        self.assertEqual(invoices["Sale:1"]["total_amount"], 505)
        self.assertEqual(invoices["Return:1"]["total_amount"], -102)
        self.assertEqual(report["rows"][0]["actual"], 390)

    def test_customer_owner_fallback_requires_unique_contact_and_channel(self):
        invoice = dict(key="Sale:9", customer="مشتری نمونه")
        contact = dict(customer_id="c1", name="مشتری نمونه", seller="s2", active=True)
        deal = dict(source_id="d1", state=0, pipeline="فروش مستقیم", customer_owners=[contact])
        result = attribution_suggestions([invoice], [deal])
        self.assertEqual(result["Sale:9"]["seller"], "s2")
        self.assertFalse(attribution_suggestions([{**invoice, "mapped": True}], [deal]))
        self.assertFalse(attribution_suggestions([{**invoice, "is_repair": True}], [deal]))
        self.assertFalse(attribution_suggestions([{**invoice, "quotation_creator_seller": "s3"}], [deal]))
        duplicate = {**deal, "customer_owners": [{**contact, "customer_id": "c2"}]}
        self.assertFalse(attribution_suggestions([invoice], [deal, duplicate]))
        self.assertFalse(attribution_suggestions([invoice], [{**deal, "customer_owners": [{**contact, "active": False}]}]))

    def setUp(self):
        self.rows = [
            dict(
                DocumentType="Sale",
                DocumentId=1,
                DocumentItemId=1,
                DocumentNumber=11,
                DocumentDate="2026-10-24",
                CustomerId=1,
                ItemCode="A",
                Quantity=2,
                GrossPrice=200,
                Discount=20,
            ),
            dict(
                DocumentType="Sale",
                DocumentId=1,
                DocumentItemId=2,
                DocumentNumber=11,
                DocumentDate="2026-10-24",
                CustomerId=1,
                ItemCode="B",
                Quantity=3,
                GrossPrice=300,
                Discount=0,
            ),
            dict(
                DocumentType="Return",
                DocumentId=1,
                DocumentItemId=1,
                DocumentNumber=12,
                DocumentDate="2026-10-25",
                CustomerId=1,
                ItemCode="A",
                Quantity=-1,
                GrossPrice=-100,
                Discount=-10,
            ),
            dict(
                DocumentType="Sale",
                DocumentId=2,
                DocumentItemId=3,
                DocumentNumber=10,
                DocumentDate="2026-09-25",
                CustomerId=1,
                ItemCode="A",
                Quantity=1,
                GrossPrice=100,
                Discount=0,
            ),
        ]
        assignment = dict(seller="s1", channel="consumer")
        self.config = dict(
            invoices={k: assignment for k in ["Sale:1", "Return:1", "Sale:2"]},
            products={"A": "drill", "B": "insert"},
            targets=[
                dict(
                    month="1405-08",
                    period_start="2026-10-23",
                    seller="s1",
                    channel="consumer",
                    target=780,
                    discount_limit=3,
                )
            ],
        )

    def run_report(self, deals=None, activities=None):
        return calculate(
            self.rows,
            deals or [],
            activities or [],
            self.config,
            "2026-10-23",
            "2026-11-21",
            "2026-09-23",
            {"1": "2026-09-25"},
        )

    def test_accounting_returns_unique_invoice_and_weighted_discount(self):
        r = self.run_report()["rows"][0]
        self.assertEqual(r["actual"], 390)
        self.assertEqual(r["invoice_count"], 1)
        self.assertEqual(r["average_invoice"], 480)
        self.assertEqual(r["achievement"], 50)
        self.assertEqual(r["discount"], 4)
        self.assertEqual(r["discount_deviation"], 1)
        self.assertEqual(r["total_quantity"], 4)
        self.assertEqual(r["groups"]["drill"], 1)
        self.assertEqual(r["new_customers"], 0)
        self.assertEqual(r["retention"], 100)

    def test_repair_channel_is_independent_of_customer_sales_channel(self):
        self.rows[1]["ItemTitle"] = "دریل مگنت(kH)"
        result = self.run_report()
        invoices = {row["key"]: row for row in result["invoices"]}
        self.assertTrue(invoices["Sale:1"]["is_repair"])
        self.assertFalse(invoices["Return:1"]["is_repair"])
        self.assertEqual(invoices["Sale:1"]["channel"], "after_sales")
        self.assertIsNone(invoices["Sale:1"]["seller"])
        self.assertEqual(invoices["Sale:1"]["previous_sales_assignment"]["channel"], "consumer")
        self.assertIn("KH", invoices["Sale:1"]["repair_reason"])
        self.assertEqual(result["rows"][0]["actual"], -90)
        repair = {**invoices["Sale:1"], "mapped": False, "customer": "مشتری"}
        deal = dict(source_id="d1", customer_names=["مشتری"], seller="s1", pipeline="فروش مستقیم", state=1)
        self.assertEqual(attribution_suggestions([repair], [deal]), {})

    def test_linked_service_pipeline_does_not_classify_other_customer_invoices(self):
        self.config["invoices"]["Sale:1"] = dict(seller="s1", channel="consumer", deal_ids=["service"])
        deals = [dict(source_id="service", pipeline="خدمات پس از فروش", seller="s1", state=1)]
        result = self.run_report(deals=deals)
        invoices = {r["key"]:r for r in result["invoices"]}
        self.assertEqual(invoices["Sale:1"]["channel"], "after_sales")
        self.assertEqual(invoices["Sale:2"]["channel"], "consumer")
        self.assertFalse(invoices["Sale:2"]["is_repair"])

    def test_crm_does_not_count_as_invoice_and_deduplicates_activities(self):
        deals = [
            dict(
                source_id="d1",
                seller="s1",
                pipeline="فروش مستقیم",
                state=1,
                registered_at="2026-10-24",
                won_at="2026-10-25",
            ),
            dict(
                source_id="d2",
                seller="s1",
                pipeline="فروش مستقیم",
                state=2,
                registered_at="2026-10-24",
                lost_at="2026-10-25",
            ),
        ]
        activity = dict(source_id="d1", state=1, done_at="2026-10-24")
        r = self.run_report(deals, [activity, activity])["rows"][0]
        self.assertEqual(r["conversion"], 50)
        self.assertEqual(r["followup"], 50)
        self.assertEqual(r["invoice_count"], 1)

    def test_unmapped_financials_never_guessed_from_customer(self):
        self.config["invoices"] = {}
        report = self.run_report()
        self.assertEqual(report["unmapped_invoices"], 2)  # Only current-month sale and return.
        self.assertFalse(report["rows"][0]["financial_complete"])
        self.assertEqual(report["rows"][0]["actual"], 0)

    def test_unknown_product_and_excluded_service(self):
        self.config["products"] = {"A": "exclude"}
        report = self.run_report()
        self.assertEqual(report["unclassified_products"], ["B"])
        self.assertEqual(report["rows"][0]["total_quantity"], 3)
        self.assertEqual(report["rows"][0]["unclassified_quantity"], 3)

    def test_zero_denominators_and_duplicate_line(self):
        self.config["targets"][0]["target"] = 0
        r = self.run_report()["rows"][0]
        self.assertIsNone(r["achievement"])
        self.assertIsNone(r["conversion"])
        self.rows.append(self.rows[0])
        with self.assertRaises(ValueError):
            self.run_report()

    def test_timezone_boundary(self):
        self.assertTrue(local_time("2026-10-22T21:00:00Z").startswith("2026-10-23T00:30"))
        with self.assertRaises(DidarError):
            local_time("2026-10-22T21:00:00")

    def test_pagination_and_failure_are_not_partial_success(self):
        client = Client("fixture-key")
        calls = []

        def request(resource, body):
            calls.append(body["From"])
            return {"List": [{"Id": "a"}] if body["From"] == 0 else [{"Id": "b"}], "TotalCount": 2}

        client.request = request
        self.assertEqual(len(client.pages("deals", {})), 2)
        self.assertEqual(calls, [0, 1])
        client.request = lambda *args: {"List": [{"Id": "a"}], "TotalCount": 2}
        with self.assertRaises(DidarError):
            client.pages("deals", {})

    def test_no_redirect_or_key_in_error_message(self):
        class Response:
            status_code = 401

        class Session:
            def post(inner, url, **kwargs):
                self.assertEqual(url, "https://app.didar.me/api/deal/search_v2")
                self.assertFalse(kwargs["allow_redirects"])
                return Response()

        with self.assertRaises(DidarError) as raised:
            Client("secret-key", Session()).request("deals", {})
        self.assertNotIn("secret-key", str(raised.exception))

    def test_live_empty_activity_response(self):
        client = Client("fixture-key")
        client.request = lambda *args: {"List": None, "Total": 0}
        self.assertEqual(client.pages("activities", {"DealId": "empty"}), [])
        client.request = lambda *args: {"List": None, "Total": 10}
        with self.assertRaises(DidarError):
            client.pages("activities", {})

    def test_live_targets_without_source_refresh_and_alias_identity(self):
        rows = [dict(seller="membership", channel="consumer", actual=500, discount=8)]
        targets = [
            dict(
                seller="user",
                channel="consumer",
                period_start="2026-10-23",
                target=1000,
                discount_limit=5,
            ),
            dict(
                seller="other",
                channel="reseller",
                period_start="2026-10-23",
                target=2000,
                discount_limit=2,
            ),
        ]
        result = apply_targets(
            rows,
            targets,
            {"membership": "user"},
            "2026-10-23",
            {"user": "کارشناس"},
            {"خرید": "خرید"},
        )
        self.assertEqual(result[0]["achievement"], 50)
        self.assertEqual(result[0]["seller_name"], "کارشناس")
        self.assertEqual(result[0]["discount_deviation"], 3)
        self.assertEqual(result[1]["target"], 2000)
        self.assertIsNone(result[1]["actual"])

    def test_groups_follow_purchase_catalog_instead_of_fixed_groups(self):
        self.config["group_labels"] = {
            "پخ‌زن دستی": "پخ‌زن دستی",
            "قطعات یدکی دریل": "قطعات یدکی دریل",
        }
        self.config["products"] = {"A": "پخ‌زن دستی", "B": "قطعات یدکی دریل"}
        result = self.run_report()
        self.assertEqual(result["rows"][0]["groups"], {"پخ‌زن دستی": 1, "قطعات یدکی دریل": 3})
        self.assertNotIn("drill", result["group_labels"])

    def test_suggestions_require_unique_customer_owner_and_channel(self):
        invoice = dict(key="Sale:1", customer="شرکت یک", mapped=False)
        deal = dict(
            source_id="d1", customer_names=["شرکت یک"], seller="s1", pipeline="فروش مستقیم", state=1
        )
        self.assertEqual(attribution_suggestions([invoice], [deal])["Sale:1"]["seller"], "s1")
        other = {**deal, "source_id": "d2", "seller": "s2"}
        self.assertEqual(attribution_suggestions([invoice], [deal, other]), {})
        identified = {**invoice, "quotation_creator_seller": "s1"}
        proposal = attribution_suggestions([identified], [deal, other])["Sale:1"]
        self.assertEqual(proposal["seller"], "s1")
        self.assertIn("ایمیل ثبت‌کننده", proposal["reason"])
        self.assertEqual(
            attribution_suggestions(
                [{**invoice, "quotation_creator_seller": "s3"}], [deal, other]
            ),
            {},
        )
        self.assertEqual(attribution_suggestions([{**invoice, "mapped": True}], [deal]), {})

    def test_customer_change_uses_document_date_and_manual_correction_wins(self):
        row = dict(DocumentType="Sale", DocumentId=1, DocumentDate="2026-10-26", CustomerId=7)
        rules = [
            dict(customer_id="7", from_date="2026-10-01", seller="old", channel="consumer"),
            dict(customer_id="7", from_date="2026-10-25", seller="new", channel="reseller"),
        ]
        config = {"customer_rules": rules}
        self.assertEqual(assignment_for(row, config)["seller"], "new")

        self.assertEqual(
            assignment_for({**row, "DocumentDate": "2026-10-24"}, config)["seller"], "old"
        )
        config["invoices"] = {"Sale:1": dict(seller="fixed", channel="consumer", method="manual")}
        self.assertEqual(assignment_for(row, config)["seller"], "fixed")
        config["invoices"]["Sale:1"]["method"] = "suggestion"
        self.assertEqual(assignment_for(row, config)["seller"], "new")
        config["invoices"]["Sale:1"].pop("method")
        config["invoices"]["Sale:1"]["deal_ids"] = ["legacy-confirmed-deal"]
        self.assertEqual(assignment_for(row, config)["seller"], "new")


    def test_customer_reference_applies_to_unassigned_documents_only(self):
        row = dict(DocumentType="Sale", DocumentId=99, DocumentDate="2026-01-01", CustomerId=7)
        config = {"customer_references": {"7": dict(seller="default", channel="reseller")}}
        self.assertEqual(assignment_for(row, config)["seller"], "default")
        self.assertEqual(assignment_for({**row, "CustomerId": 8}, config), {})
        config["invoices"] = {"Sale:99": dict(seller="manual", channel="consumer")}
        self.assertEqual(assignment_for(row, config)["seller"], "manual")
        config["invoices"] = {}
        config["customer_rules"] = [dict(customer_id="7", from_date="2026-02-01", seller="dated", channel="consumer")]
        self.assertEqual(assignment_for({**row, "DocumentDate": "2026-03-01"}, config)["seller"], "dated")
        self.assertEqual(assignment_for(row, config)["seller"], "default")

    def test_activity_search_is_scoped_to_monthly_deals_not_account_wide(self):
        client = Client("fixture-key")
        client.request = lambda resource: (
            [{"Id": "p", "Title": "فروش مستقیم"}]
            if resource == "pipelines"
            else [
                {"Id": "member-1", "UserId": "s1", "DisplayName": "کارشناس نمونه"},
                {
                    "Id": "former-member",
                    "UserId": "former",
                    "DisplayName": "کارشناس سابق",
                    "IsDisabled": True,
                },
            ]
        )
        calls = []

        def pages(resource, body):
            if resource == "deals":
                return [
                    dict(
                        Id="new",
                        PipelineId="p",
                        OwnerId="s1",
                        Status="Pending",
                        Contact=dict(Id="contact-1", DisplayName="مشتری نمونه", OwnerId="member-1"),
                        RegisterTime="2026-10-22T21:00:00Z",
                    ),
                    dict(
                        Id="old",
                        PipelineId="p",
                        OwnerId="s1",
                        Status="Won",
                        RegisterTime="2025-01-01T00:00:00Z",
                        ChangeToWonTime="2026-10-24T00:00:00Z",
                    ),
                ]
            calls.append(body)
            self.assertEqual(body["DealId"], "new")
            self.assertEqual(body["FromDate"], "1800-01-01T00:00:00Z")
            return [dict(Id="a1", DealId="new", IsDone=True, DoneDate="2026-10-24T00:00:00Z")]

        client.pages = pages
        deals, activities, sellers, _, directory = client.load("2026-10-23", "2026-11-21")
        self.assertEqual(directory["choices"], {"s1": "کارشناس نمونه"})
        self.assertIn("former", directory["inactive"])
        self.assertNotIn("former", directory["choices"])
        self.assertEqual(directory["aliases"]["member-1"], "s1")
        self.assertEqual(sellers["s1"], "کارشناس نمونه")
        self.assertEqual(sellers["member-1"], "کارشناس نمونه")
        self.assertEqual(len(deals), 2)
        self.assertEqual(deals[0]["customer_owners"][0]["seller"], "s1")
        self.assertTrue(deals[0]["customer_owners"][0]["active"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(activities[0]["source_id"], "new")


if __name__ == "__main__":
    unittest.main()
