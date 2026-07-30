from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import AnalysisReport
from .forms import DeepSeekKeyForm
from . import services
from funds.services import portfolio_snapshot

ON_DEMAND_DAILY_LIMIT = 5


@login_required
def report_list(request):
    reps = AnalysisReport.objects.filter(user=request.user)
    today = timezone.localdate()
    used = AnalysisReport.objects.filter(user=request.user, type="ondemand", date=today).count()
    remaining = max(0, ON_DEMAND_DAILY_LIMIT - used)
    return render(request, "aiagent/report_list.html",
                  {"reports": reps, "limit": ON_DEMAND_DAILY_LIMIT, "remaining": remaining})


@login_required
@require_POST
def report_delete(request, pk):
    rep = get_object_or_404(AnalysisReport, pk=pk, user=request.user)
    rep.delete()
    return redirect("aiagent:report-list")


@login_required
def report_detail(request, pk):
    rep = get_object_or_404(AnalysisReport, pk=pk, user=request.user)
    snap = portfolio_snapshot(request.user)
    snap_d = {k: float(snap[k]) for k in ("total_mv", "total_cost", "total_profit", "total_roi")}
    return render(request, "aiagent/report_detail.html", {"report": rep, "snap": snap_d})


@login_required
@require_POST
def on_demand(request):
    today = timezone.localdate()
    used = AnalysisReport.objects.filter(
        user=request.user, type="ondemand", date=today).count()
    if used >= ON_DEMAND_DAILY_LIMIT:
        return HttpResponse("今日手动分析已达上限（%d 次）" % ON_DEMAND_DAILY_LIMIT, status=429)
    try:
        services.generate_report(request.user, "ondemand")
    except services.NoApiKey:
        return redirect("aiagent:key-settings")
    return redirect("aiagent:report-list")


@login_required
def key_settings(request):
    if request.method == "POST":
        form = DeepSeekKeyForm(request.POST)
        if form.is_valid():
            request.user.set_deepseek_key(form.cleaned_data["deepseek_key"] or "")
            request.user.save()
            return redirect("aiagent:key-settings")
    else:
        form = DeepSeekKeyForm()
    return render(request, "aiagent/key_settings.html",
                  {"form": form, "has_key": bool(request.user.deepseek_key)})
