from datetime import date as date_cls
from decimal import Decimal

from django.contrib.auth.decorators import login_required
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
                # 非定投日且没填盈亏 → 不建记录
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

    # GET：预填投入（定投日填定投额，否则 0）
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
