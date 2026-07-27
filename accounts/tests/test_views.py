from django.test import TestCase, override_settings
from django.core import mail
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from accounts.models import User
from accounts.tokens import make_email_verify_token


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class RegisterViewTest(TestCase):
    def test_register_creates_and_sends_email(self):
        resp = self.client.post("/accounts/register/", {
            "username": "bob", "email": "bob@e.com",
            "password1": "Str0ng!Pass", "password2": "Str0ng!Pass"})
        self.assertEqual(resp.status_code, 302)
        u = User.objects.get(username="bob")
        self.assertFalse(u.email_verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("bob@e.com", mail.outbox[0].to[0])

    def test_verify_link_sets_verified(self):
        u = User.objects.create_user("bob", "bob@e.com", "x")
        token = make_email_verify_token(u)
        uid = urlsafe_base64_encode(force_bytes(u.pk))
        self.client.get(f"/accounts/verify/{uid}/{token}/")
        u.refresh_from_db()
        self.assertTrue(u.email_verified)


class MagicLinkTest(TestCase):
    def test_valid_token_logs_in(self):
        u = User.objects.create_user("bob", "bob@e.com", "x")
        resp = self.client.get(f"/accounts/magic/{u.mail_login_token}/")
        self.assertEqual(resp.status_code, 302)
        self.assertTrue("_auth_user_id" in self.client.session)

    def test_invalid_token_rejected(self):
        resp = self.client.get("/accounts/magic/nope/")
        self.assertEqual(resp.status_code, 404)
