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


def analyze(user, picked, portfolio_text, operations_text, mode="noon") -> dict:
    """第②阶段：摘要+仓位+今日操作 → 结构化 JSON。mode 决定提示词与模型(noon=chat / evening=reasoner)。"""
    tmpl = prompts.ANALYSIS_PROMPT_EVENING if mode == "evening" else prompts.ANALYSIS_PROMPT_NOON
    msg = (tmpl
           .replace("{portfolio}", portfolio_text)
           .replace("{operations}", operations_text or "（今日无操作）")
           .replace("{summaries}", _summaries_block(picked)))
    messages = [{"role": "system", "content": prompts.ANALYSIS_SYSTEM},
                {"role": "user", "content": msg}]
    caller = client.reasoner if mode == "evening" else client.chat
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
