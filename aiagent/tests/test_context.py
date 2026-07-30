from django.test import TestCase
from django.utils import timezone
from news.models import Article
from aiagent import context


class ContextTest(TestCase):
    def setUp(self):
        self.d = timezone.localdate()
        self.a1 = Article.objects.create(title="美联储维持利率", summary="维持利率不变",
                                         url="http://x/1", published_at=timezone.now(), category="finance")
        self.a2 = Article.objects.create(title="纳指再创新高", summary="科技股领涨",
                                         url="http://x/2", published_at=timezone.now(), category="finance")

    def test_titles_grouped(self):
        out = context.news_titles_by_category(self.d)
        self.assertEqual({t["title"] for t in out.get("finance", [])},
                         {"美联储维持利率", "纳指再创新高"})

    def test_summaries_for(self):
        sm = context.summaries_for([self.a1.id, self.a2.id])
        self.assertEqual(sm[self.a2.id]["summary"], "科技股领涨")
