from django.conf import settings
from django.db import models
from django.db.models import Q

MORNING, EVENING, ONDEMAND = "morning", "evening", "ondemand"
TYPE_CHOICES = [(MORNING, "午间"), (EVENING, "晚间"), (ONDEMAND, "手动")]
STATUS_CHOICES = [("ok", "ok"), ("degraded", "degraded"), ("failed", "failed")]


class AnalysisReport(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="ai_reports")
    type = models.CharField(max_length=8, choices=TYPE_CHOICES)
    date = models.DateField()
    content_html = models.TextField(default="")
    screening = models.JSONField(default=dict, blank=True)
    analysis = models.JSONField(default=dict, blank=True)
    meta = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=8, choices=STATUS_CHOICES, default="ok")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "type", "date"],
                condition=Q(type__in=[MORNING, EVENING]),
                name="uniq_timed_report_per_day"),
        ]
        indexes = [models.Index(fields=["user", "-date", "type"])]

    def __str__(self):
        return f"{self.user.username} {self.type} {self.date}"


class ActionLog(models.Model):
    """用户当日的关键操作（新增/调整基金等），用于注入当日 AI 总结。"""
    KIND_CHOICES = [
        ("fund_added", "新增基金"),
        ("invest_changed", "调整定投"),
        ("stopped", "停投"),
        ("resumed", "恢复定投"),
        ("cleared", "清仓"),
        ("edited", "编辑资料"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="action_logs")
    date = models.DateField(db_index=True)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES)
    text = models.CharField(max_length=200)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-date"])]

    def __str__(self):
        return f"{self.user.username} {self.date} {self.kind}"
