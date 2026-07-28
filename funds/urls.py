from django.urls import path
from . import views

urlpatterns = [
    path("", views.fund_list, name="fund-list"),
    path("new/", views.fund_create, name="fund-create"),
    path("<int:pk>/", views.fund_detail, name="fund-detail"),
    path("<int:pk>/data/", views.fund_detail_data, name="fund-detail-data"),
    path("<int:pk>/edit/", views.fund_edit, name="fund-edit"),
    path("daily/", views.daily_entry, name="daily-entry"),
]
