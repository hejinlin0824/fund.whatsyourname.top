from django.urls import path
from . import views

urlpatterns = [
    path("", views.fund_list, name="fund-list"),
    path("new/", views.fund_create, name="fund-create"),
    path("<int:pk>/edit/", views.fund_edit, name="fund-edit"),
]
