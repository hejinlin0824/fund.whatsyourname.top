from datetime import date
from decimal import Decimal
from django.test import TestCase
from accounts.models import User
from funds.models import Fund, Tag, DailyRecord


class FundModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", "u@e.com", "x")

    def test_create_fund(self):
        f = Fund.objects.create(
            user=self.user, name="A基金", market="CN", confirm_delay=1,
            invest_amount=5, invest_frequency="DAILY", start_date=date(2026, 6, 1),
            start_total=10, fund_type="INDEX", risk_level=3, currency="CNY",
        )
        self.assertEqual(f.pending_label(), "10.00（待确认 5.00）")

    def test_is_dca_day_daily_weekday(self):
        f = Fund.objects.create(user=self.user, name="A", market="CN", confirm_delay=1,
            invest_amount=5, invest_frequency="DAILY", start_date=date(2026, 6, 1), start_total=10)
        self.assertTrue(f.is_dca_day(date(2026, 6, 1)))   # 周一
        self.assertFalse(f.is_dca_day(date(2026, 6, 6)))  # 周六

    def test_is_dca_day_weekly(self):
        f = Fund.objects.create(user=self.user, name="C", market="CN", confirm_delay=1,
            invest_amount=50, invest_frequency="WEEKLY", invest_weekday=2,  # 周三
            start_date=date(2026, 6, 1), start_total=0)
        self.assertTrue(f.is_dca_day(date(2026, 6, 3)))   # 周三
        self.assertFalse(f.is_dca_day(date(2026, 6, 4)))  # 周四

    def test_dca_invest_active(self):
        f = Fund.objects.create(user=self.user, name="A", market="CN", confirm_delay=1,
            invest_amount=5, invest_frequency="DAILY", start_date=date(2026, 6, 1), start_total=0)
        self.assertEqual(f.dca_invest_for(date(2026, 6, 3)), Decimal("5"))   # 工作日
        self.assertEqual(f.dca_invest_for(date(2026, 6, 6)), Decimal("0"))   # 周末

    def test_dca_invest_stopped_after_end_date(self):
        f = Fund.objects.create(user=self.user, name="A", market="CN", confirm_delay=1,
            invest_amount=5, invest_frequency="DAILY", start_date=date(2026, 6, 1), start_total=0,
            is_active=False, end_date=date(2026, 6, 5))
        self.assertEqual(f.dca_invest_for(date(2026, 6, 3)), Decimal("5"))   # 停投前
        self.assertEqual(f.dca_invest_for(date(2026, 6, 10)), Decimal("0"))  # 停投后 → 0

    def test_dca_invest_cleared_is_zero(self):
        f = Fund.objects.create(user=self.user, name="A", market="CN", confirm_delay=1,
            invest_amount=5, invest_frequency="DAILY", start_date=date(2026, 6, 1), start_total=0,
            is_cleared=True)
        self.assertEqual(f.dca_invest_for(date(2026, 6, 3)), Decimal("0"))   # 清仓 → 0

    def test_effective_invested_with_and_without_fee(self):
        f = Fund.objects.create(user=self.user, name="A", market="CN", confirm_delay=1,
            invest_amount=10, invest_frequency="DAILY", start_date=date(2026, 6, 1), start_total=0,
            fee_rate=Decimal("0.12"))
        self.assertEqual(f.effective_invested(Decimal("10")), Decimal("9.99"))   # 10×0.9988→9.99
        f2 = Fund.objects.create(user=self.user, name="B", market="CN", confirm_delay=1,
            invest_amount=10, invest_frequency="DAILY", start_date=date(2026, 6, 1), start_total=0)
        self.assertEqual(f2.effective_invested(Decimal("10")), Decimal("10.00"))  # 无费率


class DailyRecordTest(FundModelTest):
    def test_unique_fund_date(self):
        f = Fund.objects.create(user=self.user, name="A", market="CN", confirm_delay=1,
            invest_amount=5, invest_frequency="DAILY", start_date=date(2026, 6, 1), start_total=10)
        DailyRecord.objects.create(fund=f, date=date(2026, 6, 2), profit=0.84, invested=5, has_trade=True)
        with self.assertRaises(Exception):
            DailyRecord.objects.create(fund=f, date=date(2026, 6, 2), profit=1, invested=5, has_trade=True)
