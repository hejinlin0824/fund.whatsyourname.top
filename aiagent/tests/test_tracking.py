from datetime import date
from decimal import Decimal
from django.test import TestCase
from accounts.models import User
from funds.models import Fund
from funds import actions
from aiagent import context
from aiagent.models import ActionLog


class TrackingTest(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username="tr", password="p", email="tr@e.com")
        self.f = Fund.objects.create(user=self.u, name="纳指100", code="160213", market="US",
                                     invest_amount=Decimal("100"), start_date=date(2026, 7, 1),
                                     start_total=Decimal("0"))

    def test_log_create(self):
        actions.log_fund_create(self.u, self.f)
        self.assertEqual(ActionLog.objects.filter(user=self.u).count(), 1)
        self.assertIn("新增基金", ActionLog.objects.first().text)

    def test_log_edit_invest_change(self):
        old = {"invest_amount": Decimal("100"), "is_active": True, "is_cleared": False, "name": "纳指100"}
        self.f.invest_amount = Decimal("50")
        self.f.save()
        actions.log_fund_edit(self.u, self.f, old)
        self.assertTrue(ActionLog.objects.filter(kind="invest_changed", user=self.u).exists())

    def test_operations_text(self):
        actions.log_fund_create(self.u, self.f)
        txt = context.recent_operations_text(self.u, date.today())
        self.assertIn("今日操作", txt)
        self.assertIn("新增基金", txt)

    def test_operations_empty(self):
        self.assertEqual(context.recent_operations_text(self.u, date.today()), "")
