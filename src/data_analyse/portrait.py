from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

from src.ai.deepseek_client import chat_completions, extract_message_content, load_ai_config_from_env
from src.config import db_path, default_ai_prompt_filename, load_settings
from src.database.sqlite import (
    connect,
    get_ai_portrait,
    init_schema,
    iter_clean_comments,
    upsert_ai_portrait,
)


def _load_prompt_file(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Prompt JSON must be an object")
    if "system_prompt" not in data or not isinstance(data["system_prompt"], str):
        raise ValueError("Prompt JSON must include system_prompt (string)")
    return data


def _extract_json_text(raw: str) -> str:
    s = (raw or "").strip()
    if s.startswith("```"):
        lines = s.splitlines()
        if len(lines) >= 3 and lines[-1].strip().startswith("```"):
            s = "\n".join(lines[1:-1]).strip()

    obj_start = s.find("{")
    obj_end = s.rfind("}")
    arr_start = s.find("[")
    arr_end = s.rfind("]")
    if obj_start != -1 and obj_end != -1 and obj_end > obj_start:
        return s[obj_start : obj_end + 1]
    if arr_start != -1 and arr_end != -1 and arr_end > arr_start:
        return s[arr_start : arr_end + 1]
    return s


def resolve_prompt_path(*, settings: Optional[Dict[str, Any]] = None) -> Path:
    """Resolve prompt JSON path.

    Priority:
    1) .env AI_PROMPT (explicit override)
    2) settings.json (ai.language + ai.prompt_template)
    3) legacy fallback
    """

    load_dotenv()
    settings = settings or load_settings()

    project_root = Path(__file__).resolve().parents[2]

    env_value = (os.getenv("AI_PROMPT") or "").strip().strip('"')
    if env_value:
        p = Path(env_value)
        if not p.is_absolute():
            p = project_root / p
        if p.exists():
            return p
        if p.suffix.lower() == ".txt":
            candidate = p.with_suffix(".json")
            if candidate.exists():
                return candidate

    p = project_root / "AI_PROMPT" / default_ai_prompt_filename(settings)
    if p.exists():
        return p

    return project_root / "AI_PROMPT" / "AI_PROMPT_Default.json"


def generate_portrait_for_run(
    *,
    run_id: int,
    settings: Optional[Dict[str, Any]] = None,
    overwrite: bool = False,
) -> Dict[str, Any]:
    """Generate portrait for a run_id, store into SQLite, and return result."""

    load_dotenv()
    settings = settings or load_settings()

    conn = connect(db_path(settings))
    try:
        init_schema(conn)

        existing = get_ai_portrait(conn, int(run_id))
        if existing is not None and not overwrite:
            portrait_json = existing["portrait_json"]
            portrait_raw = existing["portrait_raw"]
            parse_ok = bool(existing["parse_ok"])
            error = existing["error"]
            prompt_name = existing["prompt_name"]
            prompt_version = existing["prompt_version"]
            provider = existing["provider"]
            model = existing["model"]

            portrait_obj: Optional[Dict[str, Any]] = None
            if parse_ok and isinstance(portrait_json, str) and portrait_json:
                try:
                    portrait_obj = json.loads(portrait_json)
                except Exception:  # noqa: BLE001
                    portrait_obj = None

            return {
                "run_id": int(run_id),
                "video_id": None,
                "parse_ok": parse_ok,
                "portrait": portrait_obj,
                "portrait_raw": portrait_raw,
                "error": error,
                "prompt_name": prompt_name,
                "prompt_version": prompt_version,
                "provider": provider,
                "model": model,
                "cached": True,
            }

        rows = list(iter_clean_comments(conn, int(run_id)))
        if not rows:
            raise ValueError("No clean_comments found for this run_id")

        video_id = str(rows[0]["video_id"] or "")

        input_obj = {
            "video_id": video_id,
            "comments": [
                {
                    "comment_id": r["comment_id"],
                    "author": r["author"],
                    "published_at": r["published_at"],
                    "like_count": r["like_count"],
                    "reply_count": r["reply_count"],
                    "text": r["text"],
                }
                for r in rows
            ],
        }
        input_json = json.dumps(input_obj, ensure_ascii=False)

        prompt_path = resolve_prompt_path(settings=settings)
        prompt_obj = _load_prompt_file(prompt_path)

        ai_cfg = load_ai_config_from_env()
        provider = os.getenv("AI_PROVIDER", "deepseek").strip() or "deepseek"

        resp_json = chat_completions(
            api_url=ai_cfg["api_url"],
            api_key=ai_cfg["api_key"],
            model=ai_cfg["model"],
            system_prompt=prompt_obj["system_prompt"],
            user_content=input_json,
            temperature=float(ai_cfg["temperature"]),
            max_tokens=int(ai_cfg["max_tokens"]),
        )

        raw_content = extract_message_content(resp_json)

        portrait_json: Optional[str] = None
        portrait_obj: Optional[Dict[str, Any]] = None
        parse_ok = False
        error: Optional[str] = None

        try:
            parsed = json.loads(_extract_json_text(raw_content))
            portrait_json = json.dumps(parsed, ensure_ascii=False)
            portrait_obj = parsed if isinstance(parsed, dict) else None
            parse_ok = True
        except Exception as e:  # noqa: BLE001
            error = f"Portrait JSON parse failed: {e}"

        upsert_ai_portrait(
            conn,
            run_id=int(run_id),
            provider=provider,
            model=str(ai_cfg["model"]),
            prompt_name=str(prompt_obj.get("name") or "AI_PROMPT"),
            prompt_version=int(prompt_obj.get("version") or 1),
            input_json=input_json,
            portrait_json=portrait_json,
            portrait_raw=raw_content,
            parse_ok=parse_ok,
            error=error,
        )
        conn.commit()

        return {
            "run_id": int(run_id),
            "video_id": video_id,
            "parse_ok": parse_ok,
            "portrait": portrait_obj,
            "portrait_raw": raw_content,
            "error": error,
            "prompt_name": str(prompt_obj.get("name") or "AI_PROMPT"),
            "prompt_version": int(prompt_obj.get("version") or 1),
            "provider": provider,
            "model": str(ai_cfg["model"]),
            "cached": False,
        }
    finally:
        conn.close()
