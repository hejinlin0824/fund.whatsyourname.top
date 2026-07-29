from django.contrib import admin
from .models import Source, Article


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "kind", "category", "enabled")
    list_editable = ("enabled",)
    list_filter = ("kind", "category", "enabled")
    search_fields = ("name", "url")


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "source", "published_at")
    list_filter = ("category", "source")
    search_fields = ("title", "summary")
    date_hierarchy = "published_at"
