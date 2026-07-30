import os
import time
import logging
import requests

logger = logging.getLogger(__name__)

BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
TIMEOUT = int(os.environ.get("DEEPSEEK_TIMEOUT", "60"))
CHAT_MODEL = "deepseek-chat"
REASONER_MODEL = "deepseek-reasoner"


def call(user, messages, model=CHAT_MODEL, json_mode=False, timeout=None) -> dict:
    key = user.deepseek_key
    if not key:
        return {"ok": False, "content": None, "usage": None, "error": "no_api_key", "status": None}
    payload = {"model": model, "messages": messages, "temperature": 0.3}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    last_err = None
    for attempt in range(3):  # 初次 + 2 次重试
        try:
            resp = requests.post(f"{BASE_URL}/chat/completions", headers=headers,
                                 json=payload, timeout=timeout or TIMEOUT)
        except requests.RequestException as e:
            last_err = f"network:{e}"
            time.sleep(0.3 * (2 ** attempt))
            continue
        if resp.status_code == 401:
            return {"ok": False, "content": None, "usage": None, "error": "invalid_api_key", "status": 401}
        if resp.status_code == 429 or 500 <= resp.status_code < 600:
            last_err = f"http{resp.status_code}"
            time.sleep(0.3 * (2 ** attempt))
            continue
        if resp.status_code != 200:
            return {"ok": False, "content": None, "usage": None,
                    "error": f"http{resp.status_code}", "status": resp.status_code}
        data = resp.json()
        return {"ok": True,
                "content": data["choices"][0]["message"]["content"],
                "usage": data.get("usage"), "error": None, "status": 200}
    return {"ok": False, "content": None, "usage": None, "error": last_err or "unknown", "status": None}


def chat(user, messages, json_mode=False, timeout=None):
    return call(user, messages, CHAT_MODEL, json_mode, timeout)


def reasoner(user, messages, json_mode=False, timeout=None):
    return call(user, messages, REASONER_MODEL, json_mode, timeout)
