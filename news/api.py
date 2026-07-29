from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter, OrderingFilter
from rest_framework.response import Response
from .models import Article


class ArticleSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = Article
        fields = ["id", "title", "summary", "content", "url", "published_at",
                  "category", "category_display", "source"]


class ArticleViewSet(viewsets.ReadOnlyModelViewSet):
    """新闻列表接口：?category=&search=&ordering= ；?export&start=&end= 批量导出（喂 AI）。"""
    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ["title", "summary"]
    ordering_fields = ["published_at"]
    ordering = ["-published_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        cat = self.request.GET.get("category")
        if cat:
            qs = qs.filter(category=cat)
        return qs

    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request):
        """导出指定时段+分类的完整新闻文本，用于批量投喂 AI。"""
        qs = self.get_queryset()
        start = request.GET.get("start")
        end = request.GET.get("end")
        if start:
            qs = qs.filter(published_at__date__gte=start)
        if end:
            qs = qs.filter(published_at__date__lte=end)
        qs = qs[:5000]
        data = ArticleSerializer(qs, many=True).data
        return Response({"count": len(data), "items": data})
