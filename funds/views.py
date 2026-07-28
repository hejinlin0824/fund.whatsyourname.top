import calendar as _cal
from datetime import date as date_cls
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404

from .models import Fund, DailyRecord
from .forms import FundForm, DailyEntryFormSet
from . import services


def _today(request):
    d = request.GET.get("date")
    return date_cls.fromisoformat(d) if d else date_cls.today()


def _recompute_all(funds):
    for f in funds:
        services.recompute_fund_totals(f)


def _finalize_end_date(fund):
    """取消「仍在定投」且未填终止日 → 默认今天。"""
    if not fund.is_active and not fund.end_date:
        fund.end_date = date_cls.today()
        fund.save()


@login_required
def fund_list(request):
    funds = Fund.objects.filter(user=request.user)
    return render(request, "funds/fund_list.html", {"funds": funds})


@login_required
def fund_create(request):
    form = FundForm(request.POST or None)
    if form.is_valid():
        fund = form.save(commit=False)
        fund.user = request.user
        fund.save()
        form.save_m2m()
        _finalize_end_date(fund)
        services.backfill_fund(fund)          # 从起购日补齐到今天
        return redirect("fund-list")
    return render(request, "funds/fund_form.html", {"form": form})


@login_required
def fund_edit(request, pk):
    fund = get_object_or_404(Fund, pk=pk, user=request.user)
    form = FundForm(request.POST or None, instance=fund)
    if form.is_valid():
        form.save()
        _finalize_end_date(fund)
        services.backfill_fund(fund)          # 起购日/终止日变了就补齐
        return redirect("fund-list")
    return render(request, "funds/fund_form.html", {"form": form})


@login_required
def daily_entry(request):
    """每日批量录入页：邮件 magic link 的落点，支持任意日期（补录历史）。"""
    d = _today(request)
    funds = list(Fund.objects.filter(user=request.user, is_active=True))

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "no_trade":
            for f in funds:
                DailyRecord.objects.update_or_create(
                    fund=f, date=d,
                    defaults={"has_trade": False, "invested": Decimal("0")})
            _recompute_all(funds)
            return redirect("daily-entry")

        formset = DailyEntryFormSet(request.POST)
        if formset.is_valid():
            for frm in formset:
                fund = Fund.objects.get(pk=frm.cleaned_data["fund"], user=request.user)
                profit = frm.cleaned_data.get("profit")
                if profit is None and not fund.is_dca_day(d):
                    continue
                invested = frm.cleaned_data.get("invested")
                if invested is None:
                    invested = fund.invest_amount if fund.is_dca_day(d) else Decimal("0")
                DailyRecord.objects.update_or_create(fund=fund, date=d, defaults={
                    "profit": profit or Decimal("0"),
                    "profit_ratio": frm.cleaned_data.get("profit_ratio"),
                    "invested": invested,
                    "has_trade": True,
                })
            _recompute_all(funds)
            return redirect("daily-entry")

    initial = []
    for f in funds:
        rec = f.records.filter(date=d).first()
        invested = rec.invested if rec else (f.invest_amount if f.is_dca_day(d) else Decimal("0"))
        initial.append({
            "fund": f.id,
            "profit": rec.profit if (rec and rec.has_trade and rec.profit is not None) else "",
            "profit_ratio": rec.profit_ratio if rec else "",
            "invested": invested,
        })
    formset = DailyEntryFormSet(initial=initial)
    pairs = list(zip(formset, funds))
    return render(request, "funds/daily_entry.html",
                  {"formset": formset, "pairs": pairs, "date": d})


@login_required
def dashboard(request):
    funds = Fund.objects.filter(user=request.user)
    total_value = Decimal("0")
    total_invested = Decimal("0")
    total_profit = Decimal("0")
    fund_pairs = []
    for f in funds:
        last_known = f.records.exclude(total__isnull=True).order_by("-date").first()
        if last_known:
            mv = last_known.total
            invested_to_date = f.records.filter(date__lte=last_known.date)\
                .aggregate(s=Sum("invested"))["s"] or Decimal("0")
            cost = Decimal(f.start_total) + invested_to_date      # 成本 = 起购前已有 + 截止日累计投入
            total_value += mv
            total_invested += cost
            total_profit += (mv - cost)                           # 盈亏 = 市值 - 成本，三者一致
        fund_pairs.append((f, last_known))
    ratio = (total_profit / total_invested * 100) if total_invested else Decimal("0")
    return render(request, "funds/dashboard.html", {
        "fund_pairs": fund_pairs, "total_value": total_value,
        "total_invested": total_invested, "total_profit": total_profit, "ratio": ratio,
    })


@login_required
def calendar_view(request):
    """月历：标记每天状态（已录全/待补录/未建/未来），点格子跳到该日录入。"""
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
        if dt > today:
            status = "future"
        elif dt in by_date:
            rows = by_date[dt]
            status = "pending" if any(rr.has_trade and rr.profit is None for rr in rows) else "filled"
        else:
            status = "empty"
        days.append({"date": dt, "status": status})

    # 组成周行（前端无需取模换行）
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
    return render(request, "funds/fund_detail.html", {"fund": fund})


@login_required
def fund_detail_data(request, pk):
    """走势数据 JSON（Chart.js）。total 为 None 时送 null（图表留空）。"""
    fund = get_object_or_404(Fund, pk=pk, user=request.user)
    recs = fund.records.order_by("date")
    return JsonResponse({
        "dates": [r.date.isoformat() for r in recs],
        "totals": [None if r.total is None else float(r.total) for r in recs],
        "profits": [None if r.profit is None else float(r.profit) for r in recs],
    })
