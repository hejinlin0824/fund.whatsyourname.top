from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from .tokens import make_email_verify_token


def send_verification_email(user, request):
    """发送邮箱验证邮件，含一次性验证链接。"""
    token = make_email_verify_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    link = f"{request.scheme}://{request.get_host()}/accounts/verify/{uid}/{token}/"
    send_mail(
        subject="【基金看板】确认你的邮箱",
        message=f"点击链接确认邮箱：\n{link}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
