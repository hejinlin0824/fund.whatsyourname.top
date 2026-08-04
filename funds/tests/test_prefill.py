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

    def test_invested_defaults_to_dca_for_no_trade_placeholder(self):
        """finalize 占位(has_trade=False, invested=0)不应盖掉定投额度默认值。

        之前「有占位记录就用记录里的 0」导致日历里每天投入都显示成 0；
        修复后只有真实交易(has_trade=True)记录才沿用其投入额，否则按定投日给默认额度。
        """
        DailyRecord.objects.create(fund=self.f, date=date(2026, 7, 3),  # 周五 = DCA 日
                                   invested=0, profit=0, has_trade=False)
        r = self.client.get(reverse("daily-entry"), {"date": "2026-07-03"})
        self.assertEqual(r.context["formset"][0].initial["invested"], Decimal("100"))
