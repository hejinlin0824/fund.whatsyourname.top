from datetime import date
from decimal import Decimal
from django.test import TestCase
from accounts.models import User
from funds.models import Fund, DailyRecord, FundNav
from funds.nav import fund_dca_curve, estimate_profit


class NavTest(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username="n", password="p", email="n@e.com")
        self.f = Fund.objects.create(user=self.u, name="测试", code="000001", market="CN",
                                     invest_amount=Decimal("100"), fee_rate=Decimal("0"),
                                     start_date=date(2026, 7, 1), start_total=Decimal("0"))
        for d, nv in [(date(2026, 7, 1), 1.0), (date(2026, 7, 2), 1.1), (date(2026, 7, 3), 1.0)]:
            FundNav.objects.create(code="000001", date=d, unit_nav=Decimal(str(nv)))
        DailyRecord.objects.create(fund=self.f, date=date(2026, 7, 1), invested=100,
                                   profit=0, total=100, has_trade=True)
        DailyRecord.objects.create(fund=self.f, date=date(2026, 7, 2), invested=100,
                                   profit=10, total=210, has_trade=True)
        DailyRecord.objects.create(fund=self.f, date=date(2026, 7, 3), invested=0,
                                   profit=Decimal("-19.09"), total=Decimal("190.91"), has_trade=True)

    def test_curve_shares_and_avg(self):
        pts = fund_dca_curve(self.f)
        self.assertEqual(len(pts), 3)
        self.assertAlmostEqual(pts[0]["shares"], 100.0, places=1)
        self.assertAlmostEqual(pts[0]["avg_cost"], 1.0, places=2)

    def test_curve_est_profit(self):
        pts = fund_dca_curve(self.f)
        self.assertAlmostEqual(pts[1]["est_profit"], 10.0, places=1)      # 100份×(1.1−1.0)
        self.assertAlmostEqual(pts[2]["est_profit"], -19.09, places=1)    # 190.9份×(1.0−1.1)

    def test_estimate_profit(self):
        self.assertAlmostEqual(estimate_profit(self.f, date(2026, 7, 2)), 10.0, places=1)
        self.assertIsNone(estimate_profit(self.f, date(2026, 7, 1)))      # 首日无前日净值

    def test_no_nav(self):
        f2 = Fund.objects.create(user=self.u, name="无净值", code="999999", market="CN",
                                 invest_amount=Decimal("100"), start_date=date(2026, 7, 1),
                                 start_total=Decimal("0"))
        self.assertEqual(fund_dca_curve(f2), [])
        self.assertIsNone(estimate_profit(f2, date(2026, 7, 2)))
