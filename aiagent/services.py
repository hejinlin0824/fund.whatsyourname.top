import logging
from datetime import date
from django.utils import timezone
from funds.services import portfolio_snapshot
from . import context, screening, analysis, reports
from .models import AnalysisReport

logger = logging.getLogger(__name__)


class NoApiKey(Exception):
    pass


def _today():
    return timezone.localdate() if timezone.is_aware(timezone.now()) else date.today()


def _degraded_html(reason: str, titles_by_cat: dict) -> str:
    parts = [f'<p class="warn">⚠️ AI 分析暂不可用（{reason}），以下为当日新闻标题清单：</p><ul>']
    for cat, items in titles_by_cat.items():
        for it in items:
            parts.append(f"<li>{cat}: {it['title']}</li>")
    parts.append("</ul>")
    return "".join(parts)


def generate_report(user, report_type: str) -> AnalysisReport:
    if not user.deepseek_key:
        raise NoApiKey(f"{user.username} has no deepseek key")
    now = timezone.localtime(timezone.now())
    today = now.date()
    if report_type == "evening":
        mode = "evening"
    elif report_type == "ondemand":
        mode = "evening" if now.hour >= 15 else "noon"
    else:
        mode = "noon"
    snap = portfolio_snapshot(user)
    ptext = context.portfolio_text(snap)
    titles_by_cat = context.news_titles_by_category(today)

    meta = {"models": [], "tokens_in": 0, "tokens_out": 0, "duration_s": 0}
    status, analysis_dict, screening_result = "ok", {}, []

    if not any(titles_by_cat.values()):
        html = "<p>今日暂无足够新闻可分析。仅提供仓位小结。</p>" + ptext.replace("\n", "<br>")
    else:
        try:
            screening_result = screening.screen(user, titles_by_cat, ptext)
            ids = [p["article_id"] for p in screening_result]
            summaries = context.summaries_for(ids)
            picked = [{"article_id": i,
                       "title": summaries[i]["title"],
                       "summary": summaries[i]["summary"],
                       "category": summaries[i]["category"]}
                      for i in ids if i in summaries]
            operations_text = context.recent_operations_text(user, today)
            analysis_dict = analysis.analyze(user, picked, ptext, operations_text, mode)
            html = reports.render(analysis_dict, report_type)
        except (screening.ScreeningError, analysis.AnalysisError) as e:
            logger.warning("AI degrade for %s: %s", user.username, e)
            status = "degraded"
            html = _degraded_html(str(e), titles_by_cat)

    # upsert：定时型每日每类一条
    rep = None
    if report_type in ("morning", "evening"):
        rep = AnalysisReport.objects.filter(user=user, type=report_type, date=today).first()
    if rep:
        rep.content_html = html
        rep.screening = screening_result
        rep.analysis = analysis_dict
        rep.meta = meta
        rep.status = status
        rep.save()
    else:
        rep = AnalysisReport.objects.create(
            user=user, type=report_type, date=today, content_html=html,
            screening=screening_result, analysis=analysis_dict, meta=meta, status=status)
    return rep
