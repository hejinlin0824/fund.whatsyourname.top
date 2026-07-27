from django.test import TestCase
from accounts.models import User
from funds.models import Fund


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

    def test_list_shows_own_funds_only(self):
        Fund.objects.create(user=self.u, name="mine", market="CN", confirm_delay=1,
            invest_amount=5, invest_frequency="DAILY", start_date="2026-06-01", start_total=10)
        other = User.objects.create_user("o", "o@e.com", "pwd12345")
        Fund.objects.create(user=other, name="ZZZnotmine", market="CN", confirm_delay=1,
            invest_amount=5, invest_frequency="DAILY", start_date="2026-06-01", start_total=10)
        resp = self.client.get("/funds/")
        self.assertContains(resp, "mine")
        self.assertNotContains(resp, "ZZZnotmine")
