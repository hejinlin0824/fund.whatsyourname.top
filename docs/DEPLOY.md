# 基金看板 部署运维说明

项目路径：`~/home/claude_PJ/Jijin_Kanban/`  端口：`8188`  访问：`http://49.234.26.95:8188/`

## 一键部署
```bash
cd ~/home/claude_PJ/Jijin_Kanban && bash deploy.sh
```
脚本依次执行：`makemigrations → migrate → 全量测试(失败即中止) → collectstatic → 重启 runserver → 健康检查`。

## 手动启停
```bash
# 启动（后台）
cd ~/home/claude_PJ/Jijin_Kanban
setsid bash -c 'venv/bin/python manage.py runserver 0.0.0.0:8188 --noreload </dev/null >>server.log 2>&1' &

# 停止（按端口找 PID）
PID=$(ss -ltnp 2>/dev/null | grep ":8188" | grep -oP 'pid=\K[0-9]+' | head -1)
[ -n "$PID" ] && kill -9 "$PID"
```
> 注意：`pkill -f "runserver...8188"` 会误杀执行该命令的 ssh 会话（命令行里含这串字），故用端口取 PID。

## 防火墙（两层都要放行 8188）
1. **腾讯云安全组**：入站规则 TCP 8188 / 0.0.0.0/0。
2. **服务器 ufw**：`sudo ufw allow 8188/tcp`。

## 邮件（QQ SMTP）
- 配置在 `.env`（已 gitignore，不入库）：
  - `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD`（SMTP 授权码，**非登录密码**）
  - `DEFAULT_FROM_EMAIL`
- 旋转授权码：QQ 邮箱 → 设置 → 账户 → SMTP 服务，删旧码建新码 → 编辑服务器 `.env` 的 `EMAIL_HOST_PASSWORD` → 重启服务。
- 测试发信：`venv/bin/python manage.py shell -c "from django.core.mail import send_mail; send_mail('t','b','1285021260@qq.com',['1285021260@qq.com'])"`

## 定时任务（crontab）
```
0  18 * * * cd ~/home/claude_PJ/Jijin_Kanban && venv/bin/python manage.py send_daily_email --reminder 1 >>cron.log 2>&1
0  21 * * * cd ~/home/claude_PJ/Jijin_Kanban && venv/bin/python manage.py send_daily_email --reminder 2 >>cron.log 2>&1
0  23 * * * cd ~/home/claude_PJ/Jijin_Kanban && venv/bin/python manage.py send_daily_email --reminder 3 >>cron.log 2>&1
30 23 * * * cd ~/home/claude_PJ/Jijin_Kanban && venv/bin/python manage.py finalize_daily >>cron.log 2>&1
```
- 工作日 18/21/23 三次阶梯提醒（已录入则不发）；23:30 未录入则标记当天为「无交易」。
- 周末仅 18 点发一封问候，不阶梯、不 finalize。

## 账号
- 测试账号：`jinlin` / `jk2026test`（DEBUG 期间用，正式上线前改密或删）。

## 安全注意
- `DEBUG=True` 仅用于测试；正式对外应 `DEBUG=False` + 走 nginx + 强制 HTTPS。
- 外部 CDN 已加 SRI（`integrity` + `crossorigin`），换版本需重算 sha384。
- 邮件 magic-link 令牌存于 `User.mail_login_token`，泄露可刷新。
