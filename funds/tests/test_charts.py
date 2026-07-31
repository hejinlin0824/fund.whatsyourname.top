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
