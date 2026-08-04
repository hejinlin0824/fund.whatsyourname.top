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


def send_daily_entry_email(user, host, reminder):
    """工作日录入提醒邮件，含 magic link（点开自动登录到今日录入页）。"""
    link = f"{host}/accounts/magic/{user.mail_login_token}/"
    suffix = f"（第 {reminder} 次提醒）"
    send_mail(
        subject=f"【基金看板】录入今日盈亏{suffix}",
        message=(f"今日有交易？点此录入（自动登录到今日）：\n{link}\n\n"
                 f"今日无交易？点开后按「今日无交易」即可。"),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def send_weekend_email(user):
    send_mail(
        subject="【基金看板】周末愉快",
        message="周末不交易，好好休息～下周见。",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
