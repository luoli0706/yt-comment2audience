from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv


def _ensure_project_root_on_syspath() -> None:
    """Ensure `src.*` imports work in all execution modes.

    EN: `python -m` usually sets import path correctly.
    中文：使用 `python -m` 一般无需处理；直接执行脚本时需要把项目根目录加入 sys.path。
    """

    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


_ensure_project_root_on_syspath()

from src.config import default_ai_prompt_filename, db_path, load_settings  # noqa: E402
from src.database.sqlite import (  # noqa: E402
    connect,
    get_ai_portrait,
    init_schema,
    iter_clean_comments,
    latest_run_id,
    upsert_ai_portrait,
)
from src.ai.deepseek_client import (  # noqa: E402
    chat_completions,
    extract_message_content,
    load_ai_config_from_env,
)


def _load_prompt_file(path: Path) -> Dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("Prompt JSON must be an object")
    if "system_prompt" not in data or not isinstance(data["system_prompt"], str):
        raise ValueError("Prompt JSON must include system_prompt (string)")
    return data


def _resolve_prompt_path() -> Path:
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

    settings = load_settings()
    p = project_root / "AI_PROMPT" / default_ai_prompt_filename(settings)
    if p.exists():
        return p

    return project_root / "AI_PROMPT" / "AI_PROMPT_Default.json"


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


def main() -> int:
    load_dotenv()
    settings = load_settings()

    parser = argparse.ArgumentParser(
        description="Generate AI portrait from cleaned comments and store into SQLite."
    )
    parser.add_argument(
        "--run-id",
        type=int,
        default=0,
        help="Use a specific collection run id (default: latest)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing portrait for this run_id",
    )
    args = parser.parse_args()

    conn = connect(db_path(settings))
    try:
        init_schema(conn)
        run_id = int(args.run_id) if int(args.run_id) > 0 else (latest_run_id(conn) or 0)
        if run_id <= 0:
            raise SystemExit("No collection_runs found. Run collection first.")

        existing = get_ai_portrait(conn, run_id)
        if existing is not None and not args.overwrite:
            print(
                f"Portrait already exists for run_id={run_id}. Use --overwrite to regenerate."
            )
            return 0

        comments = [
            {
                "video_id": r["video_id"],
                "comment_id": r["comment_id"],
                "published_at": r["published_at"],
                "author": r["author"],
                "like_count": r["like_count"],
                "reply_count": r["reply_count"],
                "text": r["text"],
            }
            for r in iter_clean_comments(conn, run_id)
        ]
        if not comments:
            raise SystemExit(
                "No clean_comments found for this run. Run cleaning first (src.data_analyse.clean_data)."
            )

        video_id = str(comments[0].get("video_id") or "")
        prompt_path = _resolve_prompt_path()
        prompt_obj = _load_prompt_file(prompt_path)

        input_obj = {
            "video_id": video_id,
            "comments": [
                {
                    "comment_id": c["comment_id"],
                    "author": c.get("author"),
                    "published_at": c.get("published_at"),
                    "like_count": c.get("like_count"),
                    "reply_count": c.get("reply_count"),
                    "text": c["text"],
                }
                for c in comments
            ],
        }
        input_json = json.dumps(input_obj, ensure_ascii=False)

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
        parse_ok = False
        error: Optional[str] = None

        try:
            parsed = json.loads(_extract_json_text(raw_content))
            portrait_json = json.dumps(parsed, ensure_ascii=False)
            parse_ok = True
        except Exception as e:  # noqa: BLE001
            error = f"Portrait JSON parse failed: {e}"

        upsert_ai_portrait(
            conn,
            run_id=run_id,
            provider=provider,
            model=str(ai_cfg["model"]),
            prompt_name=str(prompt_obj.get("name") or "AI_PROMPT_Default"),
            prompt_version=int(prompt_obj.get("version") or 1),
            input_json=input_json,
            portrait_json=portrait_json,
            portrait_raw=raw_content,
            parse_ok=parse_ok,
            error=error,
        )
        conn.commit()
    finally:
        conn.close()

    print(f"Portrait stored. run_id={run_id} parse_ok={parse_ok}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
