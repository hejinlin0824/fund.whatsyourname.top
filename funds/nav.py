"""基金净值（NAV）相关计算：定投微笑曲线 + 按净值估算单日盈亏。"""
from decimal import Decimal
from .models import FundNav


def nav_map(code):
    """返回 {date: unit_nav}。"""
    return dict(FundNav.objects.filter(code=code).values_list("date", "unit_nav"))


def _initial_shares(fund, nav):
    """起购前已有持仓按起购日净值折算的（份额, 成本）。"""
    if not fund.start_total:
        return Decimal("0"), Decimal("0")
    start_nav = nav.get(fund.start_date)
    if not start_nav:
        return Decimal("0"), Decimal(fund.start_total)
    return Decimal(fund.start_total) / Decimal(start_nav), Decimal(fund.start_total)


def fund_dca_curve(fund):
    """定投微笑曲线：逐记录日点
    {date, nav(单位净值), shares(累计份额), avg_cost(平均持仓成本 元/份), est_profit(按净值估算当日盈亏)}。"""
    nav = nav_map(fund.code)
    if not nav:
        return []
    shares, cum_cost = _initial_shares(fund, nav)
    last_nav = None
    points = []
    for r in fund.records.order_by("date"):
        d = r.date
        tod = nav.get(d)
        est = None
        if tod and last_nav is not None and r.has_trade:
            # 当日新买的按当日净值买入 → 0 盈亏，故只用"买入前份额"算
            est = (shares * (Decimal(tod) - Decimal(last_nav))).quantize(Decimal("0.01"))
        if r.has_trade and tod:
            eff = fund.effective_invested(r.invested or 0)
            if eff:
                shares += eff / Decimal(tod)
                cum_cost += eff
        if tod:
            last_nav = tod
        avg = (cum_cost / shares).quantize(Decimal("0.0001")) if shares else None
        points.append({
            "date": d.isoformat(),
            "nav": float(tod) if tod else None,
            "shares": float(shares.quantize(Decimal("0.01"))),
            "avg_cost": float(avg) if avg else None,
            "est_profit": float(est) if est is not None else None,
        })
    return points


def estimate_profit(fund, d):
    """按净值估算用户在日期 d 的盈亏（录入预填用）。
    考虑 QDII/美股净值发布滞后（confirm_delay：A股=0偏移、T+2=1偏移）。
    所需净值尚未发布则返回 None。"""
    nav = nav_map(fund.code)
    if not nav:
        return None
    shift = max(0, (fund.confirm_delay or 1) - 1)        # A股 0 / 美股QDII 1
    upto = sorted(x for x in nav if x <= d)
    if len(upto) < shift + 2:
        return None
    tod, prev = upto[-1 - shift], upto[-2 - shift]
    shares, _ = _initial_shares(fund, nav)
    for r in fund.records.filter(date__lt=tod, has_trade=True).order_by("date"):
        nv = nav.get(r.date)
        if nv:
            shares += fund.effective_invested(r.invested or 0) / Decimal(nv)
    return float((shares * (Decimal(nav[tod]) - Decimal(nav[prev]))).quantize(Decimal("0.01")))
