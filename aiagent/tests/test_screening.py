import os
import json
from unittest import mock
from django.test import TestCase
from accounts.models import User
from aiagent import screening


class ScreeningTest(TestCase):
    def setUp(self):
        os.environ["JK_FERNET_KEY"] = "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg="
        self.u = User.objects.create_user(username="sc", password="p", email="sc@e.com")

    @mock.patch("aiagent.screening.client.chat")
    def test_picks_returned(self, chat):
        chat.return_value = {"ok": True, "content": json.dumps({
            "picks": [{"id": 1, "reason": "美联储动向利好美股"},
                      {"id": 3, "reason": "纳指相关"}]}), "usage": {}}
        out = screening.screen(self.u, {"finance": [{"id": 1, "title": "a"},
                                                    {"id": 2, "title": "b"},
                                                    {"id": 3, "title": "c"}]},
                               "持仓:纳斯达克100")
        self.assertEqual([p["article_id"] for p in out], [1, 3])
        self.assertEqual(out[0]["reason"], "美联储动向利好美股")

    @mock.patch("aiagent.screening.client.chat")
    def test_bad_json_raises(self, chat):
        chat.return_value = {"ok": True, "content": "not json{", "usage": {}}
        with self.assertRaises(screening.ScreeningError):
            screening.screen(self.u, {"finance": [{"id": 1, "title": "a"}]}, "持仓")
