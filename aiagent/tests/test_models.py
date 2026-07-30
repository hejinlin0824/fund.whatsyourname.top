from datetime import date
import os
from django.db import IntegrityError, transaction
from django.test import TestCase
from accounts.models import User
from aiagent.models import AnalysisReport


class UserModelTest(TestCase):
    def setUp(self):
        os.environ["JK_FERNET_KEY"] = "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg="

    def test_key_roundtrip_via_user(self):
        u = User.objects.create_user(username="t", password="p", email="t@e.com")
        u.set_deepseek_key("sk-abc")
        u.save()
        u.refresh_from_db()
        self.assertNotEqual(u.deepseek_key_enc, "sk-abc")
        self.assertEqual(u.deepseek_key, "sk-abc")

    def test_no_key_returns_empty(self):
        u = User.objects.create_user(username="t2", password="p", email="t2@e.com")
        self.assertEqual(u.deepseek_key, "")


class ReportModelTest(TestCase):
    def test_create_and_unique_timed(self):
        u = User.objects.create_user(username="t3", password="p", email="t3@e.com")
        AnalysisReport.objects.create(user=u, type="morning", date=date(2026, 7, 30))
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                AnalysisReport.objects.create(user=u, type="morning", date=date(2026, 7, 30))

    def test_ondemand_allows_many(self):
        u = User.objects.create_user(username="t4", password="p", email="t4@e.com")
        AnalysisReport.objects.create(user=u, type="ondemand", date=date(2026, 7, 30))
        AnalysisReport.objects.create(user=u, type="ondemand", date=date(2026, 7, 30))
        self.assertEqual(AnalysisReport.objects.filter(user=u, type="ondemand").count(), 2)
