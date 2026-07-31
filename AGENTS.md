# AGENTS.md — Whatsyour 基金看板

> 给后续 AI 对话/开发者快速上手用。读完这页就能干活。

## 一句话
个人基金仓位与盈亏监控网站（Django + SQLite），邮件驱动录入每日盈亏，系统反推每日总额；附带新闻聚合模块（为后续 AI 投喂做语料）。**场外基金为主，A股+美股。**

- **线上**：`https://fund.whatsyourname.top/`（nginx + Let's Encrypt HTTPS → 反代 :8188，**DEBUG=False 生产**；DNSPod 解析 `fund` A→49.234.26.95）
- **直连调试**：`http://49.234.26.95:8188/`（8188 仍开，方便调试）
- **项目路径**：服务器 `~/home/claude_PJ/Jijin_Kanban/`
- **本地暂存**：`E:\codebase\server_stuff\_jk\`（改文件在这里改，再 scp 上去）

## 技术栈
Python 3.12 · Django 6.0.1 · SQLite · Bootstrap 5 + Bootstrap Icons + Chart.js · DRF · QQ SMTP · cron + management commands（**无 Celery**）。aiagent 用 DeepSeek API + cryptography(Fernet 加密 key)。venv 在项目根 `venv/`。

## ⚠️ 开发工作流（重要，省额度）
用户要求**用脚本一次性做事，不要反复 ssh/scp 调 API**。标准循环：
1. 本地在 `E:\codebase\server_stuff\_jk\` 改文件（文件名带前缀如 `tpl_*.html`/`funds_*.py`/`news_*.py`，scp 时映射到真实路径）。
2. **一条 scp** 传所有改动文件（各自指定目标全名，别批量传到目录——会丢原名）。
3. **一条** `ssh ... 'cd ~/home/claude_PJ/Jijin_Kanban && bash deploy.sh'`。
4. `deploy.sh` 一次完成：`makemigrations → migrate → 全量测试(失败即中止) → collectstatic → 重启 runserver → 健康检查`。
- 不要逐个跑 migrate/test/restart/verify——全在 deploy.sh 里。
- **测试是硬门槛**：deploy.sh 里测试不过会中止、不重启。改逻辑先想测试。

## 目录结构
```
~/home/claude_PJ/Jijin_Kanban/
├─ venv/                      # 虚拟环境（gitignore）
├─ .env                       # SECRET_KEY/SMTP 授权码（gitignore，不入库）
├─ deploy.sh                  # 一键部署脚本
├─ manage.py
├─ config/                    # settings.py / urls.py / wsgi.py
├─ accounts/                  # 用户：注册/邮箱验证/magic-link 免密登录
├─ funds/                     # 核心：Fund/Tag/DailyRecord + 计算服务 + 录入/报表
│   ├─ services.py            # ★ 计算逻辑（纯函数，重点）
│   ├─ forms.py               # 友好表单（中文标签/必填星标/释义）
│   └─ management/commands/   # send_daily_email / finalize_daily
├─ news/                      # 新闻：Source/Article + 抓取/清洗/DRF
│   ├─ cleaners.py / fetchers.py / api.py
│   └─ management/commands/fetch_news.py
├─ aiagent/                   # AI 分析：两段式 LLM（标题初筛→深读），报告+邮件+站内历史
│   ├─ client.py / screening.py / analysis.py / reports.py / services.py / emails.py
│   └─ management/commands/run_ai_morning.py / run_ai_evening.py
├─ templates/  static/
└─ docs/                      # 设计文档 + DEPLOY.md
```

## AI 智能体分析（aiagent）
每日结合新闻+仓位生成 AI 报告，午间(12:30)/晚间(18:00)各发一封邮件，站内 `/aiagent/` 可翻阅历史 + 「立即分析」(每日 5 次；列表显示"今日还剩 N/5"、生成时按钮转圈、详情页可删除)。
- **两段式流水线（省 token）**：①`screening` 喂当天全部标题(chat)挑值得深读的~15条 → ②`analysis` 只对这些取摘要+仓位深读 → 结构化 JSON → `reports.render` 成 5 段卡片（新闻速览/利好方向/仓位建议/明日预判/小白课堂 + 免责声明）。全站无 emoji，用 Bootstrap Icons。
- **模型按时段**：午间 cron / 手动 <15 点 → `noon` 模式(chat，**无明日预判**)；晚间 cron / 手动 ≥15 点 → `evening` 模式(reasoner，**含明日预判**)。利好=红/利空=绿（同全站惯例）。
- **引用标注 refs**：每条利好/仓位建议必须带 `refs`——仓位参考具体到哪只基金+现状、新闻参考点明标题，渲染成"参考：…"，让结论可追溯。
- **操作追踪注入**：新增/编辑基金时 `funds/actions.py` 记 `ActionLog`（新增/调额/停投/恢复/清仓/改名），当日 AI 总结注入"【今日操作】…"告诉 AI 你今天动了什么。
- **激活前提**：用户在 `/aiagent/key/` 填 DeepSeek key（Fernet 加密存 `accounts.User.deepseek_key_enc`，密钥 `JK_FERNET_KEY` 在 `.env`）。没填 → 定时跳过、手动触发跳去填。
- **降级**：key 缺失/失效/限流/坏 JSON → 发降级邮件（正文置顶说明 + 当日新闻标题清单），报告 `status=degraded`，绝不静默。
- **仓位上下文**：`funds/services.portfolio_snapshot(user)` 返回纯数据 dict（aiagent 不翻 funds 内部）；报告详情页顶部还展示实时持仓 stat 行（总市值/投入/盈亏/收益率）。
- 设计 `docs/superpowers/specs/2026-07-30-ai-agent-analysis-design.md`，计划 `docs/superpowers/plans/2026-07-30-ai-agent-analysis.md`。

## 核心领域逻辑（最容易改错的地方）

**总额反推公式**（`funds/services.py: recompute_fund_totals`）：
```
running 从 start_total 起步
total_t = running + invested_t×(1−fee_rate) + profit_t
```
- `start_total` = 起购日【之前】已有持仓；从第一笔买入开始记就填 0（不是当天总额）。
- **费率** `Fund.fee_rate`（%）：`effective_invested = invested × (1 − fee_rate/100)`，C 类填 0。
- **级联**：遇到 `has_trade=True` 且 `profit=None`（未补录）的天，`total=None`，之后皆 None（不能算）。
- **休息日** `has_trade=False`：盈亏视为 0，total 续上。

**基金三态**（别混）：
| 字段 | 含义 | 日录入页 | 投入默认 |
|-----|------|---------|---------|
| `is_active=True` | 仍在定投 | 显示 | invest_amount |
| `is_active=False`（未清仓）| 停投但持仓 | **显示** | **0**（仍记盈亏）|
| `is_cleared=True` | 已清仓 | **不显示** | — |

- `dca_invest_for(d)`：停投后(end_date 之后)投入自动 0。
- `confirm_delay`（A股 T+1 / 美股 T+2）→ `compute_pending` 算"待确认"。

## 数据模型
- **accounts.User**（AbstractUser）+ `email_verified` + `mail_login_token`（magic link 令牌）
- **funds.Fund**：name/code/market/confirm_delay/invest_amount/invest_frequency/fee_rate/start_date/start_total/is_active/end_date/is_cleared/tags
- **funds.DailyRecord**：fund/date(profit 可空)/profit_ratio/invested/total(可空=None=未知)/pending/has_trade；unique(fund,date)
- **funds.Tag**：user/name
- **news.Source**：name/slug/kind(RSS/HN/AKSHARE)/category/url/enabled（**可插拔**，RSS 失效改 url 即可）
- **news.Article**：title/summary/content/url(唯一)/published_at/category/source/extra(JSON预留)/funds(M2M预留)

## 定时任务（crontab）
```
0 18,21,23 * * *  ... send_daily_email --reminder 1/2/3   # 工作日阶梯提醒
30 23 * * *       ... finalize_daily                       # 未录入标无交易
0 */3 * * *       ... fetch_news                           # 新闻抓取（全量慢，HN 串行 31 请求）
30 12 * * *       ... run_ai_morning                       # 午间 AI 报告（chat，无明日预判）
0  18 * * *       ... run_ai_evening                       # 晚间 AI 报告（reasoner，含明日预判）
```
- 工作日未录入才发提醒；周末仅问候。magic link 点开自动登录到当日录入页。
- AI 命令遍历 `is_active & email_verified & 已填 DeepSeek key` 的用户。

## 新闻模块
- 5 分类：时政国际 / A股财经 / **海外财经(finance_oversea)** / 国内科技 / 海外科技。
- 数据源：中新网 7 个 RSS（politics/finance）、HackerNews API（tech_oversea）、AkShare（finance）、**CNBC×2 + NPR Business（finance_oversea，美股/美国经济）**。
- **国内科技分类暂无源**（36氪 RSS 已死）——补源去 `/admin/news/source/` 加一条（kind=RSS，选 category），不用改代码。
- ⚠️ `fetch_news` 全量跑慢，卡在 HackerNews（串行 31 请求 ×15s 超时）；单抓某源用 `fetch_news --source <slug>`。
- DRF：`/news/api/articles/?category=&search=`，`/news/api/articles/export/?start=&end=` 批量导出喂 AI。

## 测试
`venv/bin/python manage.py test`（约 100 项，含 cleaners/计算/CRUD/录入/邮件/aiagent 全套：client/screening/analysis/reports/services/tracking/views）。改逻辑务必配套测试，deploy.sh 会跑。

## 常见坑
- **logout 必须 POST**（Django 5+ LogoutView 拒绝 GET）——导航里用 form。
- **别 `pkill -f "runserver...8188"`**：会误杀执行命令的 ssh 会话（命令行含这串字）。用端口取 PID：`ss -ltnp | grep :8188 | grep -oP 'pid=\K[0-9]+'`。`deploy.sh` 已处理。
- **端口 8188 双层防火墙**：腾讯云安全组 + 服务器 ufw 都要放行。
- **不要把本地 db.sqlite3 推回服务器**——会覆盖真实数据。`.env`/db/venv 都 gitignore。
- 表单日期字段用 `DateInput(format="%Y-%m-%d")`，否则编辑时起购日不回填。

## 账号 & 密钥
- 主力账号：`hejinlin` / `ll990824`（邮箱 1285021260@qq.com，已填 DeepSeek key，AI 邮件发这）。
- 演示账号：`yanshi` / `123456`（邮箱 hejinlindeyouxiang@gmail.com，数据复制自 hejinlin）。
- SMTP 授权码在 `.env` 的 `EMAIL_HOST_PASSWORD`（QQ 邮箱授权码，非登录密码）。**曾在对话泄露，用户应已旋转**。
- `SECRET_KEY` 也在 `.env`。

## 设计文档
- `docs/superpowers/specs/2026-07-27-jijin-kanban-design.md` — 完整设计
- `docs/superpowers/plans/2026-07-27-jijin-kanban.md` — 实现计划
- `docs/DEPLOY.md` — 部署运维
