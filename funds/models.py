from datetime import date, timedelta
from django.db import models
from accounts.models import User


class Fund(models.Model):
    MARKET_CHOICES = [("CN", "A股"), ("US", "美股")]
    FREQ_CHOICES = [("DAILY", "每日"), ("WEEKLY", "每周")]
    TYPE_CHOICES = [
        ("STOCK", "股票型"), ("MIXED", "混合型"), ("BOND", "债券型"),
        ("INDEX", "指数型"), ("QDII", "QDII"), ("MONEY", "货币型"),
    ]
    RISK_CHOICES = [(i, f"R{i}") for i in range(1, 6)]
    CURRENCY_CHOICES = [("CNY", "人民币"), ("USD", "美元")]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="funds")
    name = models.CharField(max_length=64)
    code = models.CharField(max_length=16, blank=True)
    market = models.CharField(max_length=2, choices=MARKET_CHOICES)
    confirm_delay = models.PositiveSmallIntegerField(default=1)   # A股=1, 美股=2
    invest_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    invest_frequency = models.CharField(max_length=6, choices=FREQ_CHOICES, default="DAILY")
    invest_weekday = models.PositiveSmallIntegerField(default=0)  # 0=周一…6=周日
    start_date = models.DateField()
    start_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fund_type = models.CharField(max_length=8, choices=TYPE_CHOICES, default="INDEX")
    risk_level = models.PositiveSmallIntegerField(choices=RISK_CHOICES, default=3)
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="CNY")
    is_active = models.BooleanField(default=True)
    tags = models.ManyToManyField("Tag", blank=True, related_name="funds")

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.name}({self.code})" if self.code else self.name

    def is_dca_day(self, d: date) -> bool:
        """今天是否是该基金的定投扣款日。每日=工作日(周一~周五)；每周=指定周几。"""
        if d.weekday() >= 5:           # 周六周日不扣款
            return False
        if self.invest_frequency == "DAILY":
            return True
        return d.weekday() == (self.invest_weekday or 0)

    def pending_label(self) -> str:
        """仅用于首日显示示例；运行时待确认由 services 计算。"""
        return f"{self.start_total:.2f}（待确认 {self.invest_amount:.2f}）"


class Tag(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tags")
    name = models.CharField(max_length=32)

    class Meta:
        unique_together = ("user", "name")

    def __str__(self):
        return self.name


class DailyRecord(models.Model):
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE, related_name="records")
    date = models.DateField()
    profit = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)  # 首日可为空
    profit_ratio = models.DecimalField(max_digits=7, decimal_places=4, null=True, blank=True)
    invested = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    pending = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    has_trade = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("fund", "date")
        ordering = ["date"]

    def __str__(self):
        return f"{self.fund.name} {self.date} total={self.total}"
