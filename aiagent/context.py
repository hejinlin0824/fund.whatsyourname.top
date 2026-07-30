from datetime import date
from news.models import Article
from funds.services import portfolio_snapshot


def news_titles_by_category(d: date) -> dict:
    qs = Article.objects.filter(published_at__date=d).order_by("-published_at")
    out = {}
    for a in qs:
        out.setdefault(a.category, []).append({"id": a.id, "title": a.title})
    return out


def summaries_for(ids: list) -> dict:
    out = {}
    for a in Article.objects.filter(id__in=ids):
        out[a.id] = {"title": a.title, "summary": a.summary or a.title, "category": a.category}
    return out


def portfolio_text(snapshot: dict) -> str:
    lines = ["【我的持仓】"]
    for f in snapshot["funds"]:
        st = "定投中" if f["is_active"] else "已停投"
        lines.append(
            f'- {f["name"]}({f["code"]}) [市场:{f["market"]}/类型:{f["fund_type"]}] '
            f'市值{f["mv"]} 成本{f["cost"]} 盈亏{f["profit"]} 收益率{f["roi"]}% 状态:{st}')
    lines.append(
        f'组合合计: 市值{snapshot["total_mv"]} 成本{snapshot["total_cost"]} '
        f'盈亏{snapshot["total_profit"]} 收益率{snapshot["total_roi"]}%')
    return "\n".join(lines)
