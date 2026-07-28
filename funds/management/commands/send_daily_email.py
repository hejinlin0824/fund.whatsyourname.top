from datetime import date
from django.core.management.base import BaseCommand
from accounts.models import User
from funds.models import DailyRecord
from accounts.mails import send_daily_entry_email, send_weekend_email


class Command(BaseCommand):
    help = "每日邮件提醒：工作日阶梯提醒（未录入才发）/ 周末问候（仅第1次）"

    def add_arguments(self, parser):
        parser.add_argument("--date", default=None, help="YYYY-MM-DD，默认今天")
        parser.add_argument("--reminder", type=int, default=1, help="第几次提醒(1/2/3)")

    def handle(self, *args, **opts):
        d = date.fromisoformat(opts["date"]) if opts["date"] else date.today()
        host = "http://49.234.26.95:8188"
        sent = 0
        for u in User.objects.filter(is_active=True, email_verified=True):
            # 该日有需要追踪的基金（未清仓、已起购）才提醒
            if not u.funds.filter(is_cleared=False, start_date__lte=d).exists():
                continue
            if d.weekday() >= 5:                      # 周末：仅第1次发问候
                if opts["reminder"] == 1:
                    send_weekend_email(u)
                    sent += 1
                continue
            # 工作日：已录入（任意基金当天有 profit）则不打扰
            engaged = DailyRecord.objects.filter(
                fund__user=u, date=d, profit__isnull=False).exists()
            if engaged:
                continue
            send_daily_entry_email(u, host, opts["reminder"])
            sent += 1
        self.stdout.write(self.style.SUCCESS(
            f"sent {sent} emails for {d} (reminder {opts['reminder']})"))
