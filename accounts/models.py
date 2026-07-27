import secrets
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    email_verified = models.BooleanField(default=False)
    mail_login_token = models.CharField(max_length=64, default="")

    @staticmethod
    def generate_token() -> str:
        return secrets.token_urlsafe(24)[:32]

    def save(self, *args, **kwargs):
        if not self.mail_login_token:
            self.mail_login_token = User.generate_token()
        super().save(*args, **kwargs)
