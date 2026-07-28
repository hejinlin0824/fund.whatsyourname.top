from datetime import date
from decimal import Decimal
from django.core.management.base import BaseCommand
from accounts.models import User
from funds.models import DailyRecord
from funds import services


class Command(BaseCommand):
    help = "23:30 若用户当日未录入，把各基金当天标记为无交易（has_trade=False）并重算"

    def add_arguments(self, parser):
        parser.add_argument("--date", default=None, help="YYYY-MM-DD，默认今天")

    def handle(self, *args, **opts):
        d = date.fromisoformat(opts["date"]) if opts["date"] else date.today()
        n = 0
        for u in User.objects.filter(is_active=True):
            funds = list(u.funds.filter(is_cleared=False, start_date__lte=d))
            if not funds:
                continue
            engaged = DailyRecord.objects.filter(
                fund__user=u, date=d, profit__isnull=False).exists()
            if engaged:
                continue
            for f in funds:
                DailyRecord.objects.update_or_create(fund=f, date=d, defaults={
                    "has_trade": False, "invested": Decimal("0"), "profit": Decimal("0")})
                n += 1
            for f in funds:
                services.recompute_fund_totals(f)
        self.stdout.write(self.style.SUCCESS(f"finalized {n} records for {d}"))
