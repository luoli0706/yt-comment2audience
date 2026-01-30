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
