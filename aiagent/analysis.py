import json
import re
from . import client, prompts


class AnalysisError(Exception):
    pass


def _summaries_block(picked: list) -> str:
    return "\n".join(f"id={p['article_id']} {p['title']}：{p.get('summary', '')}" for p in picked)


def _strip_fence(s: str) -> str:
    m = re.search(r"\{.*\}", s, re.DOTALL)
    return m.group(0) if m else s


def analyze(user, picked: list, portfolio_text: str, report_type: str) -> dict:
    tmpl = prompts.ANALYSIS_PROMPT_EVENING if report_type == "evening" else prompts.ANALYSIS_PROMPT_NOON
    msg = (tmpl
           .replace("{portfolio}", portfolio_text)
           .replace("{summaries}", _summaries_block(picked)))
    messages = [{"role": "system", "content": prompts.ANALYSIS_SYSTEM},
                {"role": "user", "content": msg}]
    caller = client.reasoner if report_type == "evening" else client.chat
    res = caller(user, messages, json_mode=True)
    if not res["ok"]:
        raise AnalysisError(f"analysis call failed: {res['error']}")
    try:
        data = json.loads(_strip_fence(res["content"]))
    except (ValueError, TypeError):
        raise AnalysisError("analysis returned non-JSON")
    data.setdefault("market_brief", {})
    data.setdefault("bias", [])
    data.setdefault("position_advice", [])
    data.setdefault("lesson", {})
    return data
