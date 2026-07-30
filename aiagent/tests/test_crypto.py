import os
from django.test import TestCase
from aiagent import crypto


class CryptoTest(TestCase):
    def setUp(self):
        os.environ["JK_FERNET_KEY"] = "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg="

    def test_roundtrip(self):
        enc = crypto.encrypt_key("sk-test-123")
        self.assertNotEqual(enc, "sk-test-123")
        self.assertEqual(crypto.decrypt_key(enc), "sk-test-123")

    def test_empty(self):
        self.assertEqual(crypto.encrypt_key(""), "")
        self.assertEqual(crypto.decrypt_key(""), "")
