from django.urls import path
from . import views

app_name = "aiagent"
urlpatterns = [
    path("", views.report_list, name="report-list"),
    path("key/", views.key_settings, name="key-settings"),
    path("on-demand/", views.on_demand, name="on-demand"),
    path("<int:pk>/delete/", views.report_delete, name="report-delete"),
    path("<int:pk>/", views.report_detail, name="report-detail"),
]
