# AI 智能体分析功能 设计文档

- **日期**：2026-07-30
- **状态**：已与用户确认，待写实现计划
- **作者**：brainstorming 会话产出
- **关联**：基于现有 Jijin_Kanban（基金看板）项目扩展

---

## 1. 目标

给基金看板增加一个 **AI 智能体分析**能力：每天结合**当日新闻**与**用户基金仓位/盈亏/历史**，生成通俗的智能分析报告，邮件推送给用户，并可在站内翻阅、随时触发。

用户是**基金小白**，报告既要**可执行**（仓位建议）也要**补知识**（通俗解读 + 小白课堂），目标受众重仓美股 QDII（纳斯达克 100 / 标普 500）+ 1 只 A 股（科创 50）。

### 1.1 核心需求
- **省 token 的两段式流水线**：第①阶段只喂**新闻标题**做初筛（便宜模型），第②阶段只对筛中的少数条目取**摘要**做深度分析（强模型）。
- **每日两封邮件**：午间（12:30）快速速览 + 仓位建议；晚间（18:00）一日新闻 + 明日仓位建议/预判。
- **DeepSeek API**：用户在「个人主页」自行填入保存 key。
- **完整产品形态**（非玩具）：定时邮件 + 站内历史报告存档 + 「立即分析」按钮（每日限额）。

### 1.2 非目标（YAGNI）
- 不做实时盯盘 / 不接实时行情 API。
- 不做对话式 chatbot；本期是"每日报告 + 按需生成"。
- 不对外暴露公开 API（报告仅供本站登录用户查看）。
- 不引入 Celery / 异步队列；沿用 management command + cron。

---

## 2. 背景（现有系统）

| 模块 | 现状 | 本功能如何用 |
|---|---|---|
| `news` | `Article`(title/summary/content/category/published_at/extra JSONField) / `Source`(可插拔)；每 3h cron 抓取；当前 ~370 条/天，分类 politics/finance(A股)/tech_oversea | 提供 AI 输入：标题做初筛，摘要做深读 |
| `funds` | `Fund`/`DailyRecord`；`_fund_summary()` 已算出 mv/cost/profit/roi | 提供仓位/盈亏上下文（新增 `portfolio_snapshot()`） |
| `accounts` | `User`(AbstractUser) + 魔法链接登录 + `send_daily_email` 邮件模式 | 新增加密 key 字段 + 复用邮件发送模式 |
| cron | 已有 send_daily_email/finalize_daily/fetch_news | 新增 run_ai_morning / run_ai_evening |

**已知数据缺口**：当前财经分类只抓 A 股，**缺海外/美股财经源**，而用户重仓美股。本功能顺带补 `finance_oversea` 分类 + 1-2 个源。

---

## 3. 架构

**新建独立 app `aiagent`**，承载全部 AI 逻辑，不污染 `funds`/`news`。

**新增依赖**：`cryptography`（Fernet 加密）。DeepSeek 走 HTTP `requests`（已有），**不引入 SDK**。

### 3.1 两段式流水线（方案 A，已确认）
```
当日全部标题(按分类) + 仓位画像
   │  ① screening  (deepseek-chat，便宜)
   ▼
挑出 ~15 条"值得深读"(带理由) → 只取这些条的 summary
   │  ② analysis   (午=chat / 晚=reasoner，深度)
   ▼
结构化报告 JSON → reports.render → HTML（邮件 + 站内共用）
```

---

## 4. 数据模型

### 4.1 `accounts.User` 新增字段
- `deepseek_key_enc = CharField(max_length=512, blank=True, default="")` —— Fernet 密文。
- 通过 `crypto.py` 的 `encrypt_key()`/`decrypt_key()` 存取；User 上暴露 `@property deepseek_key`（明文读取，仅服务端用）。

### 4.2 新表 `aiagent.AnalysisReport`
| 字段 | 类型 | 说明 |
|---|---|---|
| `user` | FK(User, cascade) | |
| `type` | CharField choices | `MORNING` / `EVENING` / `ONDEMAND` |
| `date` | DateField | 报告日期（业务日） |
| `content_html` | TextField | 渲染好的报告 HTML（邮件正文与站内详情共用） |
| `screening` | JSONField(default=dict) | 初筛结果：`[{article_id, title, reason}, ...]` |
| `analysis` | JSONField(default=dict) | 第②阶段结构化 JSON 原文（便于重渲染/调试） |
| `meta` | JSONField(default=dict) | `{models:[...], tokens_in, tokens_out, duration_s, cost_est, status_detail}` |
| `status` | CharField choices | `ok` / `degraded` / `failed` |
| `created_at` | DateTimeField(auto_now_add) | |

- 约束：**仅 `MORNING`/`EVENING` 在 `(user, type, date)` 上唯一**，用 `UniqueConstraint(condition=Q(type__in=["MORNING","EVENING"]))` 排除 ONDEMAND；ONDEMAND 允许同日多条。
- 定时版同日重跑走 **app 层 upsert**（`get_or_create` 后 update 字段），不裸依赖 unique 抛错。
- 索引：`(user, -date, type)` 便于历史翻阅。

### 4.3 `news` 扩展
- `CATEGORY_CHOICES` 增加 `("finance_oversea", "海外财经")`。
- 通过 `/admin/news/source/` 添加 1-2 个海外财经 RSS 源（如华尔街见闻、财联社海外）——**无需改抓取代码**（kind=RSS 复用现有 fetcher）。

### 4.4 迁移
- `accounts` 迁移：加 `deepseek_key_enc`。
- `aiagent` 初始迁移：建 `AnalysisReport`。
- `news` 迁移：choices 变更（仅可选值扩展，无字段结构变化，旧数据不受影响）。

---

## 5. 模块划分（`aiagent/`）

每个文件单一职责、可独立测试：

| 文件 | 职责 | 关键接口 |
|---|---|---|
| `crypto.py` | Fernet 加解密 | `encrypt_key(plain)`, `decrypt_key(enc)`, `get_fernet()`（密钥读 `JK_FERNET_KEY`，缺失自动生成并写 `.env`） |
| `client.py` | DeepSeek HTTP 客户端 | `chat(user, messages, json=False)`, `reasoner(user, messages, json=False)` → 返回 `{ok, content, usage, error}`；超时 60s、重试 2 次指数退避、错误归一化（401/429/5xx/network/malformed） |
| `context.py` | 拼装上下文 | `build_news_titles(date)` → 按分类的标题列表；`build_portfolio_text(snapshot)` → 给 LLM 的仓位文字版 |
| `screening.py` | 第①阶段 | `screen(user, titles_by_cat, snapshot) -> [{article_id, reason}]`，调用 `client.chat` |
| `analysis.py` | 第②阶段 | `analyze(user, picked_summaries, snapshot, report_type) -> dict`（结构化 JSON），午 chat / 晚 reasoner |
| `prompts.py` | 提示词模板（版本化常量） | `SCREENING_PROMPT`, `ANALYSIS_PROMPT_NOON`, `ANALYSIS_PROMPT_EVENING` |
| `services.py` | **编排器** | `generate_report(user, report_type) -> AnalysisReport`：screening→analysis→render→落库；含全部降级分支 |
| `reports.py` | 结构化 JSON → HTML | `render(analysis_dict, report_type) -> str`（5 段结构，邮件+站内共用） |
| `emails.py` | 发邮件 | `send_report_email(user, report)`（午间/晚间模板） |
| `views.py` | 页面 | `report_list`, `report_detail`, `on_demand`(POST, 限额), `key_settings`(GET/POST) |
| `forms.py` | 表单 | `DeepSeekKeyForm`（录入/清空 key） |
| `management/commands/run_ai_morning.py` | 12:30 定时 | 遍历合规用户 → `generate_report(MORNING)` → `send_report_email` |
| `management/commands/run_ai_evening.py` | 18:00 定时 | 同上，`EVENING` |

### 5.1 关键隔离点
`aiagent` **不直接翻 `funds` 内部**。在 `funds/services.py` 新增：

```python
def portfolio_snapshot(user) -> dict:
    """返回用户仓位快照（纯数据，供 aiagent 等外部消费）。
    {total_mv, total_cost, total_profit, total_roi,
     funds: [{name, code, market, fund_type, currency, is_active,
              mv, cost, profit, roi, last_date, trend_14d: [(date, profit), ...]}]}
    """
```
（复用现有 `_fund_summary()` 逻辑提炼而来；本身可单测。）

---

## 6. 第②阶段结构化输出（JSON 契约）

`analysis.analyze()` 要求模型返回如下结构（`reports.render` 据此渲染）：

```json
{
  "market_brief": {
    "politics":       [{"title": "...", "impact": "一句话影响"}],
    "finance_cn":     [...],
    "finance_oversea":[...],
    "tech":           [...]
  },
  "bias": [
    {"fund": "南方纳斯达克100", "direction": "利好|利空|中性", "reason": "..."}
  ],
  "position_advice": [
    {"fund": "...", "action": "继续定投|暂停|减仓|加仓|观望", "reason": "..."}
  ],
  "tomorrow": {                       // 仅晚间版
    "events": [{"time": "...", "event": "..."}],
    "watch":  "关注点位/数据一句话"
  },
  "lesson": {"title": "美联储降息对纳指QDII意味着啥", "body": "通俗解释..."}
}
```

> 报告分类是**展示分组**，映射自 news 分类：`politics`→时政、`finance`→A股、`finance_oversea`→海外、`tech_cn`+`tech_oversea`→科技。`reports.render` 负责合并映射。

- 请求时带 `response_format={"type":"json_object"}`（chat 支持；reasoner 走提示要求 JSON + 容错解析兜底）。
- 解析失败 → 降级（见 §8）。

---

## 7. 报告结构与渲染（5 段）

`reports.render()` 把 §6 的 JSON 渲染成 HTML：

1. 📰 **新闻速览** —— 按 时政 / A股 / 海外 / 科技 分类，每类列要点 + 对用户持仓的影响。
2. 🎯 **利好/利空方向** —— 点名用户**具体基金**（纳斯达克100 / 标普500 / 科创50），标利好/利空/中性 + 理由。
3. 💼 **仓位建议** —— 每只基金明日动作（继续定投/暂停/减仓/加仓）+ 一句理由；**末尾固定风险提示与免责声明**。
4. 🌅 **明日预判** —— 仅晚间版：关键事件/数据 + 关注点位。
5. 📚 **小白课堂** —— 挑当日新闻一个概念做通俗解释。

午间版精简（去掉"明日预判"，仓位建议精简），晚间版完整。

---

## 8. 错误处理与降级（绝不静默失败）

| 场景 | `generate_report` 行为 | 邮件 |
|---|---|---|
| 用户未填 key | 定时：跳过用户 + 记日志；手动：抛可读异常→前端提示 | 不发 |
| key 失效（401）/ 限流（429）/ 网络 | `client` 重试 2 次退避 → 仍失败：**降级报告**（`status=degraded`） | 发，正文置顶"AI 暂不可用（原因）"+ 附当日全部新闻标题清单 + 仅仓位小结 |
| 第②阶段返回非法 JSON | 提示要求 JSON 重试 1 次 → 仍失败则降级 | 同上 |
| 当日新闻为空 | 短报告"今日暂无足够新闻"+ 仅仓位小结（`status=ok`） | 发 |
| 第①阶段成功但第②阶段失败 | 保留 screening 结果落库，`status=degraded` | 降级邮件 |

---

## 9. 「立即分析」按钮 + 限额

- 站内报告页有「立即分析」按钮（POST `/aiagent/on-demand/`）。
- 走 `generate_report(user, ONDEMAND)`，**强制用 `deepseek-chat`**（手动要快）。
- **每日限 5 次**（按 `(user, date, type=ONDEMAND)` 计数，超限返回 429 友好提示）。
- 结果同样进历史存档（`type=ONDEMAND`）。

---

## 10. DeepSeek key 管理

- **录入**：「个人主页」`/aiagent/key/` 页面，`DeepSeekKeyForm` 输入/清空，提交后 `crypto.encrypt_key()` 存 `user.deepseek_key_enc`。
- **加密**：Fernet，密钥 `JK_FERNET_KEY` 放 `.env`（gitignore）。首次部署若 `.env` 无此键，`get_fernet()` 自动生成并追加。
- **读取**：仅服务端 `client` 通过 `user.deepseek_key` 属性读明文；明文不落日志、不进模板上下文。
- 旋转：用户在页面重新填入即可覆盖。

### 安全要点
- API key **密文落库**，不明文进 SQLite。
- 报告**固定带免责声明**：AI 生成，不构成投资建议，盈亏自负。
- 不对外暴露报告 API（`@login_required`）。

---

## 11. 定时任务（扩展 crontab）

```
30 12 * * * cd ~/home/claude_PJ/Jijin_Kanban && venv/bin/python manage.py run_ai_morning >>cron.log 2>&1
0  18 * * * cd ~/home/claude_PJ/Jijin_Kanban && venv/bin/python manage.py run_ai_evening >>cron.log 2>&1
```

- 每天跑（含周末）；周末新闻少时报告自然变短，属正常。
- 命令内部：遍历 `is_active=True & email_verified=True & 已填key` 的用户。

---

## 12. 配置项（`.env`，可选）

```
JK_FERNET_KEY=<auto-gen>          # key 加密密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com   # 可切代理/自建
DEEPSEEK_TIMEOUT=60
# 单价（用于 meta 成本估算，非必需）：
DEEPSEEK_PRICE_CHAT_IN=0.27
DEEPSEEK_PRICE_CHAT_OUT=1.10
DEEPSEEK_PRICE_REASONER_IN=0.55
DEEPSEEK_PRICE_REASONER_OUT=2.19
```

---

## 13. 测试策略（TDD；`deploy.sh` 硬门槛）

mock 掉 `client` 的 HTTP（`unittest.mock.patch`），覆盖：

- **client**：重试触发、错误归一化（401/429/5xx/network）、chat/reasoner 路由、usage 返回。
- **screening**：只对挑中条目取摘要（断言未挑中条目不被取 summary）；screening JSON 含 reason。
- **analysis**：mock 返回结构化 JSON → 断言 `reports.render` 输出含 5 段。
- **降级**：缺 key（定时跳过/手动报错）、key 失效（降级报告 status=degraded + 标题清单）、空新闻（短报告）、坏 JSON（降级）。
- **限额**：手动第 6 次被挡。
- **命令**：mock `generate_report`，断言只发给合规用户、邮件次数正确。
- **crypto**：加解密往返、缺失 key 自动生成。
- **portfolio_snapshot**：多基金聚合、trend_14d 截取。

---

## 14. 文件清单

```
aiagent/
├─ __init__.py apps.py admin.py urls.py
├─ models.py            # AnalysisReport
├─ crypto.py client.py context.py
├─ screening.py analysis.py prompts.py
├─ services.py          # generate_report（编排 + 降级）
├─ reports.py           # JSON→HTML
├─ emails.py views.py forms.py
├─ management/commands/{run_ai_morning,run_ai_evening}.py
└─ tests/{test_client,test_screening,test_analysis,test_services_degrade,
          test_quota,test_commands,test_crypto,test_snapshot}.py
templates/aiagent/{report_list,report_detail,key_settings}.html
templates/aiagent/emails/{morning,evening}.html
funds/services.py            # + portfolio_snapshot()
accounts/models.py           # + deepseek_key_enc + crypto property
news/models.py               # + finance_oversea choice（+ admin 加源）
config/settings.py           # INSTALLED_APPS 加 aiagent
config/urls.py               # include aiagent.urls
templates/base.html          # nav 加「AI报告」入口
requirements.txt             # + cryptography
.env                         # + JK_FERNET_KEY / DEEPSEEK_*
crontab                      # + 两条 AI 定时
```

---

## 15. 待定 / 未来

- **海外财经源的具体 RSS**：部署时实测可用性后选定（备选：华尔街见闻、财联社、金十数据）。
- **token 成本上限熔断**：若单用户单日消耗超阈值则暂停（本期先靠限额 + 报告 meta 观察，暂不做硬熔断）。
- **报告 RAG/历史关联**：未来可把历史报告喂入做趋势对比（本期不做）。
