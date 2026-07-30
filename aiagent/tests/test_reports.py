from django.test import TestCase
from aiagent import reports

SAMPLE = {"market_brief": {"politics": [{"title": "t", "impact": "i"}],
                           "finance_cn": [], "finance_oversea": [], "tech": []},
          "bias": [{"fund": "南方纳斯达克100", "direction": "利好", "reason": "r",
                    "refs": [{"kind": "新闻", "text": "美联储降息"}]}],
          "position_advice": [{"fund": "南方纳斯达克100", "action": "继续定投", "reason": "r",
                               "refs": [{"kind": "仓位", "text": "纳指100 收益率+8%"}]}],
          "tomorrow": {"events": [{"time": "20:30", "event": "非农"}], "watch": "纳指前高"},
          "lesson": {"title": "降息", "body": "利好成长股"}}


class ReportsTest(TestCase):
    def test_renders_sections_evening(self):
        html = reports.render(SAMPLE, "evening")
        self.assertIn("新闻速览", html)
        self.assertIn("利好", html)
        self.assertIn("南方纳斯达克100", html)
        self.assertIn("仓位建议", html)
        self.assertIn("明日预判", html)      # analysis.tomorrow 存在 → 渲染
        self.assertIn("小白课堂", html)
        self.assertIn("不构成投资建议", html)
        self.assertIn("参考", html)          # refs 渲染
        self.assertIn("美联储降息", html)    # ref 文本
        self.assertIn("bi-newspaper", html)  # 图标 class
        self.assertNotIn("📰", html)         # 无 emoji

    def test_noon_omits_tomorrow(self):
        noon = {k: v for k, v in SAMPLE.items() if k != "tomorrow"}
        html = reports.render(noon, "morning")
        self.assertNotIn("明日预判", html)
        self.assertNotIn("📰", html)
