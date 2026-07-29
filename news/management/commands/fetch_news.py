from django.core.management.base import BaseCommand
from news.models import Source, Article
from news.fetchers import fetch_source


class Command(BaseCommand):
    help = "抓取新闻：按数据源拉取 → 清洗 → 按 url 去重入库"

    def add_arguments(self, parser):
        parser.add_argument("--source", default=None, help="只抓指定 slug 的数据源；不指定则全部 enabled")

    def handle(self, *args, **opts):
        qs = Source.objects.filter(enabled=True)
        if opts["source"]:
            qs = qs.filter(slug=opts["source"])
        total_new = 0
        for src in qs:
            try:
                items = fetch_source(src)
            except Exception as e:
                self.stderr.write(f"{src.name} 抓取异常: {e}")
                continue
            created = 0
            for it in items:
                if not it["url"] or not it["published_at"]:
                    continue
                _, was_created = Article.objects.update_or_create(
                    url=it["url"],
                    defaults={
                        "title": it["title"][:500],
                        "summary": it["summary"],
                        "content": it["content"],
                        "published_at": it["published_at"],
                        "category": it["category"],
                        "source": it["source"],
                        "source_ref": src,
                    },
                )
                created += 1 if was_created else 0
            total_new += created
            self.stdout.write(f"{src.name}: 拉取 {len(items)} 条，新增 {created} 条")
        self.stdout.write(self.style.SUCCESS(f"完成，共新增 {total_new} 条"))
