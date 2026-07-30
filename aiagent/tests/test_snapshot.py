from datetime import date
from decimal import Decimal
from django.test import TestCase
from accounts.models import User
from funds.models import Fund
from funds.services import portfolio_snapshot, backfill_fund


class SnapshotTest(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username="s", password="p", email="s@e.com")
        self.f = Fund.objects.create(
            user=self.u, name="南方纳斯达克100", code="160213", market="US",
            invest_amount=Decimal("100"), start_date=date(2026, 7, 1), start_total=Decimal("0"))
        backfill_fund(self.f)

    def test_snapshot_shape(self):
        snap = portfolio_snapshot(self.u)
        self.assertIn("funds", snap)
        self.assertEqual(snap["funds"][0]["name"], "南方纳斯达克100")
        self.assertEqual(snap["funds"][0]["market"], "US")
        for k in ("mv", "cost", "profit", "roi"):
            self.assertIn(k, snap["funds"][0])
        for k in ("total_mv", "total_cost", "total_profit", "total_roi"):
            self.assertIn(k, snap)

    def test_empty_user(self):
        u2 = User.objects.create_user(username="s2", password="p", email="s2@e.com")
        snap = portfolio_snapshot(u2)
        self.assertEqual(snap["funds"], [])
        self.assertEqual(snap["total_mv"], "0")
