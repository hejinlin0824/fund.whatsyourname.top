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
        # 用 set() 显式去重：.distinct() 受 Fund.Meta.ordering=["id"] 影响，在 SQLite
        # 上 `SELECT DISTINCT code ... ORDER BY id` 仍返回重复行(实测 14 只基金→14
        # 个代码，每个抓两遍，耗时翻倍)。set() 才能稳定去重为真实的不同代码。
        codes = sorted(set(Fund.objects.exclude(code="")
                           .values_list("code", flat=True)))
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
