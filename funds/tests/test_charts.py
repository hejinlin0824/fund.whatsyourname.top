from datetime import date
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from accounts.models import User
from funds.models import Fund, DailyRecord, FundNav


class ChartEndpointTest(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username="ch", password="p", email="ch@e.com")
        self.client.force_login(self.u)
        self.f = Fund.objects.create(user=self.u, name="T", code="000001", market="CN",
                                     invest_amount=Decimal("100"), fee_rate=Decimal("0"),
                                     start_date=date(2026, 7, 1), start_total=Decimal("0"))
        FundNav.objects.create(code="000001", date=date(2026, 7, 1), unit_nav=Decimal("1.0"))
        FundNav.objects.create(code="000001", date=date(2026, 7, 2), unit_nav=Decimal("1.1"))
        DailyRecord.objects.create(fund=self.f, date=date(2026, 7, 1), invested=100,
                                   profit=0, total=100, has_trade=True)
        DailyRecord.objects.create(fund=self.f, date=date(2026, 7, 2), invested=0,
                                   profit=10, total=110, has_trade=True)

    def test_fund_detail_data_has_curve(self):
        r = self.client.get(reverse("fund-detail-data", args=[self.f.id]))
        self.assertEqual(r.status_code, 200)
        curve = r.json()["curve"]
        self.assertGreater(len(curve["nav"]), 0)
        self.assertEqual(len(curve["nav"]), len(curve["avg_cost"]))

    def test_portfolio_data_has_cost(self):
        r = self.client.get(reverse("portfolio-data"))
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("cost", data)
        self.assertEqual(len(data["cost"]), len(data["value"]))

    def test_calendar_heatmap_scales_with_magnitude(self):
        """当日盈亏幅度越大格子填色越深(热力图)；0 盈亏无填充。"""
        DailyRecord.objects.create(fund=self.f, date=date(2026, 7, 3), invested=0,
                                   profit=2, total=112, has_trade=True)   # 小幅盈利
        # 7-01 profit=0、7-02 profit=10(当月最大)、7-03 profit=2
        r = self.client.get(reverse("calendar"), {"year": 2026, "month": 7})
        cells = {c["date"]: c for week in r.context["weeks"] for c in week if c}

        def _alpha(bg):
            return float(bg.split(",")[-1].rstrip(")"))

        bg_big = cells[date(2026, 7, 2)]["bg"]    # +10
        bg_small = cells[date(2026, 7, 3)]["bg"]  # +2
        bg_zero = cells[date(2026, 7, 1)]["bg"]   # 0
        self.assertIn("220,38,38", bg_big)        # 盈利=红
        self.assertGreater(_alpha(bg_big), _alpha(bg_small))   # 幅度大→更深
        self.assertAlmostEqual(_alpha(bg_big), 0.57)           # 当月最大 = 封顶
        self.assertEqual(bg_zero, "")              # 0 盈亏不填色
