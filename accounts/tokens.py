from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import get_user_model

User = get_user_model()


def make_email_verify_token(user) -> str:
    return default_token_generator.make_token(user)


def check_email_verify_token(user, token) -> bool:
    return default_token_generator.check_token(user, token)
