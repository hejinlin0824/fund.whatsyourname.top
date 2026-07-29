from datetime import datetime
from django.test import TestCase
from news.cleaners import parse_time, ensure_summary, strip_html


class CleanerTest(TestCase):
    def test_parse_rfc822(self):
        dt = parse_time("Wed, 02 Jul 2025 02:00:00 +0000")
        self.assertEqual(dt.tzname(), "CST")
        self.assertEqual(dt.hour, 10)              # UTC 02 → 北京 10

    def test_parse_iso(self):
        dt = parse_time("2025-07-02T10:30:00+08:00")
        self.assertEqual(dt.hour, 10)

    def test_parse_naive_assumes_shanghai(self):
        dt = parse_time("2025-07-02 10:30:00")
        self.assertEqual(dt.hour, 10)
        self.assertIsNotNone(dt.tzinfo)

    def test_parse_epoch(self):
        dt = parse_time("1751440800")              # epoch
        self.assertIsNotNone(dt)

    def test_parse_invalid_returns_none(self):
        self.assertIsNone(parse_time("not a date"))
        self.assertIsNone(parse_time(""))

    def test_ensure_summary_fallbacks(self):
        self.assertEqual(ensure_summary("T", "", ""), "T")               # title 兜底
        self.assertEqual(ensure_summary("T", "<b>x</b>", ""), "x")      # 去 HTML
        self.assertEqual(ensure_summary("T", "", "长正文"), "长正文")     # content 截取
