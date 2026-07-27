from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import Fund
from .forms import FundForm


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
