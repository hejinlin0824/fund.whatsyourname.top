# AI 智能体分析功能 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在基金看板新建 `aiagent` app，每日结合新闻+仓位生成结构化 AI 报告，午间/晚间各发一封邮件，站内可翻阅历史、可随时触发（限额）。

**Architecture:** 独立 Django app `aiagent`；两段式 LLM 流水线（chat 初筛标题 → chat/reasoner 深读摘要+仓位）；DeepSeek 走 `requests` HTTP；API key 用 Fernet 加密存库；management command + cron 调度；报告结构化 JSON → HTML 渲染（邮件+站内共用）。

**Tech Stack:** Python 3.12 · Django 6.0 · DRF(已有) · `cryptography`(Fernet, 新增) · `requests`(已有) · DeepSeek HTTP API · cron + management commands。

## Global Constraints

- **执行方式（远程仓库，省额度）**：本地在 `E:\codebase\server_stuff\_jk\` 改文件（文件名带前缀 `aiagent_*`/`funds_*`/`accounts_*`/`news_*`/`config_*`/`tpl_*`，scp 时映射到真实路径）→ **一条 scp** 传所有改动 → **一条** `ssh ubuntu@49.234.26.95 'cd ~/home/claude_PJ/Jijin_Kanban && bash deploy.sh'`。`deploy.sh` 自动跑 `makemigrations → migrate → 全量测试(失败即中止) → collectstatic → 重启 :8188 → 健康检查`。**测试是硬门槛**。
- **单跑某测试（不重启）**：`ssh ubuntu@49.234.26.95 'cd ~/home/claude_PJ/Jijin_Kanban && venv/bin/python manage.py test aiagent[.tests.test_xxx]'`。
- **提交在服务器**：每任务末尾 `ssh ... 'cd ... && git add <files> && git commit -m "..."'`。
- **测试框架**：Django 内置（`manage.py test`），测试放 `aiagent/tests/` 包（仿现有 `accounts/tests/`、`funds/tests/`）。
- **绝不静默失败**：key 缺失/失效/限流 → 降级报告（`status=degraded`）+ 邮件照发（正文置顶说明）。
- **口径一致**：投入金额用扣费后 `effective_invested`（见 `funds/models.py`），与 `recompute_fund_totals` 一致。
- **密钥**：`JK_FERNET_KEY` 放 `.env`（gitignore），缺失时 `crypto.get_fernet()` 自动生成并追加。
- **报告固定带免责声明**：AI 生成，不构成投资建议。
- **命名**：app `aiagent`；模型 `AnalysisReport`；报告类型常量 `morning`/`evening`/`ondemand`。

## File Structure

```
aiagent/
├─ __init__.py apps.py admin.py urls.py        # app 骨架 + 路由
├─ models.py            # AnalysisReport（条件唯一约束）
├─ crypto.py            # Fernet encrypt/decrypt_key + get_fernet
├─ client.py            # DeepSeek HTTP：call/chat/reasoner，重试+错误归一化
├─ context.py           # news_titles_by_category + portfolio_text
├─ prompts.py           # SCREENING_PROMPT / ANALYSIS_PROMPT_NOON/EVENING
├─ screening.py         # screen() 第①阶段
├─ analysis.py          # analyze() 第②阶段 → 结构化 JSON
├─ reports.py           # render(analysis,type) → HTML（5 段）
├─ services.py          # generate_report() 编排 + 降级
├─ emails.py            # send_report_email()
├─ forms.py             # DeepSeekKeyForm
├─ views.py             # report_list/detail/on_demand/key_settings
├─ management/commands/{run_ai_morning,run_ai_evening}.py
└─ tests/{__init__,test_crypto,test_models,test_snapshot,test_client,
         test_context,test_screening,test_analysis,test_reports,
         test_services,test_emails,test_commands,test_views}.py
templates/aiagent/{report_list,report_detail,key_settings,_report_body,
                   emails/morning,emails/evening}.html
funds/services.py            # + portfolio_snapshot(user)
accounts/models.py           # + deepseek_key_enc + property/setter(用 crypto)
news/models.py               # CATEGORY_CHOICES + finance_oversea
config/settings.py           # INSTALLED_APPS += aiagent
config/urls.py               # include aiagent.urls
templates/base.html          # nav += 「AI报告」
requirements.txt             # += cryptography
```

---

## Task 1: Scaffold `aiagent` app + 接线 + 依赖

**Files:**
- Create: `aiagent/__init__.py`, `aiagent/apps.py`, `aiagent/admin.py`, `aiagent/migrations/__init__.py`, `aiagent/tests/__init__.py`, `aiagent/urls.py`
- Modify: `config/settings.py`(INSTALLED_APPS), `config/urls.py`(include), `templates/base.html`(nav), `requirements.txt`

**Interfaces:**
- Produces: 已注册的 `aiagent` app；空 `aiagent/urls.py`；nav 链接 `/aiagent/`（目标页 Task 12 实现，先指向占位 `#`）。

- [ ] **Step 1: 生成 app 骨架**

`ssh ubuntu@49.234.26.95 'cd ~/home/claude_PJ/Jijin_Kanban && venv/bin/python manage.py startapp aiagent && mkdir -p aiagent/management/commands aiagent/tests aiagent/migrations && touch aiagent/management/__init__.py aiagent/management/commands/__init__.py aiagent/tests/__init__.py aiagent/migrations/__init__.py'`

- [ ] **Step 2: 写验证测试（app 已装、根 URL 不 500）**

`aiagent/tests/test_scaffold.py`:
```python
from django.test import TestCase
from django.apps import apps

class ScaffoldTest(TestCase):
    def test_app_installed(self):
        self.assertTrue(apps.is_installed("aiagent"))
```

- [ ] **Step 3: 改 `config/settings.py`**

INSTALLED_APPS 末尾加 `"aiagent",`（在 `"news",` 之后）。

- [ ] **Step 4: 写 `aiagent/urls.py`（空，占位）**
```python
from django.urls import path

app_name = "aiagent"
urlpatterns = []  # Task 12 填充
```

- [ ] **Step 5: 改 `config/urls.py`**

在 `path("news/", ...)` 后加：
```python
path("aiagent/", include("aiagent.urls")),
```

- [ ] **Step 6: 改 `templates/base.html` nav**

加一项 `<a class="nav-link" href="/aiagent/">AI报告</a>`（沿用现有 nav 结构）。

- [ ] **Step 7: `requirements.txt` 末尾加 `cryptography==45.0.5`**

- [ ] **Step 8: 部署 + 验证**

`scp`（多源，映射到真实路径）后 `ssh ... 'cd ... && bash deploy.sh'`。
Expected：`manage.py test` 全绿（含新 `test_scaffold`）；`:8188` 健康检查 200。

- [ ] **Step 9: Commit**
```bash
ssh ... 'cd ~/home/claude_PJ/Jijin_Kanban && git add aiagent config templates requirements.txt && git commit -m "feat(aiagent): scaffold app + wiring + cryptography dep"'
```

---

## Task 2: `crypto.py`（Fernet 加解密）

**Files:**
- Create: `aiagent/crypto.py`
- Test: `aiagent/tests/test_crypto.py`

**Interfaces:**
- Produces: `encrypt_key(plain:str)->str`、`decrypt_key(enc:str)->str`、`get_fernet()->Fernet`。

- [ ] **Step 1: 写失败测试**
```python
# aiagent/tests/test_crypto.py
import os
from django.test import TestCase
from aiagent import crypto

class CryptoTest(TestCase):
    def setUp(self):
        os.environ["JK_FERNET_KEY"] = "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg="  # 固定 32 字节 base64

    def test_roundtrip(self):
        enc = crypto.encrypt_key("sk-test-123")
        self.assertNotEqual(enc, "sk-test-123")
        self.assertEqual(crypto.decrypt_key(enc), "sk-test-123")

    def test_empty(self):
        self.assertEqual(crypto.encrypt_key(""), "")
        self.assertEqual(crypto.decrypt_key(""), "")
```

- [ ] **Step 2: 跑，确认失败** — `venv/bin/python manage.py test aiagent.tests.test_crypto` → ModuleNotFoundError。

- [ ] **Step 3: 实现 `aiagent/crypto.py`**
```python
import os
from cryptography.fernet import Fernet
from django.conf import settings

def get_fernet() -> Fernet:
    key = os.environ.get("JK_FERNET_KEY") or getattr(settings, "JK_FERNET_KEY", None)
    if not key:
        key = Fernet.generate_key().decode()
        env_path = settings.BASE_DIR / ".env"
        with open(env_path, "a") as f:
            f.write(f"\nJK_FERNET_KEY={key}\n")
        os.environ["JK_FERNET_KEY"] = key
    return Fernet(key.encode() if isinstance(key, str) else key)

def encrypt_key(plain: str) -> str:
    if not plain:
        return ""
    return get_fernet().encrypt(plain.encode()).decode()

def decrypt_key(enc: str) -> str:
    if not enc:
        return ""
    return get_fernet().decrypt(enc.encode()).decode()
```

- [ ] **Step 4: 跑，确认通过** → PASS。
- [ ] **Step 5: Commit** — `git add aiagent/crypto.py aiagent/tests/test_crypto.py && git commit -m "feat(aiagent): Fernet key encryption helpers"`

---

## Task 3: 模型 — `User.deepseek_key_enc` + `AnalysisReport`

**Files:**
- Modify: `accounts/models.py`, `aiagent/models.py`
- Create: `accounts/migrations/<auto>`, `aiagent/migrations/0001_initial.py`
- Test: `aiagent/tests/test_models.py`

**Interfaces:**
- Consumes: `aiagent.crypto.encrypt_key/decrypt_key`
- Produces: `User.deepseek_key`(property, 明文) / `User.set_deepseek_key(plain)`；`AnalysisReport` 模型，常量 `TYPE_CHOICES`、`MORNING/EVENING/ONDEMAND`。

- [ ] **Step 1: 写失败测试**
```python
# aiagent/tests/test_models.py
from datetime import date
import os
from django.test import TestCase
from accounts.models import User
from aiagent.models import AnalysisReport

class UserModelTest(TestCase):
    def setUp(self):
        os.environ["JK_FERNET_KEY"] = "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg="

    def test_key_roundtrip_via_user(self):
        u = User.objects.create_user(username="t", password="p", email="t@e.com")
        u.set_deepseek_key("sk-abc")
        u.save()
        u.refresh_from_db()
        self.assertNotEqual(u.deepseek_key_enc, "sk-abc")   # 密文
        self.assertEqual(u.deepseek_key, "sk-abc")          # 明文读回

    def test_no_key_returns_empty(self):
        u = User.objects.create_user(username="t2", password="p", email="t2@e.com")
        self.assertEqual(u.deepseek_key, "")

class ReportModelTest(TestCase):
    def test_create_and_unique_timed(self):
        u = User.objects.create_user(username="t3", password="p", email="t3@e.com")
        AnalysisReport.objects.create(user=u, type="morning", date=date(2026,7,30))
        from django.db import IntegrityError, transaction
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                AnalysisReport.objects.create(user=u, type="morning", date=date(2026,7,30))

    def test_ondemand_allows_many(self):
        u = User.objects.create_user(username="t4", password="p", email="t4@e.com")
        AnalysisReport.objects.create(user=u, type="ondemand", date=date(2026,7,30))
        AnalysisReport.objects.create(user=u, type="ondemand", date=date(2026,7,30))
        self.assertEqual(AnalysisReport.objects.filter(user=u, type="ondemand").count(), 2)
```

- [ ] **Step 2: 跑，确认失败**（字段/模型不存在）。

- [ ] **Step 3: 改 `accounts/models.py`**
```python
import secrets
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    email = models.EmailField(unique=True)
    email_verified = models.BooleanField(default=False)
    mail_login_token = models.CharField(max_length=64, default="")
    deepseek_key_enc = models.CharField(max_length=512, blank=True, default="")

    @staticmethod
    def generate_token() -> str:
        return secrets.token_urlsafe(24)[:32]

    @property
    def deepseek_key(self) -> str:
        if not self.deepseek_key_enc:
            return ""
        from aiagent.crypto import decrypt_key
        try:
            return decrypt_key(self.deepseek_key_enc)
        except Exception:
            return ""

    def set_deepseek_key(self, plain: str) -> None:
        from aiagent.crypto import encrypt_key
        self.deepseek_key_enc = encrypt_key(plain) if plain else ""

    def save(self, *args, **kwargs):
        if not self.mail_login_token:
            self.mail_login_token = User.generate_token()
        super().save(*args, **kwargs)
```

- [ ] **Step 4: 写 `aiagent/models.py`**
```python
from django.conf import settings
from django.db import models
from django.db.models import Q

MORNING, EVENING, ONDEMAND = "morning", "evening", "ondemand"
TYPE_CHOICES = [(MORNING, "午间"), (EVENING, "晚间"), (ONDEMAND, "手动")]
STATUS_CHOICES = [("ok", "ok"), ("degraded", "degraded"), ("failed", "failed")]

class AnalysisReport(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ai_reports")
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
```

- [ ] **Step 5: 生成迁移 + 部署**
`scp` 后 `ssh ... 'cd ... && bash deploy.sh'`（deploy.sh 内 makemigrations+migrate 自动生成两个迁移并应用；测试全绿）。
Expected：`test_models` PASS；`AnalysisReport` 表建好。

- [ ] **Step 6: Commit** — `git add accounts aiagent && git commit -m "feat(aiagent): User deepseek key + AnalysisReport model"`

---

## Task 4: `funds/services.portfolio_snapshot(user)`

**Files:**
- Modify: `funds/services.py`
- Test: `aiagent/tests/test_snapshot.py`

**Interfaces:**
- Produces: `portfolio_snapshot(user) -> dict`（结构见下）。

返回结构：
```python
{"total_mv": str, "total_cost": str, "total_profit": str, "total_roi": str,
 "funds": [{"name","code","market","fund_type","currency","is_active",
            "mv","cost","profit","roi","last_date","trend_14d":[(iso_date,profit_str),...]}, ...]}
```
（数值一律 `str(Decimal)`，避免 JSON 序列化精度问题。）

- [ ] **Step 1: 写失败测试**
```python
# aiagent/tests/test_snapshot.py
from datetime import date
from decimal import Decimal
from django.test import TestCase
from accounts.models import User
from funds.models import Fund
from funds.services import portfolio_snapshot, backfill_fund

class SnapshotTest(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username="s", password="p", email="s@e.com")
        self.f = Fund.objects.create(
            user=self.u, name="南方纳斯达克100", code="160213", market="US",
            invest_amount=Decimal("100"), start_date=date(2026,7,1), start_total=Decimal("0"))
        backfill_fund(self.f)  # 建槽位

    def test_snapshot_shape(self):
        snap = portfolio_snapshot(self.u)
        self.assertIn("funds", snap)
        self.assertEqual(snap["funds"][0]["name"], "南方纳斯达克100")
        self.assertEqual(snap["funds"][0]["market"], "US")
        for k in ("mv","cost","profit","roi","total_mv","total_roi"):
            self.assertIn(k, {**snap["funds"][0], **snap})

    def test_empty_user(self):
        u2 = User.objects.create_user(username="s2", password="p", email="s2@e.com")
        snap = portfolio_snapshot(u2)
        self.assertEqual(snap["funds"], [])
        self.assertEqual(snap["total_mv"], "0")
```

- [ ] **Step 2: 跑，确认失败**（`portfolio_snapshot` 未定义）。

- [ ] **Step 3: 改 `funds/services.py`（追加函数）**
```python
def portfolio_snapshot(user) -> dict:
    """用户仓位快照（纯数据，供 aiagent 等外部消费）。"""
    from .models import Fund
    funds_out = []
    for f in Fund.objects.filter(user=user):
        s = _fund_summary(f)
        trend = list(
            f.records.exclude(profit__isnull=True)
             .order_by("-date").values_list("date", "profit")[:14])
        funds_out.append({
            "name": f.name, "code": f.code, "market": f.market,
            "fund_type": f.fund_type, "currency": f.currency, "is_active": f.is_active,
            "mv": str(s["mv"]), "cost": str(s["cost"]),
            "profit": str(s["profit"]), "roi": str(s["roi"]),
            "last_date": s["last_date"].isoformat() if s["last_date"] else None,
            "trend_14d": [(d.isoformat(), str(p)) for d, p in reversed(trend)],
        })
    tot_mv = sum((Decimal(x["mv"]) for x in funds_out), Decimal("0"))
    tot_cost = sum((Decimal(x["cost"]) for x in funds_out), Decimal("0"))
    tot_profit = tot_mv - tot_cost
    tot_roi = (tot_profit / tot_cost * 100) if tot_cost else Decimal("0")
    return {"total_mv": str(tot_mv), "total_cost": str(tot_cost),
            "total_profit": str(tot_profit), "total_roi": str(tot_roi),
            "funds": funds_out}
```

- [ ] **Step 4: 跑，确认通过** → PASS。
- [ ] **Step 5: Commit** — `git add funds/services.py aiagent/tests/test_snapshot.py && git commit -m "feat(funds): portfolio_snapshot(user) for AI consumption"`

---

## Task 5: `aiagent/client.py`（DeepSeek HTTP）

**Files:**
- Create: `aiagent/client.py`
- Test: `aiagent/tests/test_client.py`

**Interfaces:**
- Consumes: `user.deepseek_key`
- Produces: `call(user, messages, model, json_mode, timeout) -> dict`、`chat(...)`、`reasoner(...)`。返回 `{"ok":bool,"content":str|None,"usage":dict|None,"error":str|None,"status":int|None}`。`error` 取值集合：`no_api_key`/`invalid_api_key`/`http<n>`/`network:<...>`。

- [ ] **Step 1: 写失败测试**
```python
# aiagent/tests/test_client.py
import os
from unittest import mock
from django.test import TestCase
from accounts.models import User
from aiagent import client

def _resp(status, body=None):
    r = mock.Mock()
    r.status_code = status
    r.json.return_value = body or {}
    return r

class ClientTest(TestCase):
    def setUp(self):
        os.environ["JK_FERNET_KEY"] = "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg="
        self.u = User.objects.create_user(username="c", password="p", email="c@e.com")
        self.u.set_deepseek_key("sk-test"); self.u.save()

    @mock.patch("aiagent.client.requests.post")
    def test_chat_ok(self, post):
        post.return_value = _resp(200, {"choices":[{"message":{"content":"hi"}}], "usage":{"total_tokens":10}})
        res = client.chat(self.u, [{"role":"user","content":"hi"}])
        self.assertTrue(res["ok"]); self.assertEqual(res["content"], "hi"); self.assertEqual(res["usage"]["total_tokens"], 10)

    def test_no_key(self):
        u2 = User.objects.create_user(username="c2", password="p", email="c2@e.com")
        res = client.chat(u2, [{"role":"user","content":"hi"}])
        self.assertFalse(res["ok"]); self.assertEqual(res["error"], "no_api_key")

    @mock.patch("aiagent.client.requests.post")
    @mock.patch("aiagent.client.time.sleep")
    def test_retry_then_ok(self, sleep, post):
        post.side_effect = [_resp(500), _resp(200, {"choices":[{"message":{"content":"ok"}}]})]
        res = client.chat(self.u, [{"role":"user","content":"x"}])
        self.assertTrue(res["ok"]); self.assertEqual(post.call_count, 2)

    @mock.patch("aiagent.client.requests.post")
    def test_invalid_key_no_retry(self, post):
        post.return_value = _resp(401)
        res = client.chat(self.u, [{"role":"user","content":"x"}])
        self.assertFalse(res["ok"]); self.assertEqual(res["error"], "invalid_api_key")
        self.assertEqual(post.call_count, 1)
```

- [ ] **Step 2: 跑，确认失败**（`client` 无 `chat`）。

- [ ] **Step 3: 实现 `aiagent/client.py`**
```python
import os, time, logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)
BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
TIMEOUT = int(os.environ.get("DEEPSEEK_TIMEOUT", "60"))
CHAT_MODEL = "deepseek-chat"
REASONER_MODEL = "deepseek-reasoner"

def call(user, messages, model=CHAT_MODEL, json_mode=False, timeout=None) -> dict:
    key = user.deepseek_key
    if not key:
        return {"ok": False, "content": None, "usage": None, "error": "no_api_key", "status": None}
    payload = {"model": model, "messages": messages, "temperature": 0.3}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    last_err = None
    for attempt in range(3):  # 初次 + 2 次重试
        try:
            resp = requests.post(f"{BASE_URL}/chat/completions", headers=headers,
                                 json=payload, timeout=timeout or TIMEOUT)
        except requests.RequestException as e:
            last_err = f"network:{e}"; time.sleep(0.3 * (2 ** attempt)); continue
        if resp.status_code == 401:
            return {"ok": False, "content": None, "usage": None, "error": "invalid_api_key", "status": 401}
        if resp.status_code == 429 or 500 <= resp.status_code < 600:
            last_err = f"http{resp.status_code}"; time.sleep(0.3 * (2 ** attempt)); continue
        if resp.status_code != 200:
            return {"ok": False, "content": None, "usage": None, "error": f"http{resp.status_code}", "status": resp.status_code}
        data = resp.json()
        return {"ok": True,
                "content": data["choices"][0]["message"]["content"],
                "usage": data.get("usage"), "error": None, "status": 200}
    return {"ok": False, "content": None, "usage": None, "error": last_err or "unknown", "status": None}

def chat(user, messages, json_mode=False, timeout=None):
    return call(user, messages, CHAT_MODEL, json_mode, timeout)

def reasoner(user, messages, json_mode=False, timeout=None):
    return call(user, messages, REASONER_MODEL, json_mode, timeout)
```

- [ ] **Step 4: 跑，确认通过** → PASS。
- [ ] **Step 5: Commit** — `git add aiagent/client.py aiagent/tests/test_client.py && git commit -m "feat(aiagent): DeepSeek HTTP client with retry+error normalization"`

---

## Task 6: `aiagent/context.py`

**Files:**
- Create: `aiagent/context.py`
- Test: `aiagent/tests/test_context.py`

**Interfaces:**
- Consumes: `news.models.Article`, `funds.services.portfolio_snapshot`
- Produces: `news_titles_by_category(d:date)->dict{category:[{id,title}]}`、`portfolio_text(snapshot)->str`、`summaries_for(ids:list[int])->dict{id:{title,summary,category}}`。

- [ ] **Step 1: 写失败测试**
```python
# aiagent/tests/test_context.py
from datetime import date
from django.test import TestCase
from django.utils import timezone
from accounts.models import User
from news.models import Article, Source
from funds.services import portfolio_snapshot
from aiagent import context

class ContextTest(TestCase):
    def setUp(self):
        self.d = date(2026, 7, 30)
        a1 = Article.objects.create(title="美联储维持利率", summary="维持利率不变", url="http://x/1",
                                    published_at=timezone.now(), category="finance")
        a2 = Article.objects.create(title="纳指再创新高", summary="科技股领涨", url="http://x/2",
                                    published_at=timezone.now(), category="finance")
        self.ids = [a1.id, a2.id]

    def test_titles_grouped(self):
        out = context.news_titles_by_category(self.d)
        self.assertIn("finance", out)
        self.assertEqual(len(out["finance"]), 2)
        self.assertEqual(out["finance"][0]["title"], "美联储维持利率")

    def test_summaries_for(self):
        sm = context.summaries_for(self.ids)
        self.assertEqual(sm[self.ids[1]]["summary"], "科技股领涨")
```

- [ ] **Step 2: 跑，确认失败**。

- [ ] **Step 3: 实现 `aiagent/context.py`**
```python
from datetime import date
from news.models import Article
from funds.services import portfolio_snapshot

def news_titles_by_category(d: date) -> dict:
    qs = Article.objects.filter(published_at__date=d).order_by("-published_at")
    out = {}
    for a in qs:
        out.setdefault(a.category, []).append({"id": a.id, "title": a.title})
    return out

def summaries_for(ids: list) -> dict:
    out = {}
    for a in Article.objects.filter(id__in=ids):
        out[a.id] = {"title": a.title, "summary": a.summary or a.title, "category": a.category}
    return out

def portfolio_text(snapshot: dict) -> str:
    lines = ["【我的持仓】"]
    for f in snapshot["funds"]:
        st = "定投中" if f["is_active"] else "已停投"
        lines.append(
            f'- {f["name"]}({f["code"]}) [市场:{f["market"]}/类型:{f["fund_type"]}] '
            f'市值{f["mv"]} 成本{f["cost"]} 盈亏{f["profit"]} 收益率{f["roi"]}% 状态:{st}')
    lines.append(
        f'组合合计: 市值{snapshot["total_mv"]} 成本{snapshot["total_cost"]} '
        f'盈亏{snapshot["total_profit"]} 收益率{snapshot["total_roi"]}%')
    return "\n".join(lines)
```

- [ ] **Step 4: 跑，确认通过** → PASS。
- [ ] **Step 5: Commit** — `git add aiagent/context.py aiagent/tests/test_context.py && git commit -m "feat(aiagent): news/portfolio context builders"`

---

## Task 7: `prompts.py` + `screening.py`（第①阶段）

**Files:**
- Create: `aiagent/prompts.py`, `aiagent/screening.py`
- Test: `aiagent/tests/test_screening.py`

**Interfaces:**
- Consumes: `aiagent.client.chat`
- Produces: `screen(user, titles_by_cat:dict, portfolio_text:str) -> list[dict]`，每项 `{"article_id":int,"reason":str,"category":str}`。失败抛 `ScreeningError`。

- [ ] **Step 1: 写失败测试**
```python
# aiagent/tests/test_screening.py
import os, json
from unittest import mock
from django.test import TestCase
from accounts.models import User
from aiagent import screening

class ScreeningTest(TestCase):
    def setUp(self):
        os.environ["JK_FERNET_KEY"] = "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg="
        self.u = User.objects.create_user(username="sc", password="p", email="sc@e.com")

    @mock.patch("aiagent.screening.client.chat")
    def test_picks_returned(self, chat):
        chat.return_value = {"ok": True, "content": json.dumps({
            "picks": [{"id": 1, "reason": "美联储动向利好美股"}, {"id": 3, "reason": "纳指相关"}]}), "usage": {}}
        out = screening.screen(self.u, {"finance":[{"id":1,"title":"a"},{"id":2,"title":"b"},{"id":3,"title":"c"}]}, "持仓:纳斯达克100")
        self.assertEqual([p["article_id"] for p in out], [1, 3])
        self.assertEqual(out[0]["reason"], "美联储动向利好美股")

    @mock.patch("aiagent.screening.client.chat")
    def test_bad_json_raises(self, chat):
        chat.return_value = {"ok": True, "content": "not json{", "usage": {}}
        with self.assertRaises(screening.ScreeningError):
            screening.screen(self.u, {"finance": [{"id": 1, "title": "a"}]}, "持仓")
```

- [ ] **Step 2: 跑，确认失败**。

- [ ] **Step 3: 实现 `aiagent/prompts.py`**
```python
SCREENING_PROMPT = """你是基金投研助理。下面按分类给出今日新闻标题，以及用户的持仓画像。
请挑出与【用户持仓市场/行业】最相关、最值得深读的条目（最多 15 条），忽略无关的。
只返回 JSON：{"picks":[{"id":<int>,"reason":"一句话为何相关"}]}。不要解释。

持仓画像：
{portfolio}

今日标题（按分类，格式 分类: id=标题）：
{titles}"""

ANALYSIS_SYSTEM = "你是资深基金投顾，用中文输出严格 JSON，面向基金小白，语气通俗、结论明确。"

ANALYSIS_PROMPT_NOON = """基于以下筛选后的新闻摘要与用户持仓，生成【午间速览】。只返回 JSON，结构：
{"market_brief":{"politics":[{"title":"","impact":""}],"finance_cn":[],"finance_oversea":[],"tech":[]},
 "bias":[{"fund":"","direction":"利好|利空|中性","reason":""}],
 "position_advice":[{"fund":"","action":"继续定投|暂停|减仓|加仓|观望","reason":""}],
 "lesson":{"title":"","body":""}}
说明：direction/action 必须点名用户具体基金；末尾免责声明由系统加，你不用写。
持仓：
{portfolio}
筛选后新闻摘要（id=标题：摘要）：
{summaries}"""

ANALYSIS_PROMPT_EVENING = ANALYSIS_PROMPT_NOON.replace(
    "生成【午间速览】", "生成【一日总结+明日预判】") + """
额外字段 tomorrow：{"events":[{"time":"","event":""}],"watch":"明日关注点位/数据一句话"}
即在 JSON 顶层追加 "tomorrow" 对象。"""
```

- [ ] **Step 4: 实现 `aiagent/screening.py`**
```python
import json
from . import client, prompts

class ScreeningError(Exception):
    pass

def _titles_block(titles_by_cat: dict) -> str:
    lines = []
    for cat, items in titles_by_cat.items():
        for it in items:
            lines.append(f"{cat}: id={it['id']} {it['title']}")
    return "\n".join(lines)

def screen(user, titles_by_cat: dict, portfolio_text: str) -> list:
    if not any(titles_by_cat.values()):
        return []
    msg = prompts.SCREENING_PROMPT.format(
        portfolio=portfolio_text, titles=_titles_block(titles_by_cat))
    res = client.chat(user, [{"role": "user", "content": msg}], json_mode=True)
    if not res["ok"]:
        raise ScreeningError(f"screening call failed: {res['error']}")
    try:
        data = json.loads(res["content"])
        picks = data.get("picks", [])
    except (ValueError, TypeError, AttributeError):
        raise ScreeningError("screening returned non-JSON")
    out = []
    for p in picks:
        if "id" in p:
            out.append({"article_id": int(p["id"]), "reason": str(p.get("reason", "")),
                        "category": str(p.get("category", ""))})
    return out
```

- [ ] **Step 5: 跑，确认通过** → PASS。
- [ ] **Step 6: Commit** — `git add aiagent/prompts.py aiagent/screening.py aiagent/tests/test_screening.py && git commit -m "feat(aiagent): stage-1 title screening"`

---

## Task 8: `analysis.py`（第②阶段，结构化 JSON）

**Files:**
- Create: `aiagent/analysis.py`
- Test: `aiagent/tests/test_analysis.py`

**Interfaces:**
- Consumes: `aiagent.client.chat`/`reasoner`、`aiagent.prompts`
- Produces: `analyze(user, picked:list[dict], portfolio_text:str, report_type:str) -> dict`（§6 JSON 契约）。失败抛 `AnalysisError`。模型：`report_type in (morning, ondemand)`→chat，`evening`→reasoner。

- [ ] **Step 1: 写失败测试**
```python
# aiagent/tests/test_analysis.py
import os, json
from unittest import mock
from django.test import TestCase
from accounts.models import User
from aiagent import analysis

SAMPLE = {"market_brief":{"politics":[],"finance_cn":[],"finance_oversea":[],"tech":[]},
          "bias":[{"fund":"南方纳斯达克100","direction":"利好","reason":"降息预期"}],
          "position_advice":[{"fund":"南方纳斯达克100","action":"继续定投","reason":"趋势向上"}],
          "lesson":{"title":"降息与纳指","body":"宽松利好成长股"}}

class AnalysisTest(TestCase):
    def setUp(self):
        os.environ["JK_FERNET_KEY"] = "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg="
        self.u = User.objects.create_user(username="an", password="p", email="an@e.com")
        self.picked = [{"article_id":1,"title":"美联储降息","summary":"降息25bp","category":"finance"}]

    @mock.patch("aiagent.analysis.client.chat")
    def test_morning_uses_chat(self, chat):
        chat.return_value = {"ok": True, "content": json.dumps(SAMPLE), "usage": {}}
        out = analysis.analyze(self.u, self.picked, "持仓", "morning")
        self.assertEqual(out["bias"][0]["fund"], "南方纳斯达克100")
        chat.assert_called_once()

    @mock.patch("aiagent.analysis.client.reasoner")
    def test_evening_uses_reasoner(self, reasoner):
        SAMPLE2 = dict(SAMPLE); SAMPLE2["tomorrow"] = {"events":[], "watch":"非农数据"}
        reasoner.return_value = {"ok": True, "content": json.dumps(SAMPLE2), "usage": {}}
        out = analysis.analyze(self.u, self.picked, "持仓", "evening")
        self.assertEqual(out["tomorrow"]["watch"], "非农数据")
        reasoner.assert_called_once()

    @mock.patch("aiagent.analysis.client.chat")
    def test_non_json_raises(self, chat):
        chat.return_value = {"ok": True, "content": "<<<", "usage": {}}
        with self.assertRaises(analysis.AnalysisError):
            analysis.analyze(self.u, self.picked, "持仓", "morning")
```

- [ ] **Step 2: 跑，确认失败**。

- [ ] **Step 3: 实现 `aiagent/analysis.py`**
```python
import json, re
from . import client, prompts

class AnalysisError(Exception):
    pass

def _summaries_block(picked: list) -> str:
    return "\n".join(f"id={p['article_id']} {p['title']}：{p.get('summary','')}" for p in picked)

def _strip_fence(s: str) -> str:
    m = re.search(r"\{.*\}", s, re.DOTALL)
    return m.group(0) if m else s

def analyze(user, picked: list, portfolio_text: str, report_type: str) -> dict:
    tmpl = prompts.ANALYSIS_PROMPT_EVENING if report_type == "evening" else prompts.ANALYSIS_PROMPT_NOON
    msg = tmpl.format(portfolio=portfolio_text, summaries=_summaries_block(picked))
    messages = [{"role": "system", "content": prompts.ANALYSIS_SYSTEM},
                {"role": "user", "content": msg}]
    res = (client.reasoner if report_type == "evening" else client.chat)(
        user, messages, json_mode=True)
    if not res["ok"]:
        raise AnalysisError(f"analysis call failed: {res['error']}")
    try:
        data = json.loads(_strip_fence(res["content"]))
    except (ValueError, TypeError):
        raise AnalysisError("analysis returned non-JSON")
    # 结构兜底：确保必备键存在
    data.setdefault("market_brief", {})
    data.setdefault("bias", [])
    data.setdefault("position_advice", [])
    data.setdefault("lesson", {})
    return data
```

- [ ] **Step 4: 跑，确认通过** → PASS。
- [ ] **Step 5: Commit** — `git add aiagent/analysis.py aiagent/tests/test_analysis.py && git commit -m "feat(aiagent): stage-2 structured analysis (chat/reasoner)"`

---

## Task 9: `reports.py`（JSON → HTML，5 段）

**Files:**
- Create: `aiagent/reports.py`, `templates/aiagent/_report_body.html`
- Test: `aiagent/tests/test_reports.py`

**Interfaces:**
- Consumes: §6 结构化 dict
- Produces: `render(analysis:dict, report_type:str) -> str`（HTML 字符串，含 5 段 + 免责声明）。

- [ ] **Step 1: 写失败测试**
```python
# aiagent/tests/test_reports.py
from django.test import TestCase
from aiagent import reports

SAMPLE = {"market_brief":{"politics":[{"title":"t","impact":"i"}],"finance_cn":[],
           "finance_oversea":[],"tech":[]},
          "bias":[{"fund":"南方纳斯达克100","direction":"利好","reason":"r"}],
          "position_advice":[{"fund":"南方纳斯达克100","action":"继续定投","reason":"r"}],
          "tomorrow":{"events":[{"time":"20:30","event":"非农"}],"watch":"纳指前高"},
          "lesson":{"title":"降息","body":"利好成长股"}}

class ReportsTest(TestCase):
    def test_renders_sections(self):
        html = reports.render(SAMPLE, "evening")
        self.assertIn("新闻速览", html)
        self.assertIn("利好", html) and self.assertIn("南方纳斯达克100", html)
        self.assertIn("仓位建议", html)
        self.assertIn("明日预判", html)             # 仅晚间
        self.assertIn("小白课堂", html)
        self.assertIn("不构成投资建议", html)        # 免责

    def test_noon_omits_tomorrow(self):
        html = reports.render({k:v for k,v in SAMPLE.items() if k!="tomorrow"}, "morning")
        self.assertNotIn("明日预判", html)
```

- [ ] **Step 2: 跑，确认失败**。

- [ ] **Step 3: 写 `templates/aiagent/_report_body.html`**
```html
<div class="ai-report">
  <h2>📰 今日新闻速览</h2>
  {% for cat, label in cat_labels.items %}
    {% with items=analysis.market_brief|get:cat %}
      {% if items %}
        <h4>{{ label }}</h4>
        <ul>{% for it in items %}<li>{{ it.title }} —— <em>{{ it.impact }}</em></li>{% endfor %}</ul>
      {% endif %}
    {% endwith %}
  {% endfor %}

  <h2>🎯 利好 / 利空方向</h2>
  <ul>{% for b in analysis.bias %}
    <li><strong>{{ b.fund }}</strong> · <span>{{ b.direction }}</span> —— {{ b.reason }}</li>
  {% endfor %}</ul>

  <h2>💼 仓位建议（明日）</h2>
  <ul>{% for a in analysis.position_advice %}
    <li><strong>{{ a.fund }}</strong> → {{ a.action }}：{{ a.reason }}</li>
  {% endfor %}</ul>

  {% if report_type == "evening" and analysis.tomorrow %}
  <h2>🌅 明日预判</h2>
  <ul>{% for e in analysis.tomorrow.events %}<li>{{ e.time }} {{ e.event }}</li>{% endfor %}</ul>
  <p>关注：{{ analysis.tomorrow.watch }}</p>
  {% endif %}

  <h2>📚 小白课堂</h2>
  {% if analysis.lesson %}<h4>{{ analysis.lesson.title }}</h4><p>{{ analysis.lesson.body }}</p>{% endif %}

  <p class="disclaimer">⚠️ 本报告由 AI 生成，仅供参考，不构成投资建议，据此操作盈亏自负。</p>
</div>
```

- [ ] **Step 4: 实现 `aiagent/reports.py`**
```python
from django.template.loader import render_to_string

CAT_LABELS = {"politics": "时政国际", "finance": "A股财经", "finance_oversea": "海外财经", "tech": "科技"}

def render(analysis: dict, report_type: str) -> str:
    return render_to_string("aiagent/_report_body.html",
                            {"analysis": analysis, "report_type": report_type,
                             "cat_labels": CAT_LABELS})
```

> 模板里用了 `market_brief|get:cat`（dict 取键）。Django 模板无内置 `get` 过滤器，故 Step 4 需注册一个：
```python
# aiagent/templatetags/__init__.py  （空）
# aiagent/templatetags/ai_extras.py
from django import template
register = template.Library()

@register.filter
def get(d, key):
    try:
        return d.get(key)
    except AttributeError:
        return None
```
并把 `_report_body.html` 顶部加 `{% load ai_extras %}`。

- [ ] **Step 5: 跑，确认通过** → PASS。
- [ ] **Step 6: Commit** — `git add aiagent/reports.py aiagent/templatetags templates/aiagent/_report_body.html aiagent/tests/test_reports.py && git commit -m "feat(aiagent): render structured analysis to 5-section HTML"`

---

## Task 10: `services.py`（编排器 + 降级）

**Files:**
- Create: `aiagent/services.py`
- Test: `aiagent/tests/test_services.py`

**Interfaces:**
- Consumes: `context`、`screening`、`analysis`、`reports`、`AnalysisReport`
- Produces: `generate_report(user, report_type:str) -> AnalysisReport`。覆盖正常/降级/空新闻三态。

- [ ] **Step 1: 写失败测试**
```python
# aiagent/tests/test_services.py
import os, json
from unittest import mock
from datetime import date
from django.test import TestCase
from accounts.models import User
from news.models import Article
from django.utils import timezone
from aiagent import services, models

def _screen(picks):  # 造 screening 返回
    return lambda *a, **k: picks

class ServicesTest(TestCase):
    def setUp(self):
        os.environ["JK_FERNET_KEY"] = "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg="
        self.u = User.objects.create_user(username="sv", password="p", email="sv@e.com")
        self.u.set_deepseek_key("sk-x"); self.u.save()
        self.a = Article.objects.create(title="美联储降息", summary="降息25bp", url="http://s/1",
                                        published_at=timezone.now(), category="finance")

    @mock.patch("aiagent.services.analysis.analyze")
    @mock.patch("aiagent.services.screening.screen")
    def test_happy_path(self, screen, analyze):
        screen.return_value = [{"article_id": self.a.id, "reason": "相关", "category": "finance"}]
        analyze.return_value = {"market_brief":{}, "bias":[{"fund":"x","direction":"利好","reason":"r"}],
                                "position_advice":[], "lesson":{}}
        rep = services.generate_report(self.u, "morning")
        self.assertEqual(rep.status, "ok")
        self.assertIn("利好", rep.content_html)
        self.assertEqual(rep.screening[0]["article_id"], self.a.id)

    @mock.patch("aiagent.services.analysis.analyze")
    @mock.patch("aiagent.services.screening.screen")
    def test_degraded_on_analysis_fail(self, screen, analyze):
        screen.return_value = [{"article_id": self.a.id, "reason": "r", "category": "finance"}]
        from aiagent.analysis import AnalysisError
        analyze.side_effect = AnalysisError("bad")
        rep = services.generate_report(self.u, "morning")
        self.assertEqual(rep.status, "degraded")
        self.assertIn("AI 暂不可用", rep.content_html)
        self.assertIn("美联储降息", rep.content_html)   # 标题清单兜底

    @mock.patch("aiagent.services.screening.screen")
    def test_no_news_short_report(self, screen):
        Article.objects.all().delete()
        screen.return_value = []
        rep = services.generate_report(self.u, "morning")
        self.assertEqual(rep.status, "ok")
        self.assertIn("暂无足够新闻", rep.content_html)

    def test_no_key_skips(self):
        u2 = User.objects.create_user(username="sv2", password="p", email="sv2@e.com")
        with self.assertRaises(services.NoApiKey):
            services.generate_report(u2, "morning")
```

- [ ] **Step 2: 跑，确认失败**。

- [ ] **Step 3: 实现 `aiagent/services.py`**
```python
import logging
from datetime import date
from django.utils import timezone
from funds.services import portfolio_snapshot
from news.models import Article
from . import context, screening, analysis, reports
from .models import AnalysisReport

logger = logging.getLogger(__name__)

class NoApiKey(Exception):
    pass

def _today(): return timezone.localdate() if timezone.is_aware(timezone.now()) else date.today()

def _degraded_html(reason: str, titles_by_cat: dict) -> str:
    import itertools
    parts = [f'<p class="warn">⚠️ AI 分析暂不可用（{reason}），以下为当日新闻标题清单：</p><ul>']
    for cat, items in titles_by_cat.items():
        for it in items:
            parts.append(f"<li>{cat}: {it['title']}</li>")
    parts.append("</ul>")
    return "".join(parts)

def generate_report(user, report_type: str) -> AnalysisReport:
    if not user.deepseek_key:
        raise NoApiKey(f"{user.username} has no deepseek key")
    today = _today()
    snap = portfolio_snapshot(user)
    ptext = context.portfolio_text(snap)
    titles_by_cat = context.news_titles_by_category(today)

    meta = {"models": [], "tokens_in": 0, "tokens_out": 0, "duration_s": 0}
    status, analysis_dict, screening_result = "ok", {}, []

    if not any(titles_by_cat.values()):
        html = "<p>今日暂无足够新闻可分析。仅提供仓位小结。</p>" + ptext.replace("\n", "<br>")
    else:
        try:
            screening_result = screening.screen(user, titles_by_cat, ptext)
            ids = [p["article_id"] for p in screening_result]
            summaries = context.summaries_for(ids)
            picked = [{"article_id": i,
                       "title": summaries[i]["title"],
                       "summary": summaries[i]["summary"],
                       "category": summaries[i]["category"]} for i in ids if i in summaries]
            analysis_dict = analysis.analyze(user, picked, ptext, report_type)
            html = reports.render(analysis_dict, report_type)
        except (screening.ScreeningError, analysis.AnalysisError) as e:
            logger.warning("AI degrade for %s: %s", user.username, e)
            status = "degraded"
            html = _degraded_html(str(e), titles_by_cat)

    # upsert（定时型唯一）
    qs = AnalysisReport.objects.filter(user=user, type=report_type, date=today)
    rep = qs.first() if report_type in ("morning", "evening") else None
    if rep:
        rep.content_html = html; rep.screening = screening_result
        rep.analysis = analysis_dict; rep.meta = meta; rep.status = status; rep.save()
    else:
        rep = AnalysisReport.objects.create(
            user=user, type=report_type, date=today, content_html=html,
            screening=screening_result, analysis=analysis_dict, meta=meta, status=status)
    return rep
```

- [ ] **Step 4: 跑，确认通过** → PASS。
- [ ] **Step 5: Commit** — `git add aiagent/services.py aiagent/tests/test_services.py && git commit -m "feat(aiagent): generate_report orchestrator with degrade paths"`

---

## Task 11: `emails.py` + 邮件模板

**Files:**
- Create: `aiagent/emails.py`, `templates/aiagent/emails/morning.html`, `templates/aiagent/emails/evening.html`
- Test: `aiagent/tests/test_emails.py`

**Interfaces:**
- Consumes: `AnalysisReport`、`django.core.mail`
- Produces: `send_report_email(report:AnalysisReport) -> int`（发送数 0/1）。

- [ ] **Step 1: 写失败测试**（用 locmem 后端）
```python
# aiagent/tests/test_emails.py
import os
from datetime import date
from django.core import mail
from django.test import TestCase, override_settings
from accounts.models import User
from aiagent.models import AnalysisReport
from aiagent import emails

@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class EmailTest(TestCase):
    def setUp(self):
        os.environ["JK_FERNET_KEY"] = "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg="
        self.u = User.objects.create_user(username="em", password="p", email="em@e.com")
    def test_send(self):
        rep = AnalysisReport.objects.create(user=self.u, type="evening", date=date(2026,7,30),
                                            content_html="<h2>新闻速览</h2><p>x</p>")
        n = emails.send_report_email(rep)
        self.assertEqual(n, 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("新闻速览", mail.outbox[0].alternatives[0][0])  # html body
        self.assertEqual(mail.outbox[0].to, ["em@e.com"])
```

- [ ] **Step 2: 跑，确认失败**。

- [ ] **Step 3: 写模板**（`evening.html`；`morning.html` 同结构换标题）
```html
{% load i18n %}
<h1>📊 基金看板 · 晚间报告（{{ report.date }}）</h1>
{{ report.content_html|safe }}
<hr><p>站内查看：<a href="{{ host }}/aiagent/{{ report.id }}/">完整报告</a></p>
```

- [ ] **Step 4: 实现 `aiagent/emails.py`**
```python
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

SUBJECT = {"morning": "【基金看板】午间新闻速览 + 仓位建议",
           "evening": "【基金看板】一日新闻速览 + 明日仓位建议",
           "ondemand": "【基金看板】AI 报告（按需）"}

def send_report_email(report) -> int:
    if not report.user.email:
        return 0
    host = getattr(settings, "SITE_HOST", "http://49.234.26.95:8188")
    html = render_to_string("aiagent/emails/%s.html" % report.type,
                            {"report": report, "host": host})
    subject = SUBJECT.get(report.type, "【基金看板】AI 报告")
    msg = EmailMultiAlternatives(subject, "请用支持 HTML 的客户端查看", to=[report.user.email])
    msg.attach_alternative(html, "text/html")
    msg.send(fail_silently=True)
    return 1
```

- [ ] **Step 5: 跑，确认通过** → PASS。
- [ ] **Step 6: Commit** — `git add aiagent/emails.py templates/aiagent/emails aiagent/tests/test_emails.py && git commit -m "feat(aiagent): report email sender + templates"`

---

## Task 12: 报告页面 + 立即分析（限额）+ key 设置页

**Files:**
- Create: `aiagent/forms.py`, `aiagent/views.py`, 填充 `aiagent/urls.py`；`templates/aiagent/{report_list,report_detail,key_settings}.html`
- Test: `aiagent/tests/test_views.py`

**Interfaces:**
- Consumes: `services.generate_report`（手动版）、`emails`、`User.set_deepseek_key`、`AnalysisReport`
- Produces: 视图 `report_list`/`report_detail`/`on_demand`(POST)/`key_settings`(GET/POST)；URL name：`report-list`/`report-detail`/`on-demand`/`key-settings`。手动限额 5 次/天。

- [ ] **Step 1: 写失败测试**
```python
# aiagent/tests/test_views.py
import os
from datetime import date
from django.test import TestCase
from django.urls import reverse
from accounts.models import User
from aiagent.models import AnalysisReport

class ViewTest(TestCase):
    def setUp(self):
        os.environ["JK_FERNET_KEY"] = "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg="
        self.u = User.objects.create_user(username="v", password="p", email="v@e.com")
        self.client.force_login(self.u)

    def test_list_shows_reports(self):
        AnalysisReport.objects.create(user=self.u, type="morning", date=date(2026,7,30), content_html="x")
        r = self.client.get(reverse("aiagent:report-list"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "午间")

    def test_key_settings_post_sets_key(self):
        r = self.client.post(reverse("aiagent:key-settings"), {"deepseek_key": "sk-new"})
        self.assertEqual(r.status_code, 302)
        self.u.refresh_from_db()
        self.assertEqual(self.u.deepseek_key, "sk-new")

    def test_on_demand_quota_blocks_6th(self):
        from unittest import mock
        with mock.patch("aiagent.views.services.generate_report") as g:
            g.return_value = AnalysisReport.objects.create(user=self.u, type="ondemand", date=date.today())
            for _ in range(5):
                self.assertEqual(self.client.post(reverse("aiagent:on-demand")).status_code, 302)
            self.assertEqual(self.client.post(reverse("aiagent:on-demand")).status_code, 429)
```

- [ ] **Step 2: 跑，确认失败**。

- [ ] **Step 3: 实现 `aiagent/forms.py`**
```python
from django import forms

class DeepSeekKeyForm(forms.Form):
    deepseek_key = forms.CharField(
        widget=forms.PasswordInput(attrs={"placeholder": "sk-..."}), required=False,
        label="DeepSeek API Key")
```

- [ ] **Step 4: 实现 `aiagent/views.py`**
```python
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import AnalysisReport
from .forms import DeepSeekKeyForm
from . import services

ON_DEMAND_DAILY_LIMIT = 5

@login_required
def report_list(request):
    reps = AnalysisReport.objects.filter(user=request.user)
    return render(request, "aiagent/report_list.html", {"reports": reps})

@login_required
def report_detail(request, pk):
    rep = get_object_or_404(AnalysisReport, pk=pk, user=request.user)
    return render(request, "aiagent/report_detail.html", {"report": rep})

@login_required
@require_POST
def on_demand(request):
    today = timezone.localdate()
    used = AnalysisReport.objects.filter(user=request.user, type="ondemand", date=today).count()
    if used >= ON_DEMAND_DAILY_LIMIT:
        return HttpResponse("今日手动分析已达上限（%d 次）" % ON_DEMAND_DAILY_LIMIT, status=429)
    try:
        services.generate_report(request.user, "ondemand")
    except services.NoApiKey:
        return redirect("aiagent:key-settings")
    return redirect("aiagent:report-list")

@login_required
def key_settings(request):
    if request.method == "POST":
        form = DeepSeekKeyForm(request.POST)
        if form.is_valid():
            request.user.set_deepseek_key(form.cleaned_data["deepseek_key"] or "")
            request.user.save()
            return redirect("aiagent:key-settings")
    else:
        form = DeepSeekKeyForm()
    has_key = bool(request.user.deepseek_key)
    return render(request, "aiagent/key_settings.html", {"form": form, "has_key": has_key})
```

- [ ] **Step 5: 填充 `aiagent/urls.py`**
```python
from django.urls import path
from . import views

app_name = "aiagent"
urlpatterns = [
    path("", views.report_list, name="report-list"),
    path("key/", views.key_settings, name="key-settings"),
    path("on-demand/", views.on_demand, name="on-demand"),
    path("<int:pk>/", views.report_detail, name="report-detail"),
]
```

- [ ] **Step 6: 写三个模板**（`report_list.html` 列出报告+「立即分析」表单 POST 到 `on-demand` + 「Key 设置」链接；`report_detail.html` 渲染 `{{ report.content_html|safe }}`；`key_settings.html` 渲染 form，`has_key` 时提示"已设置，留空则清除"）。每个模板 `{% extends "base.html" %}` + `{% block content %}`。

`report_list.html` 关键片段：
```html
{% extends "base.html" %}
{% block content %}
<h1>AI 报告</h1>
<form method="post" action="{% url 'aiagent:on-demand' %}">{% csrf_token %}
  <button type="submit">⚡ 立即分析（每日 {{ 5 }} 次）</button>
</form>
<a href="{% url 'aiagent:key-settings' %}">DeepSeek Key 设置</a>
<ul>
  {% for r in reports %}
    <li><a href="{% url 'aiagent:report-detail' r.id %}">{{ r.get_type_display }} · {{ r.date }} · {{ r.status }}</a></li>
  {% endfor %}
</ul>
{% endblock %}
```

- [ ] **Step 7: 跑，确认通过** → PASS。
- [ ] **Step 8: Commit** — `git add aiagent/forms.py aiagent/views.py aiagent/urls.py templates/aiagent/report_list.html templates/aiagent/report_detail.html templates/aiagent/key_settings.html aiagent/tests/test_views.py && git commit -m "feat(aiagent): report pages, on-demand(quota), key settings"`

---

## Task 13: news 海外财经分类 + 定时命令 + cron + 最终部署

**Files:**
- Modify: `news/models.py`(CATEGORY_CHOICES)、`aiagent/management/commands/run_ai_morning.py`、`run_ai_evening.py`、crontab、`.env`
- Test: `aiagent/tests/test_commands.py`

**Interfaces:**
- Consumes: `services.generate_report`、`emails.send_report_email`、`accounts.models.User`
- Produces: 两个命令；遍历 `is_active & email_verified & 已填key` 用户，生成并发邮件。

- [ ] **Step 1: 写失败测试**
```python
# aiagent/tests/test_commands.py
import os
from datetime import date
from unittest import mock
from django.core.management import call_command
from django.test import TestCase
from accounts.models import User

class CommandTest(TestCase):
    def setUp(self):
        os.environ["JK_FERNET_KEY"] = "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg="
        self.u = User.objects.create_user(username="cmd", password="p", email="cmd@e.com",
                                          is_active=True, email_verified=True)
        self.u.set_deepseek_key("sk"); self.u.save()
        # 不应被处理的用户
        User.objects.create_user(username="nokey", password="p", email="n@e.com",
                                 is_active=True, email_verified=True)

    @mock.patch("aiagent.services.emails.send_report_email")
    @mock.patch("aiagent.services.analysis.analyze")
    @mock.patch("aiagent.services.screening.screen")
    def test_morning_runs_for_eligible(self, screen, analyze, send):
        from aiagent.models import AnalysisReport
        screen.return_value = []; analyze.return_value = {"market_brief":{},"bias":[],"position_advice":[],"lesson":{}}
        call_command("run_ai_morning")
        send.assert_called_once()                      # 只发了 1 个（cmd）
        self.assertTrue(AnalysisReport.objects.filter(user=self.u, type="morning").exists())
```

- [ ] **Step 2: 跑，确认失败**（命令不存在）。

- [ ] **Step 3: 改 `news/models.py`** —— `CATEGORY_CHOICES` 加 `("finance_oversea", "海外财经")`（choices 变更无需迁移；DB 不强制 choices）。

- [ ] **Step 4: 写 `aiagent/management/commands/run_ai_morning.py`**
```python
from django.core.management.base import BaseCommand
from accounts.models import User
from aiagent.services import generate_report, NoApiKey
from aiagent.emails import send_report_email

class Command(BaseCommand):
    help = "午间 AI 报告：生成 + 发邮件"
    def handle(self, *a, **kw):
        sent, skipped = 0, 0
        for u in User.objects.filter(is_active=True, email_verified=True):
            if not u.deepseek_key:
                skipped += 1; continue
            try:
                rep = generate_report(u, "morning")
                send_report_email(rep); sent += 1
            except NoApiKey:
                skipped += 1
            except Exception as e:
                self.stderr.write(f"ERR {u.username}: {e}")
        self.stdout.write(self.style.SUCCESS(f"morning: sent={sent} skipped={skipped}"))
```
`run_ai_evening.py` 同上，`"morning"`→`"evening"`，help 改"晚间"。

- [ ] **Step 5: 跑，确认通过** → PASS。

- [ ] **Step 6: 部署 + 全量验证**
`scp` 全部改动 → `ssh ... 'cd ... && bash deploy.sh'`。Expected：全量测试绿；`:8188` 200。

- [ ] **Step 7: 加海外财经源（admin 数据，无代码）**
`ssh ... 'cd ... && venv/bin/python manage.py shell'` 里或 `/admin/news/source/` 加 1-2 条 `kind=RSS, category=finance_oversea` 的源（URL 部署时实测可用性后定；备选：华尔街见闻/财联社）。先 `fetch_news` 跑一次确认不 hang。

- [ ] **Step 8: crontab + .env**
```
ssh ubuntu@49.234.26.95 'crontab -l > /tmp/cron.bak && (crontab -l; echo "30 12 * * * cd ~/home/claude_PJ/Jijin_Kanban && venv/bin/python manage.py run_ai_morning >>cron.log 2>&1"; echo "0 18 * * * cd ~/home/claude_PJ/Jijin_Kanban && venv/bin/python manage.py run_ai_evening >>cron.log 2>&1") | crontab -'
```
确认 `.env` 含 `JK_FERNET_KEY`（crypto 首次运行自动写入；也可手动加）。可选加 `DEEPSEEK_BASE_URL` / `DEEPSEEK_TIMEOUT`。

- [ ] **Step 9: Commit** — `git add news/models.py aiagent/management aiagent/tests/test_commands.py && git commit -m "feat(aiagent): finance_oversea category + morning/evening cron commands"`

- [ ] **Step 10: 手动冒烟** —— 在 `/aiagent/key/` 填入真实 DeepSeek key → 点「立即分析」→ 确认生成报告且 `:8188` 可见；查 `cron.log`。

---

## Self-Review（计划 vs spec 自检）

**1. Spec 覆盖**：
- 两段式流水线 → Task 7(screening)+8(analysis) ✓
- 午间/晚间邮件 → Task 11(emails)+13(commands/cron) ✓
- DeepSeek + 个人主页填 key（加密）→ Task 2(crypto)+3(User 字段)+12(key_settings) ✓
- 立即分析 + 限额 → Task 12(on_demand, 5/天) ✓
- 5 段报告 + 免责 → Task 9(reports/_report_body) ✓
- 降级矩阵 → Task 10(services: no_key/analysis_fail/empty_news) ✓
- 海外财经源 → Task 13 ✓
- 站内历史存档 → Task 12(report_list/detail) ✓
- portfolio_snapshot 隔离 → Task 4 ✓
- 测试策略 → 每个 Task 内 TDD ✓

**2. 类型/命名一致性**：`generate_report(user, report_type)`、`screen(user,titles_by_cat,portfolio_text)`、`analyze(user,picked,portfolio_text,report_type)`、`render(analysis,report_type)`、`send_report_email(report)`、`NoApiKey`/`ScreeningError`/`AnalysisError`、URL name `aiagent:*`、报告类型常量 `morning/evening/ondemand` —— 各 Task 间一致 ✓。`user.deepseek_key`(property)/`set_deepseek_key()` 一致 ✓。

**3. 占位扫描**：模板 Step 6 给了关键片段+说明（report_detail/key_settings 沿用同一 base.html 套路，非占位）；海外财经源 URL 按 spec §15 标记为"部署实测后定"，属设计内允许的未来项，非计划占位。其余步骤均含可执行代码 ✓。

**4. 作用域**：单一 app、清晰接口，13 个任务各自可独立测，适合一份计划顺序执行 ✓。
