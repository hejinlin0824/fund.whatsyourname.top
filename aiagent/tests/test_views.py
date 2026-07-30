import os
from datetime import date
from unittest import mock
from django.test import TestCase
from django.urls import reverse
from accounts.models import User
from aiagent.models import AnalysisReport


class ViewTest(TestCase):
    def setUp(self):
        os.environ["JK_FERNET_KEY"] = "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg="
        self.u = User.objects.create_user(username="v", password="p", email="v@e.com")
        self.client.force_login(self.u)

    def test_list_shows_reports(self):
        AnalysisReport.objects.create(user=self.u, type="morning", date=date(2026, 7, 30), content_html="x")
        r = self.client.get(reverse("aiagent:report-list"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "午间")

    def test_key_settings_post_sets_key(self):
        r = self.client.post(reverse("aiagent:key-settings"), {"deepseek_key": "sk-new"})
        self.assertEqual(r.status_code, 302)
        self.u.refresh_from_db()
        self.assertEqual(self.u.deepseek_key, "sk-new")

    def test_on_demand_quota_blocks_6th(self):
        with mock.patch("aiagent.views.services.generate_report") as g:
            def make(*a, **k):
                return AnalysisReport.objects.create(
                    user=self.u, type="ondemand", date=date.today(), content_html="x")
            g.side_effect = make
            for _ in range(5):
                self.assertEqual(self.client.post(reverse("aiagent:on-demand")).status_code, 302)
            self.assertEqual(self.client.post(reverse("aiagent:on-demand")).status_code, 429)
