from django.test import TestCase
from accounts.models import User


class UserModelTest(TestCase):
    def test_create_user_defaults(self):
        u = User.objects.create_user(username="alice", email="a@e.com", password="x")
        self.assertEqual(u.email, "a@e.com")
        self.assertFalse(u.email_verified)
        self.assertTrue(u.mail_login_token)  # 自动生成非空

    def test_email_unique(self):
        User.objects.create_user(username="a", email="d@e.com", password="x")
        with self.assertRaises(Exception):
            User.objects.create_user(username="b", email="d@e.com", password="x")

    def test_generate_token_length(self):
        self.assertEqual(len(User.generate_token()), 32)
