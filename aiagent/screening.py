import json
from . import client, prompts


class ScreeningError(Exception):
    pass


def _titles_block(titles_by_cat: dict) -> str:
    lines = []
    for cat, items in titles_by_cat.items():
        for it in items:
            lines.append(f"{cat}: id={it['id']} {it['title']}")
    return "\n".join(lines)


def screen(user, titles_by_cat: dict, portfolio_text: str) -> list:
    if not any(titles_by_cat.values()):
        return []
    msg = (prompts.SCREENING_PROMPT
           .replace("{portfolio}", portfolio_text)
           .replace("{titles}", _titles_block(titles_by_cat)))
    res = client.chat(user, [{"role": "user", "content": msg}], json_mode=True)
    if not res["ok"]:
        raise ScreeningError(f"screening call failed: {res['error']}")
    try:
        data = json.loads(res["content"])
        picks = data.get("picks", [])
    except (ValueError, TypeError, AttributeError):
        raise ScreeningError("screening returned non-JSON")
    out = []
    for p in picks:
        if "id" in p:
            out.append({"article_id": int(p["id"]),
                        "reason": str(p.get("reason", "")),
                        "category": str(p.get("category", ""))})
    return out
