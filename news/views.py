from django.shortcuts import render
from .models import Article, CATEGORY_CHOICES


def news_list(request):
    cat = request.GET.get("cat", "").strip()
    q = request.GET.get("q", "").strip()
    qs = Article.objects.all()
    if cat:
        qs = qs.filter(category=cat)
    if q:
        qs = qs.filter(title__icontains=q)
    articles = qs.select_related("source_ref")[:100]
    return render(request, "news/list.html", {
        "articles": articles, "cat": cat, "q": q, "cats": CATEGORY_CHOICES,
    })
