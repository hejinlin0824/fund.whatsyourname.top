import os
import json
from unittest import mock
from django.test import TestCase
from accounts.models import User
from aiagent import analysis


SAMPLE = {"market_brief": {"politics": [], "finance_cn": [], "finance_oversea": [], "tech": []},
          "bias": [{"fund": "南方纳斯达克100", "direction": "利好", "reason": "降息预期",
                    "refs": [{"kind": "新闻", "text": "美联储降息"}]}],
          "position_advice": [{"fund": "南方纳斯达克100", "action": "继续定投", "reason": "趋势向上",
                               "refs": [{"kind": "仓位", "text": "南方纳斯达克100 美股/指数 收益率+8%"}]}],
          "lesson": {"title": "降息与纳指", "body": "宽松利好成长股"}}


class AnalysisTest(TestCase):
    def setUp(self):
        os.environ["JK_FERNET_KEY"] = "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg="
        self.u = User.objects.create_user(username="an", password="p", email="an@e.com")
        self.u.set_deepseek_key("sk")
        self.u.save()
        self.picked = [{"article_id": 1, "title": "美联储降息",
                        "summary": "降息25bp", "category": "finance"}]

    @mock.patch("aiagent.analysis.client.chat")
    def test_noon_uses_chat(self, chat):
        chat.return_value = {"ok": True, "content": json.dumps(SAMPLE), "usage": {}}
        out = analysis.analyze(self.u, self.picked, "持仓", "（今日无操作）", "noon")
        self.assertEqual(out["bias"][0]["fund"], "南方纳斯达克100")
        self.assertEqual(out["bias"][0]["refs"][0]["kind"], "新闻")
        chat.assert_called_once()

    @mock.patch("aiagent.analysis.client.reasoner")
    def test_evening_uses_reasoner(self, reasoner):
        s2 = dict(SAMPLE)
        s2["tomorrow"] = {"events": [], "watch": "非农数据"}
        reasoner.return_value = {"ok": True, "content": json.dumps(s2), "usage": {}}
        out = analysis.analyze(self.u, self.picked, "持仓", "", "evening")
        self.assertEqual(out["tomorrow"]["watch"], "非农数据")
        reasoner.assert_called_once()

    @mock.patch("aiagent.analysis.client.chat")
    def test_non_json_raises(self, chat):
        chat.return_value = {"ok": True, "content": "<<<", "usage": {}}
        with self.assertRaises(analysis.AnalysisError):
            analysis.analyze(self.u, self.picked, "持仓", "", "noon")
