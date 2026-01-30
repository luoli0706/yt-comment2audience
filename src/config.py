from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def settings_path() -> Path:
    return project_root() / "settings.json"


def load_settings() -> Dict[str, Any]:
    path = settings_path()
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def youtube_order(settings: Dict[str, Any]) -> str:
    raw = (
        settings.get("youtube", {}).get("order")
        or settings.get("youtube", {}).get("sort")
        or "hot"
    )
    raw = str(raw).strip().lower()
    if raw in {"hot", "popular", "relevance", "relevant"}:
        return "relevance"
    if raw in {"time", "latest", "new"}:
        return "time"
    raise ValueError(f"Unknown youtube.order in settings.json: {raw}")


def youtube_max_comments(settings: Dict[str, Any]) -> int:
    raw = settings.get("youtube", {}).get("max_comments", 50)
    try:
        value = int(raw)
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"Invalid youtube.max_comments in settings.json: {raw}") from e

    return max(1, value)


def db_path(settings: Dict[str, Any]) -> Path:
    raw = settings.get("database", {}).get("path", "data/image_analyse.sqlite3")
    path = Path(raw)
    if not path.is_absolute():
        path = project_root() / path
    return path


def ai_language(settings: Dict[str, Any]) -> str:
    """Preferred AI prompt language.

    EN: Used to select the default system prompt when AI_PROMPT is not explicitly set.
    中文：当未显式设置 AI_PROMPT 时，用于选择默认 system prompt。

    Supported: zh | en
    """

    raw = settings.get("ai", {}).get("language", "zh")
    raw = str(raw).strip().lower()

    if raw in {"zh", "zh-cn", "zh-hans", "chinese", "cn"}:
        return "zh"
    if raw in {"en", "en-us", "english"}:
        return "en"

    raise ValueError(f"Unknown ai.language in settings.json: {raw}")


def ai_prompt_template(settings: Dict[str, Any]) -> str:
    """AI prompt template name.

    Supported: default | optimized
    """

    raw = settings.get("ai", {}).get("prompt_template", "default")
    raw = str(raw).strip().lower()
    if raw in {"default", "std", "standard"}:
        return "default"
    if raw in {"optimized", "opt", "pro"}:
        return "optimized"
    raise ValueError(f"Unknown ai.prompt_template in settings.json: {raw}")


def default_ai_prompt_filename(settings: Dict[str, Any]) -> str:
    """Resolve default prompt file name based on settings.

    EN: This is used when AI_PROMPT is not explicitly set.
    中文：当未显式设置 AI_PROMPT 时，用该规则选择默认提示词文件。
    """

    lang = ai_language(settings)
    template = ai_prompt_template(settings)

    if template == "optimized":
        return f"AI_PROMPT_Optimized.{lang}.json"
    return f"AI_PROMPT_Default.{lang}.json"
