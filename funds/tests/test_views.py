from datetime import date
from decimal import Decimal
from django.test import TestCase
from accounts.models import User
from funds.models import Fund, DailyRecord


class FundCrudTest(TestCase):
    def setUp(self):
        self.u = User.objects.create_user("u", "u@e.com", "pwd12345")
        self.client.login(username="u", password="pwd12345")

    def test_create_fund_via_post(self):
        resp = self.client.post("/funds/new/", {
            "name": "A基金", "code": "000001", "market": "CN", "confirm_delay": 1,
            "invest_amount": "5", "invest_frequency": "DAILY", "invest_weekday": 0,
            "start_date": "2026-06-01", "start_total": "10",
            "fund_type": "INDEX", "risk_level": 3, "currency": "CNY",
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self.u.funds.count(), 1)

    def test_edit_fund_via_post(self):
        f = Fund.objects.create(user=self.u, name="old", market="CN", confirm_delay=1,
            invest_amount=5, invest_frequency="DAILY", start_date="2026-06-01", start_total=10)
        resp = self.client.post(f"/funds/{f.pk}/edit/", {
            "name": "newname", "code": "", "market": "CN", "confirm_delay": 1,
            "invest_amount": "5", "invest_frequency": "DAILY", "invest_weekday": 0,
            "start_date": "2026-06-01", "start_total": "10",
            "fund_type": "INDEX", "risk_level": 3, "currency": "CNY",
        })
        self.assertEqual(resp.status_code, 302)
        f.refresh_from_db()
        self.assertEqual(f.name, "newname")

    def test_list_shows_own_funds_only(self):
        Fund.objects.create(user=self.u, name="mine", market="CN", confirm_delay=1,
            invest_amount=5, invest_frequency="DAILY", start_date="2026-06-01", start_total=10)
        other = User.objects.create_user("o", "o@e.com", "pwd12345")
        Fund.objects.create(user=other, name="ZZZnotmine", market="CN", confirm_delay=1,
            invest_amount=5, invest_frequency="DAILY", start_date="2026-06-01", start_total=10)
        resp = self.client.get("/funds/")
        self.assertContains(resp, "mine")
        self.assertNotContains(resp, "ZZZnotmine")

    def test_daily_entry_shows_stopped_not_cleared(self):
        Fund.objects.create(user=self.u, name="ZZstopped", market="CN", confirm_delay=1,
            invest_amount=5, invest_frequency="DAILY", start_date="2026-06-01", start_total=0,
            is_active=False, end_date="2026-06-05")
        Fund.objects.create(user=self.u, name="ZZcleared", market="CN", confirm_delay=1,
            invest_amount=5, invest_frequency="DAILY", start_date="2026-06-01", start_total=0,
            is_cleared=True)
        resp = self.client.get("/funds/daily/?date=2026-06-10")
        self.assertContains(resp, "ZZstopped")          # 停投仍持仓 → 显示
        self.assertNotContains(resp, "ZZcleared")       # 清仓 → 隐藏


class DailyEntryTest(FundCrudTest):
    """继承 FundCrudTest 的 login setUp，但不在 setUp 建基金（否则污染继承的 CRUD 断言）。"""

    def _make_fund(self):
        fund = Fund.objects.create(
            user=self.u, name="A", market="CN", confirm_delay=1,
            invest_amount=Decimal("5"), invest_frequency="DAILY",
            start_date=date(2026, 6, 1), start_total=Decimal("5"))
        DailyRecord.objects.create(fund=fund, date=date(2026, 6, 1),
                                   invested=Decimal("5"), profit=Decimal("0"))
        return fund

    def test_post_saves_profit_and_recomputes(self):
        fund = self._make_fund()
        resp = self.client.post("/funds/daily/?date=2026-06-02", {
            "form-TOTAL_FORMS": "1", "form-INITIAL_FORMS": "0",
            "form-0-fund": fund.id, "form-0-profit": "0.84",
            "form-0-invested": "5", "form-0-profit_ratio": "",
            "action": "save",
        })
        self.assertEqual(resp.status_code, 302)
        r = DailyRecord.objects.get(fund=fund, date=date(2026, 6, 2))
        self.assertEqual(r.total, Decimal("15.84"))
        self.assertEqual(r.pending, Decimal("5"))

    def test_mark_no_trade(self):
        fund = self._make_fund()
        resp = self.client.post("/funds/daily/?date=2026-06-07", {"action": "no_trade"})
        self.assertEqual(resp.status_code, 302)
        r = DailyRecord.objects.get(fund=fund, date=date(2026, 6, 7))
        self.assertFalse(r.has_trade)


class DashboardTest(FundCrudTest):
    def _fund_with_record(self):
        f = Fund.objects.create(user=self.u, name="A", market="CN", confirm_delay=1,
            invest_amount=Decimal("5"), invest_frequency="DAILY",
            start_date=date(2026, 6, 1), start_total=Decimal("10"))
        DailyRecord.objects.create(fund=f, date=date(2026, 6, 1),
                                   invested=Decimal("5"), total=Decimal("10"))
        return f

    def test_dashboard_shows_totals(self):
        self._fund_with_record()
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "总市值")

    def test_fund_detail_page_html(self):
        f = self._fund_with_record()
        resp = self.client.get(f"/funds/{f.pk}/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, f.name)

    def test_fund_detail_data_json(self):
        f = self._fund_with_record()
        resp = self.client.get(f"/funds/{f.pk}/data/")
        self.assertEqual(resp["Content-Type"], "application/json")
