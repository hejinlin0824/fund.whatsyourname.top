from django.core.management.base import BaseCommand
from accounts.models import User
from aiagent import services, emails


class Command(BaseCommand):
    help = "午间 AI 报告：生成 + 发邮件"

    def handle(self, *a, **kw):
        sent, skipped = 0, 0
        for u in User.objects.filter(is_active=True, email_verified=True):
            if not u.deepseek_key:
                skipped += 1
                continue
            try:
                rep = services.generate_report(u, "morning")
                emails.send_report_email(rep)
                sent += 1
            except services.NoApiKey:
                skipped += 1
            except Exception as e:  # 单用户失败不阻断其他用户
                self.stderr.write(f"ERR {u.username}: {e}")
        self.stdout.write(self.style.SUCCESS(f"morning: sent={sent} skipped={skipped}"))
