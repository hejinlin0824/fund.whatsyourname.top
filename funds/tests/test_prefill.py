from datetime import date
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from accounts.models import User
from funds.models import Fund, DailyRecord, FundNav


class PrefillTest(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username="pf", password="p", email="pf@e.com")
        self.client.force_login(self.u)
        self.f = Fund.objects.create(user=self.u, name="T", code="000010", market="CN",
                                     confirm_delay=1, invest_amount=Decimal("100"),
                                     fee_rate=Decimal("0"), start_date=date(2026, 7, 1),
                                     start_total=Decimal("0"))
        FundNav.objects.create(code="000010", date=date(2026, 7, 1), unit_nav=Decimal("1.0"))
        FundNav.objects.create(code="000010", date=date(2026, 7, 2), unit_nav=Decimal("1.1"))
        DailyRecord.objects.create(fund=self.f, date=date(2026, 7, 1), invested=100,
                                   profit=0, total=100, has_trade=True)
        DailyRecord.objects.create(fund=self.f, date=date(2026, 7, 2), invested=0,
                                   profit=None, has_trade=True)

    def test_profit_prefilled_with_estimate(self):
        r = self.client.get(reverse("daily-entry"), {"date": "2026-07-02"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "10.00")    # 100 份 × (1.1−1.0) = 10
        self.assertContains(r, "估算")      # 预填徽章
