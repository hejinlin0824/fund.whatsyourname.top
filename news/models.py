from django.db import models

CATEGORY_CHOICES = [
    ("politics", "时政国际"),
    ("finance", "A股财经"),
    ("tech_cn", "国内科技"),
    ("tech_oversea", "海外科技"),
]


class Source(models.Model):
    """可插拔新闻数据源。RSS 失效时改 url 即可；kind 决定用哪个抓取器。"""
    KIND_CHOICES = [("RSS", "RSS"), ("HN", "HackerNews"), ("AKSHARE", "AkShare"), ("CUSTOM", "自定义")]
    name = models.CharField("名称", max_length=64, unique=True)
    slug = models.SlugField(max_length=64, unique=True)
    kind = models.CharField("类型", max_length=12, choices=KIND_CHOICES, default="RSS")
    category = models.CharField("分类", max_length=16, choices=CATEGORY_CHOICES)
    url = models.URLField("地址", max_length=500, blank=True, help_text="RSS/API 地址；HN/AKSHARE 可留空")
    enabled = models.BooleanField("启用", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "数据源"
        ordering = ["id"]

    def __str__(self):
        return f"{self.name}({self.kind})"


class Article(models.Model):
    title = models.CharField("标题", max_length=500)
    summary = models.TextField("摘要", blank=True, default="")
    content = models.TextField("正文", blank=True, default="")
    url = models.URLField("原文链接", max_length=1000, unique=True)
    published_at = models.DateTimeField("发布时间", db_index=True)
    category = models.CharField("分类", max_length=16, choices=CATEGORY_CHOICES, db_index=True)
    source = models.CharField("来源", max_length=64, blank=True, default="")
    source_ref = models.ForeignKey(Source, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name="articles", verbose_name="数据源")
    # 预留：绑定站内基金
    funds = models.ManyToManyField("funds.Fund", blank=True, related_name="articles", verbose_name="关联基金")
    # 预留：AI 标签（情感/行业/个股）
    extra = models.JSONField("扩展", default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "新闻"
        ordering = ["-published_at"]

    def __str__(self):
        return self.title[:60]
