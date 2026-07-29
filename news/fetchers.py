"""按 Source.kind 分发抓取。每个抓取器返回标准化的 dict 列表，交由命令去重入库。"""
import logging
from .cleaners import parse_time, ensure_summary

logger = logging.getLogger(__name__)


def _item(title, url, summary, published, category, source_name, content=""):
    return {
        "title": (title or "").strip(),
        "url": (url or "").strip(),
        "summary": ensure_summary(title, summary, content),
        "content": content or "",
        "published_at": published,
        "category": category,
        "source": source_name,
    }


def fetch_rss(source):
    import feedparser
    import requests
    items = []
    try:
        resp = requests.get(source.url, timeout=15,
                            headers={"User-Agent": "Mozilla/5.0 (Whatsyour Fund Dashboard)"})
        resp.raise_for_status()
        feed = feedparser.parse(resp.content)
    except Exception as e:
        logger.warning("RSS 抓取失败 %s: %s", source.name, e)
        return []
    for e in feed.entries:
        url = getattr(e, "link", "") or ""
        if not url:
            continue
        raw_time = getattr(e, "published", "") or getattr(e, "updated", "")
        content = ""
        if getattr(e, "content", None):
            content = e.content[0].get("value", "") if isinstance(e.content, list) else str(e.content)
        items.append(_item(getattr(e, "title", ""), url,
                           getattr(e, "summary", "") or getattr(e, "description", ""),
                           parse_time(raw_time), source.category, source.name, content))
    return items


_HN_BASE = "https://hacker-news.firebaseio.com/v0"


def fetch_hn(source):
    import requests
    items = []
    try:
        ids = requests.get(f"{_HN_BASE}/topstories.json", timeout=15).json()[:30]
        for i in ids:
            d = requests.get(f"{_HN_BASE}/item/{i}.json", timeout=15).json()
            if not d or d.get("type") != "story":
                continue
            url = d.get("url") or f"https://news.ycombinator.com/item?id={i}"
            items.append(_item(d.get("title", ""), url, "",
                               parse_time(str(d.get("time", ""))), source.category, source.name))
    except Exception as e:
        logger.warning("HackerNews 抓取失败: %s", e)
    return items


def fetch_akshare(source):
    """AkShare 财经新闻。包未装或接口变动时静默跳过，不影响其它源。"""
    try:
        import akshare as ak
    except Exception:
        logger.warning("akshare 未安装，跳过 %s", source.name)
        return []
    items = []
    try:
        # AkShare 财经新闻（接口可能变动，按 source.url 指定 symbol，默认 000001）
        symbol = (source.url or "").strip() or "000001"
        df = ak.stock_news_em(symbol=symbol)
        for _, r in df.head(30).iterrows():
            pub = parse_time(str(r.get("发布时间", r.get("date", ""))))
            items.append(_item(str(r.get("新闻标题", "")), str(r.get("新闻链接", "")),
                               str(r.get("新闻内容", "")), pub, source.category, source.name))
    except Exception as e:
        logger.warning("AkShare 抓取失败 (%s): %s", source.name, e)
    return items


DISPATCH = {"RSS": fetch_rss, "HN": fetch_hn, "AKSHARE": fetch_akshare}


def fetch_source(source):
    fn = DISPATCH.get(source.kind)
    if not fn:
        logger.warning("未知 kind %s (source=%s)", source.kind, source.name)
        return []
    return fn(source)
