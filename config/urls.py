from django.contrib import admin
from django.urls import path, include
from funds import views as fund_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("funds/", include("funds.urls")),
    path("news/", include("news.urls")),
    path("", fund_views.dashboard, name="dashboard"),
]
