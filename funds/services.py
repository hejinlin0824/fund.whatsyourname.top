from datetime import date, timedelta
from decimal import Decimal


def compute_total(prev_total, profit, invested) -> Decimal:
    """反推当日总额 = 前日总额 + 当日盈亏 + 当日投入。profit 为空（首日）视为 0。"""
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
    """从 fund.start_date 起逐日重算 total 与 pending。返回处理记录数。"""
    records = list(fund.records.order_by("date"))
    if not records:
        return 0
    prev = Decimal(fund.start_total)
    first = True
    for r in records:
        if first:                       # 首日：total = start_total；profit 忽略
            r.total = Decimal(fund.start_total)
            r.pending = compute_pending(records, r.date, fund.confirm_delay)
            prev = r.total
            first = False
        else:
            r.total = compute_total(prev, r.profit, r.invested)
            r.pending = compute_pending(records, r.date, fund.confirm_delay)
            prev = r.total
        r.save()
    return len(records)


def validate_ratio(profit, prev_total, given_ratio, tolerance=Decimal("0.005")):
    """比例校验：返回 (是否一致, 系统计算的比例)。given_ratio 为空则跳过（返回 True, None）。"""
    if given_ratio is None or prev_total == 0:
        return True, None
    p = Decimal("0") if profit is None else Decimal(profit)
    computed = p / Decimal(prev_total)
    return abs(computed - Decimal(given_ratio)) <= tolerance, computed


def validate_total(fund, current_total) -> dict:
    """终点总额校验：比较最后一条记录的 total 与 current_total。容差 0.01。"""
    last = fund.records.order_by("date").last()
    if last is None:
        return {"ok": False, "last_total": None, "diff": None}
    diff = Decimal(last.total) - Decimal(current_total)
    return {"ok": abs(diff) <= Decimal("0.01"), "last_total": last.total, "diff": diff}
