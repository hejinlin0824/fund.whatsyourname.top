from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, api

router = DefaultRouter()
router.register("articles", api.ArticleViewSet, basename="article")

urlpatterns = [
    path("", views.news_list, name="news-list"),
    path("api/", include(router.urls)),
]
