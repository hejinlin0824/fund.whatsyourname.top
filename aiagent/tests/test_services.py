import os
from unittest import mock
from django.test import TestCase
from django.utils import timezone
from accounts.models import User
from news.models import Article
from aiagent import services


class ServicesTest(TestCase):
    def setUp(self):
        os.environ["JK_FERNET_KEY"] = "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg="
        self.u = User.objects.create_user(username="sv", password="p", email="sv@e.com")
        self.u.set_deepseek_key("sk-x")
        self.u.save()
        self.a = Article.objects.create(title="美联储降息", summary="降息25bp", url="http://s/1",
                                        published_at=timezone.now(), category="finance")

    @mock.patch("aiagent.services.analysis.analyze")
    @mock.patch("aiagent.services.screening.screen")
    def test_happy_path(self, screen, analyze):
        screen.return_value = [{"article_id": self.a.id, "reason": "相关", "category": "finance"}]
        analyze.return_value = {"market_brief": {},
                                "bias": [{"fund": "x", "direction": "利好", "reason": "r"}],
                                "position_advice": [], "lesson": {}}
        rep = services.generate_report(self.u, "morning")
        self.assertEqual(rep.status, "ok")
        self.assertIn("利好", rep.content_html)
        self.assertEqual(rep.screening[0]["article_id"], self.a.id)

    @mock.patch("aiagent.services.analysis.analyze")
    @mock.patch("aiagent.services.screening.screen")
    def test_degraded_on_analysis_fail(self, screen, analyze):
        screen.return_value = [{"article_id": self.a.id, "reason": "r", "category": "finance"}]
        from aiagent.analysis import AnalysisError
        analyze.side_effect = AnalysisError("bad")
        rep = services.generate_report(self.u, "morning")
        self.assertEqual(rep.status, "degraded")
        self.assertIn("AI 分析暂不可用", rep.content_html)
        self.assertIn("美联储降息", rep.content_html)

    @mock.patch("aiagent.services.screening.screen")
    def test_no_news_short_report(self, screen):
        Article.objects.all().delete()
        screen.return_value = []
        rep = services.generate_report(self.u, "morning")
        self.assertEqual(rep.status, "ok")
        self.assertIn("暂无足够新闻", rep.content_html)

    def test_no_key_skips(self):
        u2 = User.objects.create_user(username="sv2", password="p", email="sv2@e.com")
        with self.assertRaises(services.NoApiKey):
            services.generate_report(u2, "morning")
