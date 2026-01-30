from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import requests


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def chat_completions(
    *,
    api_url: str,
    api_key: str,
    model: str,
    system_prompt: str,
    user_content: str,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    timeout_seconds: int = 180,
) -> Dict[str, Any]:
    """Call DeepSeek (OpenAI-compatible) chat completions API.

    EN: Returns the raw JSON response.
    中文：返回接口的原始 JSON 响应。
    """

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload: Dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
        "stream": False,
    }

    if temperature is not None:
        payload["temperature"] = temperature
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    resp = requests.post(api_url, headers=headers, json=payload, timeout=timeout_seconds)
    if resp.status_code != 200:
        raise RuntimeError(f"AI HTTP {resp.status_code}: {resp.text[:800]}")

    return resp.json()


def extract_message_content(response_json: Dict[str, Any]) -> str:
    """Extract assistant message content from OpenAI-style response."""

    choices = response_json.get("choices") or []
    if not choices:
        raise RuntimeError("AI response missing choices")

    msg = (choices[0].get("message") or {}) if isinstance(choices[0], dict) else {}
    content = msg.get("content")
    if not isinstance(content, str):
        raise RuntimeError("AI response missing message.content")
    return content


def load_ai_config_from_env() -> Dict[str, Any]:
    api_key = os.getenv("AI_API_KEY", "").strip() or os.getenv("AI-API-KEY", "").strip()
    api_url = os.getenv("AI_API_URL", "").strip()
    model = os.getenv("AI_MODEL_NAME", "").strip() or os.getenv("AI_MODEL", "").strip()

    if not api_key:
        raise ValueError("Missing AI_API_KEY in .env")
    if not api_url:
        raise ValueError("Missing AI_API_URL in .env")
    if not model:
        raise ValueError("Missing AI_MODEL_NAME in .env")

    return {
        "api_key": api_key,
        "api_url": api_url,
        "model": model,
        "temperature": _env_float("AI_TEMPERATURE", 0.2),
        "max_tokens": _env_int("AI_MAX_TOKENS", 1024),
    }
