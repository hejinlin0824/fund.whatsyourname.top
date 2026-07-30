import os
from datetime import date
from django.core import mail
from django.test import TestCase, override_settings
from accounts.models import User
from aiagent.models import AnalysisReport
from aiagent import emails


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class EmailTest(TestCase):
    def setUp(self):
        os.environ["JK_FERNET_KEY"] = "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg="
        self.u = User.objects.create_user(username="em", password="p", email="em@e.com")

    def test_send(self):
        rep = AnalysisReport.objects.create(user=self.u, type="evening", date=date(2026, 7, 30),
                                            content_html="<h2>新闻速览</h2><p>x</p>")
        n = emails.send_report_email(rep)
        self.assertEqual(n, 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("新闻速览", mail.outbox[0].alternatives[0][0])
        self.assertEqual(mail.outbox[0].to, ["em@e.com"])
