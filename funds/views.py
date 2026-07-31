import calendar as _cal
from datetime import date as date_cls, timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse

from .models import Fund, DailyRecord
from .forms import FundForm, DailyEntryFormSet
from . import services
from .actions import log_fund_create, log_fund_edit


def _today(request):
    d = request.GET.get("date")
    return date_cls.fromisoformat(d) if d else date_cls.today()


def _recompute_all(funds):
    for f in funds:
        services.recompute_fund_totals(f)


def _next_trading_day(d):
    nxt = d + timedelta(days=1)
    while nxt.weekday() >= 5:
        nxt += timedelta(days=1)
    return nxt


def _prev_trading_day(d):
    prv = d - timedelta(days=1)
    while prv.weekday() >= 5:
        prv -= timedelta(days=1)
    return prv


def _finalize_end_date(fund):
    if not fund.end_date and (not fund.is_active or fund.is_cleared):
        fund.end_date = date_cls.today()
        fund.save()


def _fund_summary(fund):
    """单基金汇总（委托 services.fund_summary，保持单一计算口径）。"""
    return services.fund_summary(fund)


@login_required
def fund_list(request):
    funds = Fund.objects.filter(user=request.user)
    rows = [(f, _fund_summary(f)) for f in funds]
    return render(request, "funds/fund_list.html", {"rows": rows})


@login_required
def fund_create(request):
    form = FundForm(request.POST or None)
    if form.is_valid():
        fund = form.save(commit=False)
        fund.user = request.user
        fund.save()
        form.save_m2m()
        _finalize_end_date(fund)
        services.backfill_fund(fund)
        services.recompute_fund_totals(fund)
        log_fund_create(request.user, fund)
        return redirect("fund-list")
    return render(request, "funds/fund_form.html", {"form": form})


@login_required
def fund_edit(request, pk):
    fund = get_object_or_404(Fund, pk=pk, user=request.user)
    form = FundForm(request.POST or None, instance=fund)
    if form.is_valid():
        old = {"invest_amount": fund.invest_amount, "is_active": fund.is_active,
               "is_cleared": fund.is_cleared, "name": fund.name}
        fund = form.save()
        _finalize_end_date(fund)
        services.backfill_fund(fund)
        services.recompute_fund_totals(fund)
        log_fund_edit(request.user, fund, old)
        return redirect("fund-list")
    return render(request, "funds/fund_form.html", {"form": form})


@login_required
def daily_entry(request):
    d = _today(request)
    funds = list(Fund.objects.filter(user=request.user, is_cleared=False, start_date__lte=d))
    saved_back = reverse("daily-entry") + f"?date={d.isoformat()}&saved=1"

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "no_trade":
            for f in funds:
                DailyRecord.objects.update_or_create(
                    fund=f, date=d,
                    defaults={"has_trade": False, "invested": Decimal("0")})
            _recompute_all(funds)
            return redirect(saved_back)

        formset = DailyEntryFormSet(request.POST)
        if formset.is_valid():
            for frm in formset:
                fund = Fund.objects.get(pk=frm.cleaned_data["fund"], user=request.user)
                profit = frm.cleaned_data.get("profit")
                if profit is None and not fund.is_dca_day(d):
                    continue
                invested = frm.cleaned_data.get("invested")
                if invested is None:
                    invested = fund.dca_invest_for(d)
                DailyRecord.objects.update_or_create(fund=fund, date=d, defaults={
                    "profit": profit or Decimal("0"),
                    "profit_ratio": frm.cleaned_data.get("profit_ratio"),
                    "invested": invested,
                    "has_trade": True,
                })
            _recompute_all(funds)
            return redirect(saved_back)

    from .nav import estimate_profit
    initial = []
    estimated = set()
    for f in funds:
        rec = f.records.filter(date=d).first()
        invested = rec.invested if rec else f.dca_invest_for(d)
        if rec and rec.has_trade and rec.profit is not None:
            profit_val = rec.profit
        else:
            est = estimate_profit(f, d)
            profit_val = Decimal(str(est)).quantize(Decimal("0.01")) if est is not None else ""
            if est is not None:
                estimated.add(f.id)
        initial.append({
            "fund": f.id,
            "profit": profit_val,
            "profit_ratio": rec.profit_ratio if rec else "",
            "invested": invested,
        })
    formset = DailyEntryFormSet(initial=initial)
    pairs = list(zip(formset, funds))

    today = date_cls.today()
    nxt = _next_trading_day(d)
    prv = _prev_trading_day(d)
    earliest = min((f.start_date for f in funds), default=d)
    context = {
        "formset": formset, "pairs": pairs, "date": d, "saved": request.GET.get("saved") == "1",
        "estimated": estimated,
        "prev_date": prv if prv >= earliest else None,
        "next_date": nxt if nxt <= today else None,
    }
    return render(request, "funds/daily_entry.html", context)


@login_required
def dashboard(request):
    funds = Fund.objects.filter(user=request.user)
    total_value = Decimal("0")
    total_invested = Decimal("0")
    total_profit = Decimal("0")
    fund_pairs = []
    for f in funds:
        s = _fund_summary(f)
        total_value += s["mv"]
        total_invested += s["cost"]
        total_profit += s["profit"]
        fund_pairs.append((f, s))
    ratio = (total_profit / total_invested * 100) if total_invested else Decimal("0")
    return render(request, "funds/dashboard.html", {
        "fund_pairs": fund_pairs, "total_value": total_value,
        "total_invested": total_invested, "total_profit": total_profit, "ratio": ratio,
    })


@login_required
def calendar_view(request):
    today = date_cls.today()
    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))
    first = date_cls(year, month, 1)
    last_day = _cal.monthrange(year, month)[1]

    recs = DailyRecord.objects.filter(fund__user=request.user,
                                      date__year=year, date__month=month)
    by_date = {}
    for r in recs:
        by_date.setdefault(r.date, []).append(r)

    days = []
    for dnum in range(1, last_day + 1):
        dt = date_cls(year, month, dnum)
        rows = by_date.get(dt, [])
        day_profit = sum((Decimal(r.profit) for r in rows if r.profit is not None), Decimal("0"))
        if dt > today:
            status = "future"
        elif rows:
            if any(r.has_trade and r.profit is None for r in rows):
                status = "pending"
            elif any(r.has_trade for r in rows):
                status = "filled"
            else:
                status = "rest"
        else:
            status = "empty"
        pcls = "up" if day_profit > 0 else ("down" if day_profit < 0 else "")
        days.append({"date": dt, "status": status, "profit": day_profit, "pcls": pcls})

    cells = [None] * first.weekday() + days
    while len(cells) % 7 != 0:
        cells.append(None)
    weeks = [cells[i:i + 7] for i in range(0, len(cells), 7)]

    def prev(y, m):
        return (y, m - 1) if m > 1 else (y - 1, 12)

    def nxt(y, m):
        return (y, m + 1) if m < 12 else (y + 1, 1)

    return render(request, "funds/calendar.html", {
        "year": year, "month": month, "month_label": f"{year}年{month}月",
        "weekdays": ["一", "二", "三", "四", "五", "六", "日"],
        "weeks": weeks,
        "prev_ym": prev(year, month),
        "next_ym": nxt(year, month),
        "today": today,
    })


@login_required
def fund_detail(request, pk):
    fund = get_object_or_404(Fund, pk=pk, user=request.user)
    return render(request, "funds/fund_detail.html", {"fund": fund, "s": _fund_summary(fund)})


@login_required
def fund_detail_data(request, pk):
    fund = get_object_or_404(Fund, pk=pk, user=request.user)
    recs = fund.records.order_by("date")
    from .nav import fund_dca_curve
    cn = [p for p in fund_dca_curve(fund) if p["nav"] and p["avg_cost"]]
    return JsonResponse({
        "dates": [r.date.isoformat() for r in recs],
        "totals": [None if r.total is None else float(r.total) for r in recs],
        "profits": [None if r.profit is None else float(r.profit) for r in recs],
        "invested": [float(r.invested) for r in recs],
        "curve": {"dates": [p["date"] for p in cn],
                  "nav": [p["nav"] for p in cn],
                  "avg_cost": [p["avg_cost"] for p in cn]},
    })


@login_required
def portfolio(request):
    funds = Fund.objects.filter(user=request.user)
    mv = cost = Decimal("0")
    for f in funds:
        s = _fund_summary(f)
        mv += s["mv"]
        cost += s["cost"]
    profit = mv - cost
    roi = (profit / cost * 100) if cost else Decimal("0")
    return render(request, "funds/portfolio.html", {"mv": mv, "cost": cost, "profit": profit, "roi": roi})


@login_required
def portfolio_data(request):
    funds = list(Fund.objects.filter(user=request.user).order_by("id"))
    fund_recs = {f.id: dict(f.records.exclude(total__isnull=True)
                            .order_by("date").values_list("date", "total")) for f in funds}
    inv_map = {f.id: {d: f.effective_invested(inv)
                      for d, inv in f.records.values_list("date", "invested")} for f in funds}
    all_dates = sorted(set(DailyRecord.objects.filter(fund__user=request.user)
                           .values_list("date", flat=True)))
    profit_by_date = {}
    for f in funds:
        for d, p in f.records.exclude(profit__isnull=True).values_list("date", "profit"):
            profit_by_date[d] = profit_by_date.get(d, Decimal("0")) + Decimal(p)

    last = {f.id: None for f in funds}
    cost_last = {f.id: Decimal(f.start_total) for f in funds}
    labels, port_value, port_profit, port_cost = [], [], [], []
    for d in all_dates:
        for f in funds:
            if d in fund_recs[f.id]:
                last[f.id] = fund_recs[f.id][d]
            if d in inv_map[f.id]:
                cost_last[f.id] += inv_map[f.id][d]
        val = sum((v for v in last.values() if v is not None), Decimal("0"))
        labels.append(d.isoformat())
        port_value.append(float(val))
        port_profit.append(float(profit_by_date.get(d, Decimal("0"))))
        port_cost.append(float(sum(cost_last.values())))

    alloc = [{"name": f.name, "value": float(last[f.id] or 0)} for f in funds if (last[f.id] or 0) > 0]
    return JsonResponse({
        "dates": labels, "value": port_value, "profit": port_profit,
        "cost": port_cost, "alloc": alloc,
    })
