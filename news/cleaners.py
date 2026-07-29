"""统一数据清洗工具：时间标准化（→ Asia/Shanghai）、摘要兜底、去 HTML。"""
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

SHANGHAI = ZoneInfo("Asia/Shanghai")
_FALLBACK_FMTS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
                  "%Y/%m/%d %H:%M:%S", "%Y/%m/%d", "%Y年%m月%d日 %H:%M")


def parse_time(raw):
    """兼容 RSS 各类时间串，统一转 Asia/Shanghai tz-aware datetime；失败返回 None。"""
    if not raw:
        return None
    raw = str(raw).strip()
    # 1) RFC822（RSS 标准）：Wed, 02 Jul 2025 10:30:00 +0800
    try:
        dt = parsedate_to_datetime(raw)
        if dt is not None:
            return dt.astimezone(SHANGHAI)
    except Exception:
        pass
    # 2) ISO 8601：2025-07-02T10:30:00+08:00 / ...Z
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=SHANGHAI)
        return dt.astimezone(SHANGHAI)
    except Exception:
        pass
    # 3) 常见无时区格式（按东八区）
    for fmt in _FALLBACK_FMTS:
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=SHANGHAI)
        except Exception:
            continue
    # 4) epoch 秒（HackerNews）
    try:
        return datetime.fromtimestamp(int(float(raw)), tz=SHANGHAI)
    except Exception:
        return None


_TAG_RE = re.compile(r"<[^>]+>")


def strip_html(text):
    return _TAG_RE.sub("", text or "").strip()


def ensure_summary(title, summary, content=""):
    """优先 summary，其次截取 content，最后用 title 兜底；保证非空。"""
    s = strip_html(summary)
    if not s:
        s = strip_html(content)[:200]
    if not s:
        s = (title or "").strip()
    return s[:500]
