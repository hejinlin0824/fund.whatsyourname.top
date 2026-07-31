from django.core.management.base import BaseCommand
from funds.models import Fund, FundNav


class Command(BaseCommand):
    help = "抓取基金历史单位净值（akshare 单位净值走势），按代码缓存到 FundNav"

    def add_arguments(self, parser):
        parser.add_argument("--code", default=None, help="只抓指定代码")

    def handle(self, *args, **opts):
        try:
            import akshare as ak
        except Exception:
            self.stderr.write("akshare 未安装")
            return
        codes = list(Fund.objects.exclude(code="").exclude(code__isnull=True)
                     .values_list("code", flat=True).distinct())
        if opts["code"]:
            codes = [c for c in codes if c == opts["code"]]
        total = 0
        for code in codes:
            try:
                df = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
            except Exception as e:
                self.stderr.write(f"{code}: 抓取失败 {str(e)[:60]}")
                continue
            n = 0
            for _, row in df.iterrows():
                d = row.get("净值日期")
                nv = row.get("单位净值")
                if not d or nv is None:
                    continue
                FundNav.objects.update_or_create(
                    code=code, date=d, defaults={"unit_nav": round(float(nv), 4)})
                n += 1
            total += n
            self.stdout.write(f"{code}: {n} 条净值")
        self.stdout.write(self.style.SUCCESS(f"完成，共 {total} 条净值，{len(codes)} 个代码"))
