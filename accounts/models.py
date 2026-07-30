import secrets
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    email_verified = models.BooleanField(default=False)
    mail_login_token = models.CharField(max_length=64, default="")
    deepseek_key_enc = models.CharField(max_length=512, blank=True, default="")

    @staticmethod
    def generate_token() -> str:
        return secrets.token_urlsafe(24)[:32]

    @property
    def deepseek_key(self) -> str:
        if not self.deepseek_key_enc:
            return ""
        from aiagent.crypto import decrypt_key
        try:
            return decrypt_key(self.deepseek_key_enc)
        except Exception:
            return ""

    def set_deepseek_key(self, plain: str) -> None:
        from aiagent.crypto import encrypt_key
        self.deepseek_key_enc = encrypt_key(plain) if plain else ""

    def save(self, *args, **kwargs):
        if not self.mail_login_token:
            self.mail_login_token = User.generate_token()
        super().save(*args, **kwargs)
