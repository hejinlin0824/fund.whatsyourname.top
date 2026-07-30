from django.test import TestCase
from aiagent import reports

SAMPLE = {"market_brief": {"politics": [{"title": "t", "impact": "i"}],
                           "finance_cn": [], "finance_oversea": [], "tech": []},
          "bias": [{"fund": "南方纳斯达克100", "direction": "利好", "reason": "r"}],
          "position_advice": [{"fund": "南方纳斯达克100", "action": "继续定投", "reason": "r"}],
          "tomorrow": {"events": [{"time": "20:30", "event": "非农"}], "watch": "纳指前高"},
          "lesson": {"title": "降息", "body": "利好成长股"}}


class ReportsTest(TestCase):
    def test_renders_sections(self):
        html = reports.render(SAMPLE, "evening")
        self.assertIn("新闻速览", html)
        self.assertIn("利好", html)
        self.assertIn("南方纳斯达克100", html)
        self.assertIn("仓位建议", html)
        self.assertIn("明日预判", html)
        self.assertIn("小白课堂", html)
        self.assertIn("不构成投资建议", html)

    def test_noon_omits_tomorrow(self):
        html = reports.render({k: v for k, v in SAMPLE.items() if k != "tomorrow"}, "morning")
        self.assertNotIn("明日预判", html)
