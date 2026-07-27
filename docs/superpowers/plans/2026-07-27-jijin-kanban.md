# 基金看板（Jijin_Kanban）实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建一个 Django 基金看板 MVP，邮件驱动录入每日盈亏，系统反推每日总额/待确认/收益，提供组合总览、日历、走势可视化，并部署到 8188 端口供本地访问。

**Architecture:** 单体 Django + SQLite。核心计算逻辑抽为 `funds/services.py` 纯函数（TDD 重点）。录入由每日邮件 magic link 驱动，crontab 定时触发管理命令。

**Tech Stack:** Python 3.12.3 · Django 6.0.1 · SQLite · Bootstrap 5 + Chart.js · QQ SMTP · crontab + management commands

## Global Constraints

- **Python**: 3.12.3（`/usr/bin/python3`），所有 python 操作在项目根的 `venv/` 内执行
- **Django**: 6.0.1
- **路径**: `~/home/claude_PJ/Jijin_Kanban/`
- **金额字段**: 一律 `DecimalField(max_digits=12, decimal_places=2)`，代码内用 `decimal.Decimal`（禁止 float 参与金额运算）
- **比例字段**: `DecimalField(max_digits=7, decimal_places=4)`（如 0.0083 = 0.83%）
- **时区**: `TIME_ZONE = 'Asia/Shanghai'`，`USE_TZ = True`
- **日期**: `datetime.date`；`weekday()` 返回 0=周一…6=周日，`invest_weekday` 用同一编码
- **凭证**: SECRET_KEY、SMTP 授权码只进 `.env`（已 gitignore），绝不写代码
- **测试**: Django 内置 `TestCase`，命令 `venv/bin/python manage.py test`
- **端口**: 开发服务器 `0.0.0.0:8188`，腾讯云安全组需放行 TCP 8188
- **commit 频率**: 每个任务结束 commit 一次

---

## File Structure

```
~/home/claude_PJ/Jijin_Kanban/
├─ venv/                              # 虚拟环境
├─ .env                               # SECRET_KEY/SMTP/DEBUG（gitignore）
├─ .gitignore
├─ requirements.txt
├─ manage.py
├─ config/                            # Django 项目配置
│   ├─ __init__.py
│   ├─ settings.py                    # 读 .env、SQLite、时区、ALLOWED_HOSTS、INSTALLED_APPS
│   ├─ urls.py                        # 根路由
│   └─ wsgi.py
├─ accounts/                          # 用户与认证
│   ├─ models.py                      # User(AbstractUser) + email_verified + mail_login_token
│   ├─ tokens.py                      # 邮箱验证 token、magic link token 生成器
│   ├─ mails.py                       # 发邮件辅助函数
│   ├─ views.py                       # 注册/登录/邮箱验证/magic link 登录
│   ├─ forms.py                       # 注册表单
│   ├─ urls.py
│   └─ tests/test_*.py
├─ funds/                             # 基金、记录、计算、录入、报表
│   ├─ models.py                      # Fund, Tag, DailyRecord
│   ├─ services.py                    # ★计算逻辑纯函数（TDD 重点）
│   ├─ forms.py                       # 批量录入 formset
│   ├─ views.py                       # 录入/列表/详情/仪表盘/日历
│   ├─ urls.py
│   ├─ admin.py
│   ├─ management/commands/send_daily_email.py
│   ├─ management/commands/finalize_daily.py
│   └─ tests/test_services.py 等
├─ templates/{base.html, accounts/*, funds/*}
└─ static/
```

**职责边界**：`services.py` 只含纯函数（入参是 record/fund/Decimal，返回 Decimal/bool），不 import models 之外的 Django 组件（除 `datetime`/`decimal`）——保证可脱离 HTTP/DB 单测。

---

# Phase A — 基础设施与计算引擎

## Task 1: 项目骨架 + venv + 配置

**Files:**
- Create: `venv/`, `requirements.txt`, `.gitignore`, `.env`, `manage.py`, `config/{__init__.py,settings.py,urls.py,wsgi.py,asgi.py}`

**Interfaces:**
- Produces: 可运行的 Django 空项目；`config.settings` 读 `.env`；`INSTALLED_APPS` 占位；默认 SQLite `db.sqlite3`

- [ ] **Step 1: 建 venv 并装依赖**

```bash
cd ~/home/claude_PJ/Jijin_Kanban
/usr/bin/python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install "Django==6.0.1" python-dotenv
venv/bin/pip freeze > requirements.txt
```

- [ ] **Step 2: 起 Django 项目**

```bash
venv/bin/django-admin startproject config .
```

- [ ] **Step 3: 写 `.gitignore`**

```gitignore
venv/
__pycache__/
*.pyc
.env
db.sqlite3
db.sqlite3-journal
staticfiles/
.DS_Store
```

- [ ] **Step 4: 写 `.env`**（注意：真实 SMTP 授权码到 Task 11 再填，这里占位）

```dotenv
SECRET_KEY=dev-insecure-change-me-please-put-a-real-one-here
DEBUG=True
ALLOWED_HOSTS=49.234.26.95,localhost,127.0.0.1
EMAIL_HOST_USER=1285021260@qq.com
EMAIL_HOST_PASSWORD=REPLACE_WITH_NEW_SMTP_CODE
DEFAULT_FROM_EMAIL=1285021260@qq.com
```

- [ ] **Step 5: 改 `config/settings.py`**（关键改动）

```python
from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ["SECRET_KEY"]
DEBUG = os.environ.get("DEBUG", "False") == "True"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "funds",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

DATABASES = {"default": {
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": BASE_DIR / "db.sqlite3",
}}

AUTH_USER_MODEL = "accounts.User"
LANGUAGE_CODE = "zh-hans"
TIME_ZONE = "Asia/Shanghai"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Email（Task 11 用）
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.qq.com"
EMAIL_PORT = 465
EMAIL_USE_SSL = True
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", EMAIL_HOST_USER)
```

- [ ] **Step 6: 简化 `config/urls.py`（占位，后续 app 各自带 urls）**

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
]
```

- [ ] **Step 7: 建两个空 app 占位（避免 settings 引用报错）**

```bash
venv/bin/python manage.py startapp accounts
venv/bin/python manage.py startapp funds
```
> 每个 app 的 `apps.py` 里 `name` 改为 `"accounts"` / `"funds"`（默认即是）。

- [ ] **Step 8: 验证项目可启动**

```bash
venv/bin/python manage.py check
```
Expected: `System check identified no issues (0 silenced).`（可能因 AUTH_USER_MODEL 指向尚未定义的 accounts.User 报错——若报错，先注释 settings 里 `AUTH_USER_MODEL` 行，Task 2 定义 User 后再放开。）

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "chore: scaffold Django project with venv and config"
```

---

## Task 2: accounts.User 模型（自定义用户）

**Files:**
- Create: `accounts/models.py`, `accounts/migrations/`
- Test: `accounts/tests/test_models.py`

**Interfaces:**
- Produces: `accounts.User`（AbstractUser 扩展），字段 `email`(unique)、`email_verified`(bool)、`mail_login_token`(str)；类方法 `User.generate_token()` 返回 32 字符 token

- [ ] **Step 1: 写失败测试** `accounts/tests/__init__.py`（空）+ `accounts/tests/test_models.py`

```python
from django.test import TestCase
from accounts.models import User

class UserModelTest(TestCase):
    def test_create_user_defaults(self):
        u = User.objects.create_user(username="alice", email="a@e.com", password="x")
        self.assertEqual(u.email, "a@e.com")
        self.assertFalse(u.email_verified)
        self.assertTrue(u.mail_login_token)            # 自动生成非空

    def test_email_unique(self):
        User.objects.create_user(username="a", email="d@e.com", password="x")
        with self.assertRaises(Exception):
            User.objects.create_user(username="b", email="d@e.com", password="x")

    def test_generate_token_length(self):
        self.assertEqual(len(User.generate_token()), 32)
```

- [ ] **Step 2: 跑测试确认失败**

```bash
venv/bin/python manage.py test accounts.tests.test_models -v 2
```
Expected: FAIL（`accounts.User` 未定义 / 字段缺失）

- [ ] **Step 3: 实现 `accounts/models.py`**

```python
import secrets
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    email = models.EmailField(unique=True)
    email_verified = models.BooleanField(default=False)
    mail_login_token = models.CharField(max_length=64, default="")

    @staticmethod
    def generate_token() -> str:
        return secrets.token_urlsafe(24)[:32]

    def save(self, *args, **kwargs):
        if not self.mail_login_token:
            self.mail_login_token = User.generate_token()
        super().save(*args, **kwargs)
```

- [ ] **Step 4: 确保 settings 放开 `AUTH_USER_MODEL = "accounts.User"`，建迁移**

```bash
venv/bin/python manage.py makemigrations accounts
venv/bin/python manage.py migrate
```

- [ ] **Step 5: 跑测试确认通过**

```bash
venv/bin/python manage.py test accounts.tests.test_models -v 2
```
Expected: OK (3 tests)

- [ ] **Step 6: Commit**

```bash
git add accounts/
git commit -m "feat(accounts): custom User with email verification and login token"
```

---

## Task 3: funds.Fund 与 funds.Tag 模型

**Files:**
- Create: `funds/models.py`
- Test: `funds/tests/test_models.py`（先建 `funds/tests/__init__.py` 空）

**Interfaces:**
- Produces:
  - `Fund` 字段见下；`Fund.MARKET_CHOICES`、`Fund.FREQ_CHOICES`、`Fund.is_dca_day(date)->bool`
  - `Tag`(user, name)

- [ ] **Step 1: 写失败测试** `funds/tests/test_models.py`

```python
from datetime import date
from django.test import TestCase
from accounts.models import User
from funds.models import Fund, Tag


class FundModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", "u@e.com", "x")

    def test_create_fund(self):
        f = Fund.objects.create(
            user=self.user, name="A基金", market="CN", confirm_delay=1,
            invest_amount=5, invest_frequency="DAILY", start_date=date(2026, 6, 1),
            start_total=10, fund_type="INDEX", risk_level=3, currency="CNY",
        )
        self.assertEqual(f.pending_label(), "10.00（待确认 5.00）")  # 首日 pending=今日投入

    def test_is_dca_day_daily_weekday(self):
        f = Fund.objects.create(user=self.user, name="A", market="CN", confirm_delay=1,
            invest_amount=5, invest_frequency="DAILY", start_date=date(2026, 6, 1), start_total=10)
        self.assertTrue(f.is_dca_day(date(2026, 6, 1)))   # 周一
        self.assertFalse(f.is_dca_day(date(2026, 6, 6)))  # 周六

    def test_is_dca_day_weekly(self):
        f = Fund.objects.create(user=self.user, name="C", market="CN", confirm_delay=1,
            invest_amount=50, invest_frequency="WEEKLY", invest_weekday=2,  # 周三
            start_date=date(2026, 6, 1), start_total=0)
        self.assertTrue(f.is_dca_day(date(2026, 6, 3)))   # 周三
        self.assertFalse(f.is_dca_day(date(2026, 6, 4)))  # 周四
```

- [ ] **Step 2: 跑测试确认失败**

```bash
venv/bin/python manage.py test funds.tests.test_models -v 2
```
Expected: FAIL（`Fund` 未定义）

- [ ] **Step 3: 实现 `funds/models.py`**

```python
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
```

- [ ] **Step 4: 建迁移**

```bash
venv/bin/python manage.py makemigrations funds
venv/bin/python manage.py migrate
```

- [ ] **Step 5: 跑测试确认通过**

```bash
venv/bin/python manage.py test funds.tests.test_models -v 2
```
Expected: OK (3 tests)

- [ ] **Step 6: Commit**

```bash
git add funds/
git commit -m "feat(funds): Fund and Tag models"
```

---

## Task 4: funds.DailyRecord 模型

**Files:**
- Modify: `funds/models.py`（追加 DailyRecord）
- Test: `funds/tests/test_models.py`（追加用例）

**Interfaces:**
- Produces: `DailyRecord`(fund, date[unique_together], profit, profit_ratio, invested, total, pending, has_trade)

- [ ] **Step 1: 追加失败测试到 `funds/tests/test_models.py`**

```python
from funds.models import DailyRecord

class DailyRecordTest(FundModelTest):
    def test_unique_fund_date(self):
        f = Fund.objects.create(user=self.user, name="A", market="CN", confirm_delay=1,
            invest_amount=5, invest_frequency="DAILY", start_date=date(2026, 6, 1), start_total=10)
        DailyRecord.objects.create(fund=f, date=date(2026, 6, 2), profit=0.84, invested=5, has_trade=True)
        with self.assertRaises(Exception):
            DailyRecord.objects.create(fund=f, date=date(2026, 6, 2), profit=1, invested=5, has_trade=True)
```

- [ ] **Step 2: 跑测试确认失败**

```bash
venv/bin/python manage.py test funds.tests.test_models.DailyRecordTest -v 2
```
Expected: FAIL（DailyRecord 未定义）

- [ ] **Step 3: 在 `funds/models.py` 末尾追加**

```python
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
```

- [ ] **Step 4: 建迁移并应用**

```bash
venv/bin/python manage.py makemigrations funds
venv/bin/python manage.py migrate
```

- [ ] **Step 5: 跑测试确认通过**

```bash
venv/bin/python manage.py test funds.tests.test_models -v 2
```
Expected: OK（含 DailyRecordTest）

- [ ] **Step 6: Commit**

```bash
git add funds/
git commit -m "feat(funds): DailyRecord model"
```

---

## Task 5: ★计算逻辑 funds/services.py（TDD 核心）

**Files:**
- Create: `funds/services.py`
- Test: `funds/tests/test_services.py`

**Interfaces:**
- Consumes: `Fund`, `DailyRecord`（Task 3/4）
- Produces（供后续所有任务调用，签名固定）:
  - `compute_total(prev_total: Decimal, profit: Decimal|None, invested: Decimal|None) -> Decimal`
  - `compute_pending(records: list[DailyRecord], date: date, confirm_delay: int) -> Decimal` —— `records` 为该 fund 按日期升序的全部记录
  - `recompute_fund_totals(fund: Fund) -> int` —— 从 start_date 重算全部记录的 total/pending，返回处理记录数
  - `validate_ratio(profit: Decimal, prev_total: Decimal, given_ratio: Decimal|None, tolerance=Decimal("0.005")) -> tuple[bool, Decimal]`
  - `validate_total(fund: Fund, current_total: Decimal) -> dict` —— 返回 `{"ok": bool, "last_total": Decimal, "diff": Decimal}`

- [ ] **Step 1: 写失败测试** `funds/tests/test_services.py`（用 6/1 spec 示例）

```python
from datetime import date
from decimal import Decimal
from django.test import TestCase
from accounts.models import User
from funds.models import Fund, DailyRecord
from funds import services as S


def _d(x): return Decimal(str(x))


class ServicesTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("u", "u@e.com", "x")
        self.fund = Fund.objects.create(
            user=self.user, name="A", market="CN", confirm_delay=1,
            invest_amount=5, invest_frequency="DAILY",
            start_date=date(2026, 6, 1), start_total=_d(10))

    def _seed(self):
        """6/1 基准 + 6/2,6/3 有盈亏。"""
        DailyRecord.objects.create(fund=self.fund, date=date(2026, 6, 1), invested=_d(5), has_trade=True)
        DailyRecord.objects.create(fund=self.fund, date=date(2026, 6, 2), profit=_d(0.84), invested=_d(5), has_trade=True)
        DailyRecord.objects.create(fund=self.fund, date=date(2026, 6, 3), profit=_d(1.20), invested=_d(5), has_trade=True)

    def test_compute_total(self):
        self.assertEqual(S.compute_total(_d(10), _d(0.84), _d(5)), _d("15.84"))
        self.assertEqual(S.compute_total(_d(10), None, _d(5)), _d("15"))   # 首日 profit 视为 0

    def test_pending_t_plus_1(self):
        self._seed()
        recs = list(self.fund.records.order_by("date"))
        # 6/2：T+1 待确认 = 当天 invested = 5
        self.assertEqual(S.compute_pending(recs, date(2026, 6, 2), 1), _d("5"))

    def test_pending_t_plus_2(self):
        self.fund.confirm_delay = 2
        self.fund.save()
        self._seed()
        recs = list(self.fund.records.order_by("date"))
        # 6/3：T+2 待确认 = 6/2 + 6/3 的 invested
        self.assertEqual(S.compute_pending(recs, date(2026, 6, 3), 2), _d("10"))

    def test_recompute_totals_matches_spec(self):
        self._seed()
        S.recompute_fund_totals(self.fund)
        recs = {r.date: r for r in self.fund.records.all()}
        self.assertEqual(recs[date(2026, 6, 1)].total, _d("10.00"))     # 起点
        self.assertEqual(recs[date(2026, 6, 1)].pending, _d("5.00"))
        self.assertEqual(recs[date(2026, 6, 2)].total, _d("15.84"))
        self.assertEqual(recs[date(2026, 6, 3)].total, _d("22.04"))

    def test_validate_ratio_ok_and_bad(self):
        ok, ratio = S.validate_ratio(_d(0.84), _d(10), _d("0.084"))
        self.assertTrue(ok)
        ok2, _ = S.validate_ratio(_d(0.84), _d(10), _d("0.05"))   # 实际 8.4%，给 5% 应不通过
        self.assertFalse(ok2)

    def test_validate_total(self):
        self._seed(); S.recompute_fund_totals(self.fund)
        r = S.validate_total(self.fund, _d("22.04"))
        self.assertTrue(r["ok"])
        r2 = S.validate_total(self.fund, _d("99"))
        self.assertFalse(r2["ok"])
```

- [ ] **Step 2: 跑测试确认失败**

```bash
venv/bin/python manage.py test funds.tests.test_services -v 2
```
Expected: FAIL（`services` 无这些函数）

- [ ] **Step 3: 实现 `funds/services.py`**

```python
from datetime import date, timedelta
from decimal import Decimal


def compute_total(prev_total: Decimal, profit, invested) -> Decimal:
    """反推当日总额 = 前日总额 + 当日盈亏 + 当日投入。profit 为空（首日）视为 0。"""
    p = Decimal("0") if profit is None else Decimal(profit)
    i = Decimal("0") if invested is None else Decimal(invested)
    return Decimal(prev_total) + p + i


def compute_pending(records, d: date, confirm_delay: int) -> Decimal:
    """待确认 = 最近 confirm_delay 天（含 d）的 invested 之和。records 为升序列表。"""
    total = Decimal("0")
    for k in range(confirm_delay):
        cur = d - timedelta(days=k)
        for r in records:
            if r.date == cur:
                total += Decimal(r.invested or 0)
                break
    return total


def recompute_fund_totals(fund) -> int:
    """从 fund.start_date 起逐日重算 total 与 pending。返回处理记录数。"""
    records = list(fund.records.order_by("date"))
    if not records:
        return 0
    prev = Decimal(fund.start_total)
    first = True
    for r in records:
        if first:                       # 首日：total = start_total；profit 忽略
            r.total = Decimal(fund.start_total)
            r.pending = compute_pending(records, r.date, fund.confirm_delay)
            prev = r.total
            first = False
        else:
            r.total = compute_total(prev, r.profit, r.invested)
            r.pending = compute_pending(records, r.date, fund.confirm_delay)
            prev = r.total
        r.save()
    return len(records)


def validate_ratio(profit, prev_total, given_ratio, tolerance=Decimal("0.005")):
    """比例校验：返回 (是否一致, 系统计算的比例)。given_ratio 为空则跳过（返回 True, None）。"""
    if given_ratio is None or prev_total == 0:
        return True, None
    p = Decimal("0") if profit is None else Decimal(profit)
    computed = p / Decimal(prev_total)
    return abs(computed - Decimal(given_ratio)) <= tolerance, computed


def validate_total(fund, current_total) -> dict:
    """终点总额校验：比较最后一条记录的 total 与 current_total。容差 0.01。"""
    last = fund.records.order_by("date").last()
    if last is None:
        return {"ok": False, "last_total": None, "diff": None}
    diff = Decimal(last.total) - Decimal(current_total)
    return {"ok": abs(diff) <= Decimal("0.01"), "last_total": last.total, "diff": diff}
```

- [ ] **Step 4: 跑测试确认通过**

```bash
venv/bin/python manage.py test funds.tests.test_services -v 2
```
Expected: OK（6 tests）—— 这是准确性的命脉，必须全绿

- [ ] **Step 5: Commit**

```bash
git add funds/services.py funds/tests/test_services.py
git commit -m "feat(funds): core calculation services (total/pending/validation)"
```

---

# Phase B — 用户、录入与可视化

## Task 6: 注册 + 邮箱验证

**Files:**
- Create: `accounts/tokens.py`, `accounts/mails.py`, `accounts/forms.py`, `accounts/views.py`, `accounts/urls.py`, `templates/registration/register.html`, `templates/registration/register_done.html`, `templates/accounts/verify_email.html`
- Modify: `config/urls.py`（include accounts.urls）
- Test: `accounts/tests/test_views.py`

**Interfaces:**
- Produces:
  - `accounts.tokens.make_email_verify_token(user) -> str`（基于 `default_token_generator`）
  - `accounts.tokens.check_email_verify_token(user, token) -> bool`
  - 注册视图 `POST /accounts/register/`；验证视图 `GET /accounts/verify/<uidb64>/<token>/`
  - `accounts.mails.send_verification_email(user, request)` 使用 `EMAIL_BACKEND`

- [ ] **Step 1: 写失败测试** `accounts/tests/test_views.py`

```python
from django.test import TestCase, RequestFactory
from django.core import mail
from accounts.models import User

class RegisterViewTest(TestCase):
    def test_register_creates_inactive_and_sends_email(self):
        resp = self.client.post("/accounts/register/", {
            "username": "bob", "email": "bob@e.com",
            "password1": "Str0ng!Pass", "password2": "Str0ng!Pass"})
        self.assertEqual(resp.status_code, 302)
        u = User.objects.get(username="bob")
        self.assertFalse(u.email_verified)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("bob@e.com", mail.outbox[0].to[0])

    def test_verify_link_sets_verified(self):
        from accounts.tokens import make_email_verify_token
        from django.utils.http import urlsafe_base64_encode
        from django.utils.encoding import force_bytes
        u = User.objects.create_user("bob", "bob@e.com", "x")
        token = make_email_verify_token(u)
        uid = urlsafe_base64_encode(force_bytes(u.pk))
        resp = self.client.get(f"/accounts/verify/{uid}/{token}/")
        u.refresh_from_db()
        self.assertTrue(u.email_verified)
```

- [ ] **Step 2: 跑测试确认失败**（路由/视图未定义）

- [ ] **Step 3: 实现 `accounts/tokens.py`**

```python
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth import get_user_model

User = get_user_model()

def make_email_verify_token(user) -> str:
    return default_token_generator.make_token(user)

def check_email_verify_token(user, token) -> bool:
    return default_token_generator.check_token(user, token)
```

- [ ] **Step 4: 实现 `accounts/mails.py`**

```python
from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from .tokens import make_email_verify_token

def send_verification_email(user, request):
    token = make_email_verify_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    link = f"{request.scheme}://{request.get_host()}/accounts/verify/{uid}/{token}/"
    send_mail(
        subject="【基金看板】确认你的邮箱",
        message=f"点击链接确认邮箱：\n{link}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
```

- [ ] **Step 5: 实现 `accounts/forms.py`**

```python
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

User = get_user_model()

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")
```

- [ ] **Step 6: 实现 `accounts/views.py`**（注册 + 验证）

```python
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from .forms import RegisterForm
from .mails import send_verification_email
from .tokens import check_email_verify_token

User = get_user_model()

def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            send_verification_email(user, request)
            return redirect("register_done")
    else:
        form = RegisterForm()
    return render(request, "registration/register.html", {"form": form})

def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
    if user is not None and check_email_verify_token(user, token):
        user.email_verified = True
        user.save()
        return render(request, "accounts/verify_email.html", {"ok": True})
    return render(request, "accounts/verify_email.html", {"ok": False})
```

- [ ] **Step 7: 实现 `accounts/urls.py`**

```python
from django.urls import path
from . import views

urlpatterns = [
    path("register/", views.register, name="register"),
    path("register/done/", lambda r: __import__("django.shortcuts").shortcuts.render(r, "registration/register_done.html"), name="register_done"),
    path("verify/<str:uidb64>/<str:token>/", views.verify_email, name="verify_email"),
]
```

- [ ] **Step 8: 写模板**（结构示意，关键变量给全）
  - `templates/registration/register.html`：`<form method="post">{% csrf_token %}{{ form.as_p }}<button>注册</button></form>`
  - `templates/registration/register_done.html`：「验证邮件已发送，请查收」
  - `templates/accounts/verify_email.html`：`{% if ok %}邮箱已验证{% else %}链接无效或过期{% endif %}`

- [ ] **Step 9: `config/urls.py` include**

```python
urlpatterns += [path("accounts/", include("accounts.urls"))]
```
> 同时 settings 加 `EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"` **仅测试时**——通过测试 settings 覆盖，或在 test 里用 `override_settings`。生产保持 SMTP。

- [ ] **Step 10: 跑测试确认通过**

```bash
venv/bin/python manage.py test accounts.tests.test_views -v 2
```
Expected: OK（用 locmem backend 捕获 mail.outbox）

- [ ] **Step 11: Commit**

```bash
git add accounts/ templates/ config/urls.py
git commit -m "feat(accounts): registration with email verification"
```

---

## Task 7: 登录 + magic link 免密登录

**Files:**
- Modify: `accounts/views.py`, `accounts/urls.py`
- Create: `templates/registration/login.html`
- Test: 追加到 `accounts/tests/test_views.py`

**Interfaces:**
- Produces: `GET /accounts/magic/<token>/` —— 校验 `mail_login_token`，通过则 `login()` 并跳转 `daily-entry`

- [ ] **Step 1: 写失败测试**

```python
from django.urls import reverse

class MagicLinkTest(TestCase):
    def test_valid_token_logs_in(self):
        u = User.objects.create_user("bob", "bob@e.com", "x")
        resp = self.client.get(f"/accounts/magic/{u.mail_login_token}/")
        self.assertEqual(resp.status_code, 302)
        self.assertTrue("_auth_user_id" in self.client.session)

    def test_invalid_token_rejected(self):
        resp = self.client.get("/accounts/magic/nope/")
        self.assertEqual(resp.status_code, 404)
```

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 在 `accounts/views.py` 追加**

```python
from django.contrib.auth import login
from django.http import Http404

def magic_login(request, token):
    try:
        user = User.objects.get(mail_login_token=token)
    except User.DoesNotExist:
        raise Http404
    login(request, user)
    return redirect("daily-entry")     # Task 9 定义此 url name
```

- [ ] **Step 4: 在 `accounts/urls.py` 追加**

```python
path("magic/<str:token>/", views.magic_login, name="magic_login"),
```

- [ ] **Step 5: 加标准登录** —— `accounts/urls.py` 追加：

```python
from django.contrib.auth import views as auth_views
path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
path("logout/", auth_views.LogoutView.as_view(), name="logout"),
```
> settings 加 `LOGIN_REDIRECT_URL = "/"`、`LOGOUT_REDIRECT_URL = "/accounts/login/"`。

- [ ] **Step 6: 跑测试确认通过**

```bash
venv/bin/python manage.py test accounts.tests.test_views -v 2
```

- [ ] **Step 7: Commit**

```bash
git add accounts/ templates/registration/login.html config/settings.py
git commit -m "feat(accounts): magic-link login + standard auth"
```

---

## Task 8: 基金 CRUD + 标签

**Files:**
- Create: `funds/forms.py`, `funds/views.py`, `funds/urls.py`, `templates/funds/fund_list.html`, `templates/funds/fund_form.html`
- Modify: `config/urls.py`
- Test: `funds/tests/test_views.py`

**Interfaces:**
- Produces: 视图 `fund-list`、`fund-create`、`fund-edit`（登录后只操作本人基金）

- [ ] **Step 1: 写失败测试** `funds/tests/test_views.py`

```python
from django.test import TestCase
from accounts.models import User

class FundCrudTest(TestCase):
    def setUp(self):
        self.u = User.objects.create_user("u", "u@e.com", "pwd12345")
        self.client.login(username="u", password="pwd12345")

    def test_create_fund_via_post(self):
        resp = self.client.post("/funds/new/", {
            "name": "A基金", "code": "000001", "market": "CN", "confirm_delay": 1,
            "invest_amount": "5", "invest_frequency": "DAILY", "invest_weekday": 0,
            "start_date": "2026-06-01", "start_total": "10",
            "fund_type": "INDEX", "risk_level": 3, "currency": "CNY",
            "tags-TOTAL_FORMS": "0", "tags-INITIAL_FORMS": "0",  # 如用 formset；否则去掉
        })
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(self.u.funds.count(), 1)

    def test_list_shows_own_funds_only(self):
        from funds.models import Fund
        Fund.objects.create(user=self.u, name="mine", market="CN", confirm_delay=1,
            invest_amount=5, invest_frequency="DAILY", start_date="2026-06-01", start_total=10)
        other = User.objects.create_user("o", "o@e.com", "pwd12345")
        Fund.objects.create(user=other, name="notmine", market="CN", confirm_delay=1,
            invest_amount=5, invest_frequency="DAILY", start_date="2026-06-01", start_total=10)
        resp = self.client.get("/funds/")
        self.assertContains(resp, "mine")
        self.assertNotContains(resp, "notmine")
```

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 实现 `funds/forms.py`**

```python
from django import forms
from .models import Fund, Tag

class FundForm(forms.ModelForm):
    class Meta:
        model = Fund
        fields = ["name", "code", "market", "confirm_delay", "invest_amount",
                  "invest_frequency", "invest_weekday", "start_date", "start_total",
                  "fund_type", "risk_level", "currency", "is_active", "tags"]
        widgets = {"start_date": forms.DateInput(attrs={"type": "date"})}
```

- [ ] **Step 4: 实现 `funds/views.py`**（CRUD，先放 fund 相关；录入/仪表盘在 Task 9/10 追加）

```python
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import Fund
from .forms import FundForm

@login_required
def fund_list(request):
    funds = Fund.objects.filter(user=request.user)
    return render(request, "funds/fund_list.html", {"funds": funds})

@login_required
def fund_create(request):
    form = FundForm(request.POST or None)
    if form.is_valid():
        fund = form.save(commit=False)
        fund.user = request.user
        fund.save()
        form.save_m2m()
        return redirect("fund-list")
    return render(request, "funds/fund_form.html", {"form": form})

@login_required
def fund_edit(request, pk):
    fund = get_object_or_404(Fund, pk=pk, user=request.user)
    form = FundForm(request.POST or None, instance=fund)
    if form.is_valid():
        form.save()
        return redirect("fund-list")
    return render(request, "funds/fund_form.html", {"form": form})
```

- [ ] **Step 5: 实现 `funds/urls.py`**

```python
from django.urls import path
from . import views

urlpatterns = [
    path("", views.fund_list, name="fund-list"),
    path("new/", views.fund_create, name="fund-create"),
    path("<int:pk>/edit/", views.fund_edit, name="fund-edit"),
]
```

- [ ] **Step 6: `config/urls.py` 追加** `path("funds/", include("funds.urls"))`

- [ ] **Step 7: 写模板**（list 表格列出 name/code/market/start_total；form 渲染 `{{ form.as_p }}` + csrf + 提交）

- [ ] **Step 8: 跑测试确认通过**

```bash
venv/bin/python manage.py test funds.tests.test_views -v 2
```

- [ ] **Step 9: Commit**

```bash
git add funds/ templates/funds/ config/urls.py
git commit -m "feat(funds): fund CRUD with tag support"
```

---

## Task 9: 每日批量录入页

**Files:**
- Modify: `funds/views.py`, `funds/forms.py`, `funds/urls.py`
- Create: `templates/funds/daily_entry.html`
- Test: 追加到 `funds/tests/test_views.py`

**Interfaces:**
- Consumes: `services.recompute_fund_totals`、`Fund.is_dca_day`、`services.validate_ratio`
- Produces: 视图 `daily-entry`（GET 显示当日表单；POST 批量保存并重算）；支持「今日无交易」与「+添加新基金」

- [ ] **Step 1: 写失败测试**

```python
from datetime import date
from decimal import Decimal
from funds.models import Fund, DailyRecord

class DailyEntryTest(FundCrudTest):
    def setUp(self):
        super().setUp()
        self.fund = Fund.objects.create(user=self.u, name="A", market="CN", confirm_delay=1,
            invest_amount=Decimal("5"), invest_frequency="DAILY",
            start_date=date(2026, 6, 1), start_total=Decimal("10"))
        DailyRecord.objects.create(fund=self.fund, date=date(2026,6,1), invested=Decimal("5"))  # 起点已存

    def test_post_saves_profit_and_recomputes(self):
        resp = self.client.post("/funds/daily/?date=2026-06-02", {
            "form-TOTAL_FORMS": "1", "form-INITIAL_FORMS": "0",
            "form-0-fund": self.fund.id, "form-0-profit": "0.84",
            "form-0-invested": "5", "form-0-profit_ratio": "",
            "action": "save",
        })
        self.assertEqual(resp.status_code, 302)
        r = DailyRecord.objects.get(fund=self.fund, date=date(2026,6,2))
        self.assertEqual(r.total, Decimal("15.84"))
        self.assertEqual(r.pending, Decimal("5"))

    def test_mark_no_trade(self):
        resp = self.client.post("/funds/daily/?date=2026-06-07", {"action": "no_trade"})  # 周日
        self.assertEqual(resp.status_code, 302)
        r = DailyRecord.objects.get(fund=self.fund, date=date(2026,6,7))
        self.assertFalse(r.has_trade)
```

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 在 `funds/forms.py` 追加 formset**

```python
from django.forms import formset_factory

class DailyEntryForm(forms.Form):
    fund = forms.IntegerField(widget=forms.HiddenInput)
    profit = forms.DecimalField(max_digits=12, decimal_places=2, required=False)
    profit_ratio = forms.DecimalField(max_digits=7, decimal_places=4, required=False)
    invested = forms.DecimalField(max_digits=12, decimal_places=2, required=False)

DailyEntryFormSet = formset_factory(DailyEntryForm, extra=0)
```

- [ ] **Step 4: 在 `funds/views.py` 追加录入视图**

```python
from datetime import date as date_cls
from decimal import Decimal
from .models import DailyRecord
from .forms import DailyEntryFormSet
from . import services

def _today(request):
    d = request.GET.get("date")
    return date_cls.fromisoformat(d) if d else date_cls.today()

@login_required
def daily_entry(request):
    d = _today(request)
    funds = Fund.objects.filter(user=request.user, is_active=True)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "no_trade":
            for f in funds:
                DailyRecord.objects.update_or_create(fund=f, date=d,
                    defaults={"has_trade": False, "invested": Decimal("0")})
            _recompute_all(funds)
            return redirect("daily-entry")
        formset = DailyEntryFormSet(request.POST)
        if formset.is_valid():
            for frm in formset:
                fund = Fund.objects.get(pk=frm.cleaned_data["fund"], user=request.user)
                profit = frm.cleaned_data.get("profit")
                if profit is None and not fund.is_dca_day(d):
                    continue   # 非定投日且没填盈亏 → 不建记录
                invested = frm.cleaned_data.get("invested")
                if invested is None:
                    invested = fund.invest_amount if fund.is_dca_day(d) else Decimal("0")
                DailyRecord.objects.update_or_create(fund=fund, date=d, defaults={
                    "profit": profit or Decimal("0"),
                    "profit_ratio": frm.cleaned_data.get("profit_ratio"),
                    "invested": invested,
                    "has_trade": True,
                })
            _recompute_all(funds)
            return redirect("daily-entry")
    # GET：预填
    initial = []
    for f in funds:
        rec = f.records.filter(date=d).first()
        invested = rec.invested if rec else (f.invest_amount if f.is_dca_day(d) else Decimal("0"))
        initial.append({
            "fund": f.id,
            "profit": rec.profit if rec and rec.has_trade else "",
            "profit_ratio": rec.profit_ratio if rec else "",
            "invested": invested,
        })
    return render(request, "funds/daily_entry.html",
        {"formset": DailyEntryFormSet(initial=initial), "funds": list(funds), "date": d})

def _recompute_all(funds):
    for f in funds:
        services.recompute_fund_totals(f)
```

- [ ] **Step 5: 在 `funds/urls.py` 追加** `path("daily/", views.daily_entry, name="daily-entry")`

- [ ] **Step 6: 写 `daily_entry.html`**（关键结构）：
  - 顶部「日期」+ `[今日无交易]` 按钮（POST `action=no_trade`）+ `[+添加新基金]`（链 `fund-create`）
  - 表单：迭代 `formset` 与 `funds`（用 `zip`），每行显示基金名 + 对应 profit/invested/ratio 输入框
  - 隐藏字段 `form-TOTAL_FORMS/INITIAL_FORMS`（Django formset 自动渲染 `{{ formset.management_form }}`）
  - `[保存今日全部]`（POST `action=save`）

- [ ] **Step 7: 跑测试确认通过**

```bash
venv/bin/python manage.py test funds.tests.test_views.DailyEntryTest -v 2
```

- [ ] **Step 8: Commit**

```bash
git add funds/ templates/funds/daily_entry.html
git commit -m "feat(funds): daily batch entry page with recompute"
```

---

## Task 10: 仪表盘 + 日历 + 走势图

**Files:**
- Modify: `funds/views.py`, `funds/urls.py`
- Create: `templates/base.html`, `templates/funds/dashboard.html`, `templates/funds/fund_detail.html`, `static/js/`（Chart.js 用 CDN）
- Test: 追加到 `funds/tests/test_views.py`

**Interfaces:**
- Consumes: `services`（取最后 total/profit 求和）
- Produces: 视图 `dashboard`（组合总览+日历）、`fund-detail`（走势 JSON）；根 `/` 重定向 dashboard

- [ ] **Step 1: 写失败测试**

```python
class DashboardTest(FundCrudTest):
    def setUp(self):
        super().setUp()
        from datetime import date
        self.fund = Fund.objects.create(user=self.u, name="A", market="CN", confirm_delay=1,
            invest_amount=Decimal("5"), invest_frequency="DAILY",
            start_date=date(2026,6,1), start_total=Decimal("10"))
        DailyRecord.objects.create(fund=self.fund, date=date(2026,6,1), invested=Decimal("5"), total=Decimal("10"))

    def test_dashboard_shows_totals(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "10")   # 总市值

    def test_fund_detail_returns_json(self):
        resp = self.client.get(f"/funds/{self.fund.pk}/")
        self.assertEqual(resp["Content-Type"], "application/json")
```

- [ ] **Step 2: 跑测试确认失败**

- [ ] **Step 3: 在 `funds/views.py` 追加**

```python
from django.http import JsonResponse

@login_required
def dashboard(request):
    funds = Fund.objects.filter(user=request.user)
    total_value = sum((f.records.order_by("-date").first().total for f in funds if f.records.exists()), Decimal("0"))
    total_invested = sum((f.records.aggregate(s=models.Sum("invested"))["s"] or Decimal("0") for f in funds), Decimal("0"))
    total_profit = sum((f.records.filter(has_trade=True).aggregate(s=models.Sum("profit"))["s"] or Decimal("0") for f in funds), Decimal("0"))
    return render(request, "funds/dashboard.html", {
        "funds": funds, "total_value": total_value,
        "total_invested": total_invested, "total_profit": total_profit,
        "ratio": (total_profit / total_invested) if total_invested else 0,
    })

@login_required
def fund_detail(request, pk):
    fund = get_object_or_404(Fund, pk=pk, user=request.user)
    recs = fund.records.order_by("date")
    return JsonResponse({"dates": [r.date.isoformat() for r in recs],
                         "totals": [str(r.total) for r in recs],
                         "profits": [str(r.profit or 0) for r in recs]})
```
> views.py 顶部加 `from django.db.models import Sum` 并 `from decimal import Decimal`、`from . import models`（或直接 `from funds.models import ...`，保持与已有 import 一致）。

- [ ] **Step 4: 在 `funds/urls.py` 追加**

```python
path("fund/<int:pk>/", views.fund_detail, name="fund-detail"),
```

- [ ] **Step 5: `config/urls.py`** 把根 `/` 指向 dashboard：

```python
from funds import views as fund_views
urlpatterns += [path("", fund_views.dashboard, name="dashboard")]
```

- [ ] **Step 6: 写模板**
  - `base.html`：Bootstrap 5 CDN + 导航（首页/基金/录入/登出）+ `{% block content %}`
  - `dashboard.html`：4 个总览卡片（总市值/总投入/总盈亏/收益率）+ 基金列表（链 fund-detail）+ 日历占位（可先用基金列表代替，日历网格作为 follow-up）
  - `fund_detail.html`：`<canvas id="chart">` + 引入 Chart.js CDN + fetch `/funds/<pk>/` 拿 JSON 画 total/profit 双线图（日/周/月/年按钮先做"日"全量，其余阶段化）

- [ ] **Step 7: 跑测试确认通过**

```bash
venv/bin/python manage.py test funds.tests.test_views.DashboardTest -v 2
```

- [ ] **Step 8: Commit**

```bash
git add funds/ templates/ static/ config/urls.py
git commit -m "feat(funds): dashboard overview + fund detail chart"
```

---

# Phase C — 邮件驱动与部署

## Task 11: 邮件系统 + 阶梯提醒 + finalize

**Files:**
- Create: `funds/management/__init__.py`, `funds/management/commands/__init__.py`, `funds/management/commands/send_daily_email.py`, `funds/management/commands/finalize_daily.py`, `accounts/mails.py`（追加 `send_daily_entry_email`）
- Test: `funds/tests/test_commands.py`
- Modify: `.env`（填真实 SMTP 授权码）

**Interfaces:**
- Consumes: `User.mail_login_token`、`DailyRecord`（判断今日是否已录入）
- Produces: 命令 `send_daily_email`（参数 `--reminder 1|2|3`）、`finalize_daily`

- [ ] **Step 1: 在 `accounts/mails.py` 追加**

```python
def send_daily_entry_email(user, request_host, reminder):
    link = f"{request_host}/accounts/magic/{user.mail_login_token}/"
    title = "【基金看板】录入今日盈亏" + (f"（第{reminder}次提醒）" if reminder > 1 else "")
    send_mail(subject=title,
        message=f"今日有交易请点：{link}\n如今日无交易，点开后按「今日无交易」。",
        from_email=settings.DEFAULT_FROM_EMAIL, recipient_list=[user.email], fail_silently=False)
```

- [ ] **Step 2: 写失败测试** `funds/tests/test_commands.py`（用 locmem backend）

```python
from datetime import date
from django.test import TestCase, override_settings
from django.core import mail
from django.core.management import call_command
from accounts.models import User
from funds.models import Fund, DailyRecord

@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class CommandTest(TestCase):
    def setUp(self):
        self.u = User.objects.create_user("u", "u@e.com", "x", email_verified=True)
        Fund.objects.create(user=self.u, name="A", market="CN", confirm_delay=1,
            invest_amount=5, invest_frequency="DAILY", start_date=date(2026,6,1), start_total=10)

    def test_weekend_sends_weekend_mail(self):
        # 2026-06-06 是周六
        call_command("send_daily_email", date="2026-06-06")
        self.assertIn("周末", mail.outbox[-1].subject)

    def test_weekday_sends_entry_link_when_not_recorded(self):
        call_command("send_daily_email", date="2026-06-02", reminder=1)
        self.assertIn("/accounts/magic/", mail.outbox[-1].body)

    def test_no_mail_when_already_recorded(self):
        DailyRecord.objects.create(fund=self.u.funds.first(), date=date(2026,6,2), profit=1, invested=5)
        call_command("send_daily_email", date="2026-06-02")
        self.assertEqual(len(mail.outbox), 0)

    def test_finalize_marks_no_trade(self):
        call_command("finalize_daily", date="2026-06-02")
        r = DailyRecord.objects.get(fund=self.u.funds.first(), date=date(2026,6,2))
        self.assertFalse(r.has_trade)
```

- [ ] **Step 3: 跑测试确认失败**

- [ ] **Step 4: 实现 `send_daily_email.py`**

```python
from datetime import date
from django.core.management.base import BaseCommand
from django.conf import settings
from accounts.models import User
from funds.models import DailyRecord
from accounts.mails import send_daily_entry_email, send_mail
from django.core.mail import send_mail as _send

class Command(BaseCommand):
    help = "每日邮件提醒（阶梯）"
    def add_arguments(self, p):
        p.add_argument("--date", default=None)
        p.add_argument("--reminder", type=int, default=1)
    def handle(self, *a, **o):
        d = date.fromisoformat(o["date"]) if o["date"] else date.today()
        host = "http://49.234.26.95:8188"
        for u in User.objects.filter(email_verified=True, is_active=True):
            if d.weekday() >= 5:
                _send(subject="【基金看板】周末愉快 🌿",
                    message="周末不交易，好好休息～",
                    from_email=settings.DEFAULT_FROM_EMAIL, recipient_list=[u.email])
                continue
            already = DailyRecord.objects.filter(fund__user=u, date=d).exists()
            if already:
                continue
            send_daily_entry_email(u, host, o["reminder"])
        self.stdout.write(self.style.SUCCESS(f"sent for {d}"))
```

- [ ] **Step 5: 实现 `finalize_daily.py`**

```python
from datetime import date
from decimal import Decimal
from django.core.management.base import BaseCommand
from accounts.models import User
from funds.models import DailyRecord
from funds import services

class Command(BaseCommand):
    help = "23:30 未录入则标记无交易"
    def add_arguments(self, p):
        p.add_argument("--date", default=None)
    def handle(self, *a, **o):
        d = date.fromisoformat(o["date"]) if o["date"] else date.today()
        for u in User.objects.filter(is_active=True):
            for f in u.funds.filter(is_active=True):
                if not f.records.filter(date=d).exists():
                    DailyRecord.objects.create(fund=f, date=d, has_trade=False, invested=Decimal("0"))
            for f in u.funds.filter(is_active=True):
                services.recompute_fund_totals(f)
        self.stdout.write(self.style.SUCCESS(f"finalized {d}"))
```

- [ ] **Step 6: 跑测试确认通过**

```bash
venv/bin/python manage.py test funds.tests.test_commands -v 2
```

- [ ] **Step 7: 填真实 SMTP 授权码到 `.env`**（用户生成新码后，手动写入，不入 git）
```
EMAIL_HOST_PASSWORD=<用户在服务器上手填新码>
```

- [ ] **Step 8: 手动冒烟测试发信**

```bash
venv/bin/python manage.py send_daily_email --date 2026-06-02
```
Expected: 终端输出 `sent for 2026-06-02`，用户邮箱收到邮件。

- [ ] **Step 9: Commit**（不含 .env）

```bash
git add funds/management accounts/mails.py
git commit -m "feat(funds): daily email reminders + finalize command"
```

---

## Task 12: 部署上线（端口 8188）+ crontab

**Files:**
- 无代码改动；配置 crontab + nohup 启动 runserver
- 前置：用户已在腾讯云安全组放行 TCP 8188

- [ ] **Step 1: 收集静态文件**

```bash
cd ~/home/claude_PJ/Jijin_Kanban
venv/bin/python manage.py collectstatic --noinput
```

- [ ] **Step 2: 后台启动 runserver**

```bash
nohup venv/bin/python manage.py runserver 0.0.0.0:8188 > server.log 2>&1 &
```

- [ ] **Step 3: 本地（服务器上）验证监听**

```bash
ss -tlnp | grep 8188
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8188/
```
Expected: 监听 `0.0.0.0:8188`；curl 返回 `200` 或 `302`（重定向登录）

- [ ] **Step 4: 用户本地访问 `http://49.234.26.95:8188/`** —— 应看到登录/注册页

> 若访问超时 → 腾讯云安全组未放行 8188（回去检查入站规则 TCP 8188 0.0.0.0/0）

- [ ] **Step 5: 配置 crontab（阶梯提醒 + finalize）**

```bash
crontab -e
```
写入：
```
# 工作日阶梯提醒（18/21/23 点）
0 18 * * * cd /home/ubuntu/home/claude_PJ/Jijin_Kanban && venv/bin/python manage.py send_daily_email --reminder 1
0 21 * * * cd /home/ubuntu/home/claude_PJ/Jijin_Kanban && venv/bin/python manage.py send_daily_email --reminder 2
0 23 * * * cd /home/ubuntu/home/claude_PJ/Jijin_Kanban && venv/bin/python manage.py send_daily_email --reminder 3
# 23:30 finalize 未录入
30 23 * * * cd /home/ubuntu/home/claude_PJ/Jijin_Kanban && venv/bin/python manage.py finalize_daily
```

- [ ] **Step 6: 写运维说明到 `docs/DEPLOY.md`**（记录启动命令、crontab、安全组、如何换授权码、如何停服务）

- [ ] **Step 7: Commit**

```bash
git add docs/DEPLOY.md
git commit -m "docs: deployment guide and crontab"
```

---

## Self-Review（已执行）

- **Spec 覆盖**：模型(Task2-4)、计算(Task5)、注册/邮箱验证(Task6)、magic link(Task7)、基金CRUD(Task8)、批量录入(Task9)、仪表盘/走势(Task10)、邮件阶梯+finalize(Task11)、部署(Task12)——spec 每节均有任务覆盖。日历视图 MVP 简化为基金列表，完整月历网格列为 follow-up（spec 7.5 允许阶段化）。
- **占位符扫描**：无 TBD/TODO；模板步骤给了关键结构而非逐行 HTML（对模板量大项的合理处理，关键变量与 form 字段均给全）。
- **类型一致**：`services` 签名（compute_total/compute_pending/recompute_fund_totals/validate_ratio/validate_total）在 Task5 定义后，Task9/10/11 调用名一致；`is_dca_day`、`mail_login_token`、`DailyRecord.has_trade` 跨任务命名统一。
- **金额一致性**：全链路 `DecimalField(12,2)` + `Decimal`，测试断言用 `Decimal`。
