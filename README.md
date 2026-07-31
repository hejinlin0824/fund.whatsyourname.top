# Whatsyour 基金看板（Jijin_Kanban）

个人基金仓位与盈亏监控 + 新闻聚合 + AI 智能体分析。场外基金为主（A股 + 美股）。

**线上**：https://fund.whatsyourname.top （nginx + HTTPS → 反代 Django）

---

## 功能一览

- **基金仓位 / 盈亏**：邮件驱动录入每日盈亏，系统**反推每日总额**
  `V_t = V_{t-1} + profit + invested×(1−fee_rate)`；申购费率自动扣；A股 T+1 / 美股 T+2 待确认；日历视图、组合看板、走势图。
- **新闻聚合**：5 分类（时政 / A股 / 海外财经 / 国内科技 / 海外科技），RSS + HackerNews + AkShare，数据源**可插拔**（失效改 URL 即可），DRF 支持批量导出喂 AI。
- **AI 智能体分析**：每日 **12:30 / 18:00** 结合新闻 + 仓位生成报告（**两段式 LLM**：标题初筛 → 深度分析），邮件推送 + 站内历史 + 按需生成；每条建议带**仓位/新闻引用**，结论可追溯。

---

## 技术栈

Python 3.12 · Django 6.0 · SQLite · Bootstrap 5 + Bootstrap Icons + Chart.js · DRF · cryptography(Fernet) · DeepSeek API · QQ SMTP · cron + management commands（**无 Celery**）

---

## 目录结构

```
Jijin_Kanban/
├─ config/                      # Django 项目配置
│  ├─ settings.py               #   读 .env：SECRET_KEY/SMTP/ALLOWED_HOSTS/CSRF/SSL 代理头
│  ├─ urls.py / wsgi.py / asgi.py
│
├─ accounts/                    # 用户：注册 / 邮箱验证 / 魔法链接免密登录
│  ├─ models.py                 #   User(AbstractUser) + email_verified + mail_login_token + deepseek_key_enc(加密)
│  ├─ mails.py / tokens.py      #   邮件发送 / 登录令牌
│  └─ views.py / forms.py / urls.py
│
├─ funds/                       # 核心：基金 / 每日记录 + 计算服务 + 录入与报表
│  ├─ models.py                 #   Fund / Tag / DailyRecord（unique fund+date）
│  ├─ services.py               #   recompute_fund_totals / backfill_fund / fund_summary / portfolio_snapshot ★
│  ├─ actions.py                #   ActionLog：记录新增/调额/停投/清仓/改名（喂给当日 AI）
│  ├─ forms.py                  #   中文友好表单
│  ├─ views.py                  #   fund_list/detail/create/edit、daily_entry、dashboard、calendar、portfolio
│  └─ management/commands/      #   send_daily_email（阶梯提醒）、finalize_daily（未录入标无交易）
│
├─ news/                        # 新闻：Source / Article + 抓取 / 清洗 / DRF
│  ├─ models.py                 #   Source(可插拔) / Article；5 分类
│  ├─ fetchers.py               #   按 kind 分发：RSS / HN / AKSHARE
│  ├─ cleaners.py               #   时间解析 / 摘要兜底
│  ├─ api.py                    #   DRF：列表 / 搜索 / 批量导出
│  └─ management/commands/fetch_news.py   #   --source <slug> 可单抓
│
├─ aiagent/                     # AI 智能体分析（DeepSeek 两段式流水线）
│  ├─ models.py                 #   AnalysisReport（条件唯一约束）、ActionLog
│  ├─ crypto.py                 #   Fernet 加解密 DeepSeek key
│  ├─ client.py                 #   DeepSeek HTTP：chat/reasoner + 重试 + 错误归一化
│  ├─ context.py                #   news 标题/摘要 + portfolio_text + recent_operations_text
│  ├─ prompts.py                #   初筛 / 午间 / 晚间 提示词
│  ├─ screening.py              #   ① 标题初筛（chat）→ 挑值得深读的条目
│  ├─ analysis.py               #   ② 深度分析（午=chat / 晚=reasoner）→ 结构化 JSON（带 refs）
│  ├─ reports.py                #   结构化 JSON → 5 段 HTML（邮件+站内共用）
│  ├─ services.py               #   generate_report 编排器 + 降级（绝不静默失败）
│  ├─ emails.py                 #   send_report_email
│  ├─ views.py / forms.py / urls.py   #   报告列表/详情/删除、立即分析(限额)、Key 设置
│  ├─ templatetags/ai_extras.py #   模板 dict 取值过滤器
│  └─ management/commands/      #   run_ai_morning（12:30）、run_ai_evening（18:00）
│
├─ templates/                   # base.html + accounts/ funds/ news/ aiagent/（含 emails/）
├─ static/  staticfiles/        # 静态资源（collectstatic 产物）
├─ docs/                        # 设计文档 + plans/ + DEPLOY.md
│  └─ superpowers/{specs,plans}/2026-07-30-ai-agent-analysis-*.md
│
├─ manage.py
├─ deploy.sh                    # 一键部署：makemigrations→migrate→测试(失败即止)→collectstatic→重启→健康检查
├─ requirements.txt
├─ .env                         # ⚠️ gitignore，不入库（SECRET_KEY/SMTP/JK_FERNET_KEY/DEEPSEEK_*）
├─ db.sqlite3                   # ⚠️ gitignore，不入库
└─ venv/                        # gitignore
```

---

## 核心领域逻辑（最易改错）

- **总额反推**（`funds/services.py: recompute_fund_totals`）：`running` 从 `start_total` 起步，`total_t = running + profit + invested×(1−fee)`；遇 `has_trade=True` 但 `profit=None`（未补录）则 `total=None` 且之后皆 None。
- **基金三态**：`is_active`（定投中）/ `is_active=False` 未清仓（停投仍记盈亏）/ `is_cleared`（清仓不再追踪）。
- **AI 两段式**：① 只喂标题省钱初筛 → ② 只对筛中条目取摘要深读；**午间模板无明日预判、晚间含明日预判**（手动按时段自动切）；每条建议带 `refs`（仓位/新闻引用）。

---

## 定时任务（crontab）

```
0  18,21,23 * * *  ... send_daily_email --reminder 1/2/3   # 工作日阶梯录入提醒
30 23 * * *        ... finalize_daily                       # 未录入标"无交易"
0  */3 * * *       ... fetch_news                           # 新闻抓取（每 3 小时）
30 12 * * *        ... run_ai_morning                       # 午间 AI 报告（chat）
0  18 * * *        ... run_ai_evening                       # 晚间 AI 报告（reasoner）
```

---

## 本地开发 & 部署

```bash
# 一次性
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # 填 SECRET_KEY / SMTP / JK_FERNET_KEY

# 跑起来
venv/bin/python manage.py migrate
venv/bin/python manage.py test            # 约 100 项，全绿才放心
venv/bin/python manage.py runserver 0.0.0.0:8188

# 服务器一键部署（迁移 + 测试 + 重启 + 健康检查）
bash deploy.sh
```

生产：nginx + Let's Encrypt HTTPS 反代 `:8188`（`DEBUG=False`）。详见 `docs/DEPLOY.md`。

---

## 文档

- **AGENTS.md** —— 给 AI / 开发者的上手指南（最全，读完即可干活）
- `docs/DEPLOY.md` —— 部署运维
- `docs/superpowers/specs/2026-07-30-ai-agent-analysis-design.md` —— AI 功能设计
- `docs/superpowers/plans/2026-07-30-ai-agent-analysis.md` —— AI 功能实现计划

---

> ⚠️ AI 报告由模型生成，仅供参考，**不构成投资建议**，据此操作盈亏自负。
