from datetime import date as date_cls
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404

from .models import Fund, DailyRecord
from .forms import FundForm, DailyEntryFormSet
from . import services


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
        return redirect("fund-list")
    return render(request, "funds/fund_form.html", {"form": form})


@login_required
def fund_edit(request, pk):
    fund = get_object_or_404(Fund, pk=pk, user=request.user)
    form = FundForm(request.POST or None, instance=fund)
    if form.is_valid():
        form.save()
        return redirect("fund-list")
    return render(request, "funds/fund_form.html", {"form": form})


def _today(request):
    d = request.GET.get("date")
    return date_cls.fromisoformat(d) if d else date_cls.today()


def _recompute_all(funds):
    for f in funds:
        services.recompute_fund_totals(f)


@login_required
def daily_entry(request):
    """每日批量录入页：邮件 magic link 的落点。"""
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
            "profit": rec.profit if rec and rec.has_trade else "",
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
    for f in funds:
        last = f.records.order_by("-date").first()
        if last:
            total_value += last.total
        total_invested += f.records.aggregate(s=Sum("invested"))["s"] or Decimal("0")
        total_profit += f.records.filter(has_trade=True).aggregate(s=Sum("profit"))["s"] or Decimal("0")
    ratio = (total_profit / total_invested * 100) if total_invested else Decimal("0")
    return render(request, "funds/dashboard.html", {
        "funds": funds, "total_value": total_value,
        "total_invested": total_invested, "total_profit": total_profit, "ratio": ratio,
    })


@login_required
def fund_detail(request, pk):
    fund = get_object_or_404(Fund, pk=pk, user=request.user)
    return render(request, "funds/fund_detail.html", {"fund": fund})


@login_required
def fund_detail_data(request, pk):
    """走势数据 JSON 端点（供 Chart.js fetch）。"""
    fund = get_object_or_404(Fund, pk=pk, user=request.user)
    recs = fund.records.order_by("date")
    return JsonResponse({
        "dates": [r.date.isoformat() for r in recs],
        "totals": [str(r.total) for r in recs],
        "profits": [str(r.profit or 0) for r in recs],
    })
