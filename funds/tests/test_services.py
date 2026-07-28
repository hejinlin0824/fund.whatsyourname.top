from datetime import date
from decimal import Decimal
from django.test import TestCase
from accounts.models import User
from funds.models import Fund, DailyRecord
from funds import services as S


def _d(x):
    return Decimal(str(x))


class ServicesTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", "u@e.com", "x")
        self.fund = Fund.objects.create(
            user=self.user, name="A", market="CN", confirm_delay=1,
            invest_amount=5, invest_frequency="DAILY",
            start_date=date(2026, 6, 1), start_total=_d(10))

    def _seed(self):
        """6/1 基准 + 6/2,6/3 有盈亏。"""
        DailyRecord.objects.create(fund=self.fund, date=date(2026, 6, 1), invested=_d(5), has_trade=True)
        DailyRecord.objects.create(fund=self.fund, date=date(2026, 6, 2), profit=_d(0.84), invested=_d(5), has_trade=True)
        DailyRecord.objects.create(fund=self.fund, date=date(2026, 6, 3), profit=_d(1.20), invested=_d(5), has_trade=True)

    def test_compute_total(self):
        self.assertEqual(S.compute_total(_d(10), _d(0.84), _d(5)), _d("15.84"))
        self.assertEqual(S.compute_total(_d(10), None, _d(5)), _d("15"))   # 首日 profit 视为 0

    def test_pending_t_plus_1(self):
        self._seed()
        recs = list(self.fund.records.order_by("date"))
        # 6/2：T+1 待确认 = 当天 invested = 5
        self.assertEqual(S.compute_pending(recs, date(2026, 6, 2), 1), _d("5"))

    def test_pending_t_plus_2(self):
        self.fund.confirm_delay = 2
        self.fund.save()
        self._seed()
        recs = list(self.fund.records.order_by("date"))
        # 6/3：T+2 待确认 = 6/2 + 6/3 的 invested
        self.assertEqual(S.compute_pending(recs, date(2026, 6, 3), 2), _d("10"))

    def test_recompute_totals_matches_spec(self):
        self._seed()
        S.recompute_fund_totals(self.fund)
        recs = {r.date: r for r in self.fund.records.all()}
        self.assertEqual(recs[date(2026, 6, 1)].total, _d("10.00"))     # 起点
        self.assertEqual(recs[date(2026, 6, 1)].pending, _d("5.00"))
        self.assertEqual(recs[date(2026, 6, 2)].total, _d("15.84"))
        self.assertEqual(recs[date(2026, 6, 3)].total, _d("22.04"))

    def test_validate_ratio_ok_and_bad(self):
        ok, ratio = S.validate_ratio(_d(0.84), _d(10), _d("0.084"))
        self.assertTrue(ok)
        ok2, _ = S.validate_ratio(_d(0.84), _d(10), _d("0.05"))   # 实际 8.4%，给 5% 应不通过
        self.assertFalse(ok2)

    def test_validate_total(self):
        self._seed()
        S.recompute_fund_totals(self.fund)
        r = S.validate_total(self.fund, _d("22.04"))
        self.assertTrue(r["ok"])
        r2 = S.validate_total(self.fund, _d("99"))
        self.assertFalse(r2["ok"])


class BackfillTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", "u@e.com", "x")
        self.fund = Fund.objects.create(
            user=self.user, name="A", market="CN", confirm_delay=1,
            invest_amount=_d(5), invest_frequency="DAILY",
            start_date=date(2026, 6, 1), start_total=_d(10))

    def test_backfill_creates_slots(self):
        n = S.backfill_fund(self.fund, until=date(2026, 6, 5))   # 6/1..6/5 全工作日
        self.assertEqual(n, 5)
        recs = {r.date: r for r in self.fund.records.all()}
        for d in [date(2026, 6, 1), date(2026, 6, 2), date(2026, 6, 3),
                  date(2026, 6, 4), date(2026, 6, 5)]:
            self.assertTrue(recs[d].has_trade)
            self.assertEqual(recs[d].invested, _d(5))
            self.assertIsNone(recs[d].profit)        # 待补录

    def test_backfill_weekend_rest(self):
        S.backfill_fund(self.fund, until=date(2026, 6, 7))       # 6/6周六 6/7周日
        recs = {r.date: r for r in self.fund.records.all()}
        self.assertFalse(recs[date(2026, 6, 6)].has_trade)
        self.assertFalse(recs[date(2026, 6, 7)].has_trade)
        self.assertEqual(recs[date(2026, 6, 6)].invested, _d(0))

    def test_cascade_pending_makes_total_none(self):
        S.backfill_fund(self.fund, until=date(2026, 6, 3))
        recs = {r.date: r for r in self.fund.records.all()}
        self.assertEqual(recs[date(2026, 6, 1)].total, _d(10))   # 首日恒为 start_total
        self.assertIsNone(recs[date(2026, 6, 2)].total)          # 未补录 → None
        self.assertIsNone(recs[date(2026, 6, 3)].total)

    def test_fill_profit_computes_forward(self):
        S.backfill_fund(self.fund, until=date(2026, 6, 3))
        r = DailyRecord.objects.get(fund=self.fund, date=date(2026, 6, 2))
        r.profit = _d("0.84")
        r.save()
        S.recompute_fund_totals(self.fund)
        recs = {r.date: r for r in self.fund.records.all()}
        self.assertEqual(recs[date(2026, 6, 2)].total, _d("15.84"))
        self.assertIsNone(recs[date(2026, 6, 3)].total)          # 6/3 仍未补 → None

    def test_backfill_does_not_overwrite(self):
        S.backfill_fund(self.fund, until=date(2026, 6, 3))
        r = DailyRecord.objects.get(fund=self.fund, date=date(2026, 6, 2))
        r.profit = _d("0.84")
        r.save()
        n = S.backfill_fund(self.fund, until=date(2026, 6, 3))   # 再补齐，不应覆盖
        self.assertEqual(n, 0)
        r.refresh_from_db()
        self.assertEqual(r.profit, _d("0.84"))
