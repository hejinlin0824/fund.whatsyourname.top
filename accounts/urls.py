from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", views.register, name="register"),
    path("register/done/", views.register_done, name="register_done"),
    path("verify/<str:uidb64>/<str:token>/", views.verify_email, name="verify_email"),
    path("magic/<str:token>/", views.magic_login, name="magic_login"),
]
