from datetime import date, timedelta
from decimal import Decimal


def compute_total(prev_total, profit, invested) -> Decimal:
    """反推当日总额 = 前日总额 + 当日盈亏 + 当日投入。profit 为空视为 0。"""
    p = Decimal("0") if profit is None else Decimal(profit)
    i = Decimal("0") if invested is None else Decimal(invested)
    return Decimal(prev_total) + p + i


def compute_pending(records, d: date, confirm_delay: int) -> Decimal:
    """待确认 = 最近 confirm_delay 天（含 d）的 invested 之和。records 为升序列表。"""
    total = Decimal("0")
    for k in range(confirm_delay):
        cur = d - timedelta(days=k)
        for r in records:
            if r.date == cur:
                total += Decimal(r.invested or 0)
                break
    return total


def recompute_fund_totals(fund) -> int:
    """逐日重算 total 与 pending。

    公式：total_t = running + invested_t + profit_t，running 从 start_total 起步。
    级联：遇到 has_trade=True 但 profit 为空（待补录）的天，total=None，且之后皆 None。
    休息日(has_trade=False) 盈亏视为 0。
    """
    records = list(fund.records.order_by("date"))
    if not records:
        return 0
    running = Decimal(fund.start_total)
    known = True
    for r in records:
        r.pending = compute_pending(records, r.date, fund.confirm_delay)
        if not r.has_trade:
            r.total = running if known else None
        elif r.profit is None:
            r.total = None
            known = False
        else:
            r.total = (running + Decimal(r.profit) + fund.effective_invested(r.invested)) if known else None
        if r.total is not None:
            running = r.total
            known = True
        r.save()
    return len(records)


def backfill_fund(fund, until: date = None) -> int:
    """从 start_date 补齐 DailyRecord 槽位。

    - 未清仓：补到今天（停投后 invested 自动为 0，仍建槽位记盈亏）。
    - 已清仓：补到 end_date（之后不再追踪）。
    周末→休息日；交易日→首日盈亏 0（基准），其余留空待补。
    """
    from .models import DailyRecord
    today = date.today()
    until = until or today
    if fund.is_cleared and fund.end_date:
        until = min(until, fund.end_date)
    until = min(until, today)
    existing = set(fund.records.values_list("date", flat=True))
    created = 0
    d = fund.start_date
    while d <= until:
        if d not in existing:
            if d.weekday() >= 5:
                DailyRecord.objects.create(fund=fund, date=d, has_trade=False,
                                            invested=Decimal("0"), profit=Decimal("0"))
            else:
                inv = fund.dca_invest_for(d)
                profit = Decimal("0") if d == fund.start_date else None
                DailyRecord.objects.create(fund=fund, date=d, has_trade=True,
                                            invested=inv, profit=profit)
            created += 1
        d += timedelta(days=1)
    if created:
        recompute_fund_totals(fund)
    return created


def validate_ratio(profit, prev_total, given_ratio, tolerance=Decimal("0.005")):
    if given_ratio is None or prev_total == 0:
        return True, None
    p = Decimal("0") if profit is None else Decimal(profit)
    computed = p / Decimal(prev_total)
    return abs(computed - Decimal(given_ratio)) <= tolerance, computed


def validate_total(fund, current_total) -> dict:
    last = fund.records.order_by("date").last()
    if last is None or last.total is None:
        return {"ok": False, "last_total": None, "diff": None}
    diff = Decimal(last.total) - Decimal(current_total)
    return {"ok": abs(diff) <= Decimal("0.01"), "last_total": last.total, "diff": diff}
