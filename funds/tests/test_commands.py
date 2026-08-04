from datetime import date
from decimal import Decimal
from unittest import mock
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from accounts.models import User
from funds.models import Fund, DailyRecord, FundNav


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class CommandTest(TestCase):
    def setUp(self):
        self.u = User.objects.create_user("u", "u@e.com", "x", email_verified=True)
        self.fund = Fund.objects.create(
            user=self.u, name="A", market="CN", confirm_delay=1,
            invest_amount=5, invest_frequency="DAILY",
            start_date=date(2026, 6, 1), start_total=0)

    def test_weekday_sends_entry_when_not_engaged(self):
        call_command("send_daily_email", date="2026-06-02", reminder=1)   # 周二
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("/accounts/magic/", mail.outbox[0].body)

    def test_weekend_sends_weekend_email_once(self):
        call_command("send_daily_email", date="2026-06-06", reminder=1)   # 周六
        self.assertIn("周末", mail.outbox[-1].subject)
        mail.outbox = []
        call_command("send_daily_email", date="2026-06-06", reminder=2)   # 周末第2次不发
        self.assertEqual(len(mail.outbox), 0)

    def test_engaged_skips_email(self):
        DailyRecord.objects.create(fund=self.fund, date=date(2026, 6, 2),
                                   profit=Decimal("1"), invested=Decimal("5"))
        call_command("send_daily_email", date="2026-06-02", reminder=1)
        self.assertEqual(len(mail.outbox), 0)

    def test_finalize_marks_no_trade_when_not_engaged(self):
        DailyRecord.objects.create(fund=self.fund, date=date(2026, 6, 2),
                                   invested=Decimal("5"), profit=None, has_trade=True)
        call_command("finalize_daily", date="2026-06-02")
        r = DailyRecord.objects.get(fund=self.fund, date=date(2026, 6, 2))
        self.assertFalse(r.has_trade)

    def test_finalize_skips_when_engaged(self):
        DailyRecord.objects.create(fund=self.fund, date=date(2026, 6, 2),
                                   profit=Decimal("1"), invested=Decimal("5"))
        call_command("finalize_daily", date="2026-06-02")
        r = DailyRecord.objects.get(fund=self.fund, date=date(2026, 6, 2))
        self.assertTrue(r.has_trade)   # 已录入不被改

    def test_reminder_subject_shows_count(self):
        """三次提醒标题都带「第 N 次提醒」，含最常见的第 1 次。"""
        call_command("send_daily_email", date="2026-06-02", reminder=1)   # 周二
        self.assertIn("第 1 次提醒", mail.outbox[0].subject)
        mail.outbox = []
        call_command("send_daily_email", date="2026-06-02", reminder=2)
        self.assertIn("第 2 次提醒", mail.outbox[0].subject)

    def test_fetch_navs_dedupes_duplicate_codes(self):
        """同一代码多只基金只抓一次(set 去重)，不再因 distinct() 失效抓两遍。"""
        for nm in ("B", "C"):
            Fund.objects.create(user=self.u, name=nm, code="000010", market="CN",
                                confirm_delay=1, invest_amount=5, invest_frequency="DAILY",
                                start_date=date(2026, 6, 1), start_total=0)

        class _DF:  # 极简 DataFrame 替身：iterrows 产出 (index, row)，row 支持 .get
            def __init__(self):
                self._rows = [{"净值日期": date(2026, 6, 2), "单位净值": 1.0}]

            def iterrows(self):
                for i, row in enumerate(self._rows):
                    yield i, row

        with mock.patch("akshare.fund_open_fund_info_em", return_value=_DF()) as m:
            call_command("fetch_fund_navs")
        self.assertEqual(m.call_count, 1)   # 同代码去重，只抓 1 次
        self.assertTrue(FundNav.objects.filter(code="000010", date=date(2026, 6, 2)).exists())
