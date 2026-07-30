import os
from unittest import mock
from django.core.management import call_command
from django.test import TestCase
from accounts.models import User


class CommandTest(TestCase):
    def setUp(self):
        os.environ["JK_FERNET_KEY"] = "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg="
        self.u = User.objects.create_user(username="cmd", password="p", email="cmd@e.com",
                                          is_active=True, email_verified=True)
        self.u.set_deepseek_key("sk")
        self.u.save()
        User.objects.create_user(username="nokey", password="p", email="n@e.com",
                                 is_active=True, email_verified=True)

    @mock.patch("aiagent.emails.send_report_email")
    @mock.patch("aiagent.services.analysis.analyze")
    @mock.patch("aiagent.services.screening.screen")
    def test_morning_runs_for_eligible(self, screen, analyze, send):
        from aiagent.models import AnalysisReport
        screen.return_value = []
        analyze.return_value = {"market_brief": {}, "bias": [], "position_advice": [], "lesson": {}}
        call_command("run_ai_morning")
        send.assert_called_once()  # 只发给 cmd（有 key），nokey 被跳过
        self.assertTrue(AnalysisReport.objects.filter(user=self.u, type="morning").exists())
