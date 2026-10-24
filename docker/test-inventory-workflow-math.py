from datetime import date
from decimal import Decimal
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'apps'/'saeenaria_portal'))
from saeenaria_portal.purchase_reports import workflow_math as m


class InventoryPolicy(unittest.TestCase):
    def test_persian_month_and_saturday_week(self):
        self.assertEqual(m.previous_week(date(2026,10,19)),(date(2026,10,10),date(2026,10,16)))
        self.assertEqual(m.previous_month(date(2026,10,19)),(date(2026,8,23),date(2026,9,22)))
        self.assertEqual(len(m.month_ends(date(2026,9,22))),12)

    def test_resolved_denominator_status_reason_and_distinct(self):
        deals=[dict(source_id='1',state=2,lost_at='2026-10-12',won_at='2026-10-01',reason='نبود کالا'),
               dict(source_id='2',state=1,won_at='2026-10-13',lost_at='2026-10-01',reason='نبود کالا'),
               dict(source_id='3',state=0,won_at='2026-10-13',lost_at='2026-10-13',reason='نبود کالا'),
               dict(source_id='4',state=2,lost_at='2026-10-14',reason='نداشتن بودجه کافی'),
               dict(source_id='5',state=2,lost_at='2026-10-17',reason='نبود کالا')]
        result=m.weekly_rate(deals+[deals[0]],date(2026,10,10),date(2026,10,16))
        self.assertEqual(result['evidence']['denominator'],3)
        self.assertEqual(result['evidence']['numerator'],1)
        self.assertEqual(result['value'],Decimal(100)/3)

    def test_no_resolved_request_is_missing(self):
        r=m.weekly_rate([],date(2026,10,10),date(2026,10,16))
        self.assertIsNone(r['value']);self.assertEqual(r['status'],'Missing')

    def test_six_groups_money_basis_full_stagnant_not_excess(self):
        inventory=[dict(ItemCode='A',StockId=1,Quantity=10,UnitPrice=100),dict(ItemCode='B',StockId=1,Quantity=5,UnitPrice=200),dict(ItemCode='C',StockId=1,Quantity=-4,UnitPrice=100)]
        mapping=[dict(ItemCode='A',EffectiveReference='A',Category='گردبر'),dict(ItemCode='B',EffectiveReference='B',Category='انواع مته')]
        values,groups,orders=m.aggregate_finance(inventory,mapping,[],[dict(ItemCode='A',StockId=1)],date(2026,10,19))
        self.assertEqual(values[0]['value'],2000)
        self.assertEqual(values[1]['value'],1000)
        bits=next(r for r in groups if r['code']=='bits')
        self.assertEqual(bits['inventory_toman'],200)
        self.assertEqual(bits['stagnant_toman'],100)
        self.assertEqual(values[0]['evidence']['negative_stock_rows'],1)

    def test_missing_price_is_disclosed_and_basis_not_cost(self):
        values,_,_=m.aggregate_finance([dict(ItemCode='A',StockId=1,Quantity=10,UnitPrice=None)],[],[],[],date(2026,10,19))
        self.assertEqual(values[0]['status'],'Missing');self.assertIsNone(values[0]['value'])
        self.assertEqual(values[0]['evidence']['missing_prices'],1)
        self.assertIn('فروش',m.BASIS)

    def test_forecast_requires_complete_prior_baseline(self):
        self.assertIsNone(m.forecast_accuracy({},dict(bits=100))['value'])
        forecast={k:100 for k in m.GROUPS};actual={k:80 for k in m.GROUPS}
        self.assertEqual(m.forecast_accuracy(forecast,actual)['value'],75)
        self.assertIsNone(m.forecast_accuracy(forecast,{k:0 for k in m.GROUPS})['value'])
        self.assertEqual(m.forecast_accuracy(forecast,{k:1 for k in m.GROUPS})['value'],0)

    def test_urgency_uses_configured_lead_and_no_order_for_similar(self):
        base=dict(ItemCode='A',EffectiveReference='A',StockId=None,ItemTitle='کالا',Category='انواع دریل',SuggestedOrderQty=3,OfficialPriceRial=100,AverageMonthlyNetSales=10,ReferenceInventoryQty=0,LeadMonths=2)
        similar=dict(base,ItemCode='B')
        _,groups,urgency=m.aggregate_finance([],[],[base,similar],[],date(2026,10,19))
        self.assertEqual(len(urgency),1);self.assertEqual(urgency[0]['priority'],'فوری')
        self.assertEqual(urgency[0]['lead_days'],60);self.assertEqual(urgency[0]['order_date'],'2026-10-19')
        self.assertEqual(next(r for r in groups if r['code']=='drills')['need_toman'],30)


if __name__=='__main__':unittest.main()
