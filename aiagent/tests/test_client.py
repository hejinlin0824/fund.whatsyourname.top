import os
from unittest import mock
from django.test import TestCase
from accounts.models import User
from aiagent import client


def _resp(status, body=None):
    r = mock.Mock()
    r.status_code = status
    r.json.return_value = body or {}
    return r


class ClientTest(TestCase):
    def setUp(self):
        os.environ["JK_FERNET_KEY"] = "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg="
        self.u = User.objects.create_user(username="c", password="p", email="c@e.com")
        self.u.set_deepseek_key("sk-test")
        self.u.save()

    @mock.patch("aiagent.client.requests.post")
    def test_chat_ok(self, post):
        post.return_value = _resp(200, {"choices": [{"message": {"content": "hi"}}],
                                        "usage": {"total_tokens": 10}})
        res = client.chat(self.u, [{"role": "user", "content": "hi"}])
        self.assertTrue(res["ok"])
        self.assertEqual(res["content"], "hi")
        self.assertEqual(res["usage"]["total_tokens"], 10)

    def test_no_key(self):
        u2 = User.objects.create_user(username="c2", password="p", email="c2@e.com")
        res = client.chat(u2, [{"role": "user", "content": "hi"}])
        self.assertFalse(res["ok"])
        self.assertEqual(res["error"], "no_api_key")

    @mock.patch("aiagent.client.requests.post")
    @mock.patch("aiagent.client.time.sleep")
    def test_retry_then_ok(self, sleep, post):
        post.side_effect = [_resp(500), _resp(200, {"choices": [{"message": {"content": "ok"}}]})]
        res = client.chat(self.u, [{"role": "user", "content": "x"}])
        self.assertTrue(res["ok"])
        self.assertEqual(post.call_count, 2)

    @mock.patch("aiagent.client.requests.post")
    def test_invalid_key_no_retry(self, post):
        post.return_value = _resp(401)
        res = client.chat(self.u, [{"role": "user", "content": "x"}])
        self.assertFalse(res["ok"])
        self.assertEqual(res["error"], "invalid_api_key")
        self.assertEqual(post.call_count, 1)
