from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from .forms import RegisterForm
from .mails import send_verification_email
from .tokens import check_email_verify_token
from django.contrib.auth import login
from django.http import Http404
from django.conf import settings

User = get_user_model()


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            send_verification_email(user, request)
            return redirect("register_done")
    else:
        form = RegisterForm()
    return render(request, "registration/register.html", {"form": form})


def register_done(request):
    return render(request, "registration/register_done.html")


def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and check_email_verify_token(user, token):
        user.email_verified = True
        user.save()
        return render(request, "accounts/verify_email.html", {"ok": True})
    return render(request, "accounts/verify_email.html", {"ok": False})


def magic_login(request, token):
    """邮件 magic link 免密登录：校验 token → 登录 → 跳转。"""
    try:
        user = User.objects.get(mail_login_token=token)
    except User.DoesNotExist:
        raise Http404
    login(request, user)
    # Task 9 建好 daily-entry 后改为 redirect("daily-entry")
    return redirect(settings.LOGIN_REDIRECT_URL)
