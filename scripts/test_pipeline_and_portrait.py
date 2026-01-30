from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import requests
from dotenv import load_dotenv


def _ensure_project_root_on_syspath() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


_ensure_project_root_on_syspath()

from src.ai.deepseek_client import (  # noqa: E402
    chat_completions,
    extract_message_content,
    load_ai_config_from_env,
)
from src.config import ai_language, load_settings  # noqa: E402


def _resolve_base_url() -> str:
    host = os.getenv("HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = os.getenv("PORT", "5076").strip() or "5076"
    return os.getenv("BASE_URL", f"http://{host}:{port}").rstrip("/")


def _load_prompt_json(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Prompt JSON must be an object")
    if not isinstance(data.get("system_prompt"), str) or not data["system_prompt"].strip():
        raise ValueError("Prompt JSON must contain non-empty system_prompt")
    return data


def _extract_json_text(raw: str) -> str:
    """Best-effort JSON extractor.

    EN: Some models return JSON wrapped in markdown code fences.
    中文：部分模型会把 JSON 包在 markdown 代码块里，这里做一次兼容抽取。
    """

    s = (raw or "").strip()
    if s.startswith("```"):
        lines = s.splitlines()
        if len(lines) >= 3 and lines[-1].strip().startswith("```"):
            s = "\n".join(lines[1:-1]).strip()
    # Try to slice the first JSON object/array.
    obj_start = s.find("{")
    obj_end = s.rfind("}")
    arr_start = s.find("[")
    arr_end = s.rfind("]")
    if obj_start != -1 and obj_end != -1 and obj_end > obj_start:
        return s[obj_start : obj_end + 1]
    if arr_start != -1 and arr_end != -1 and arr_end > arr_start:
        return s[arr_start : arr_end + 1]
    return s


def _resolve_prompt_path(cli_value: str | None) -> Path:
    project_root = Path(__file__).resolve().parents[1]

    # 1) CLI override
    if cli_value:
        raw = str(cli_value).strip().strip('"')
        p = Path(raw)
        if not p.is_absolute():
            p = project_root / p
        return p

    # 2) Env override
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

    # 3) Default based on settings.json ai.language (default zh)
    settings = load_settings()
    lang = ai_language(settings)
    default_path = project_root / "AI_PROMPT" / f"AI_PROMPT_Default.{lang}.json"
    if default_path.exists():
        return default_path

    # 4) Final fallback for legacy setups
    return project_root / "AI_PROMPT" / "AI_PROMPT_Default.json"


def _pipeline_call(*, base_url: str, url: str, order: str, max_comments: int) -> Dict[str, Any]:
    endpoint = f"{base_url}/api/pipeline"
    payload = {"url": url, "order": order, "max_comments": int(max_comments)}

    resp = requests.post(endpoint, json=payload, timeout=180)
    try:
        data = resp.json()
    except Exception:  # noqa: BLE001
        raise RuntimeError(f"HTTP {resp.status_code} (non-JSON): {resp.text[:500]}")

    if not resp.ok or data.get("ok") is not True:
        raise RuntimeError(f"Pipeline failed: HTTP {resp.status_code} body={data}")

    return data


def _to_portrait_input(pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
    video_id = str(pipeline_data.get("video_id") or "")
    result = pipeline_data.get("result") or []
    if not isinstance(result, list) or not result:
        raise ValueError("Pipeline result is empty")

    comments: List[Dict[str, Any]] = []
    for r in result:
        if not isinstance(r, dict):
            continue
        comments.append(
            {
                "comment_id": r.get("comment_id"),
                "author": r.get("author"),
                "published_at": r.get("published_at"),
                "like_count": r.get("like_count"),
                "reply_count": r.get("reply_count"),
                "text": r.get("text"),
            }
        )

    if not video_id:
        # Fallback to the first row's video_id if server omitted top-level video_id.
        video_id = str((result[0] if isinstance(result[0], dict) else {}).get("video_id") or "")

    return {"video_id": video_id, "comments": comments}


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description=(
            "Test script: call /api/pipeline (collect+clean), then call DeepSeek portrait "
            "using the configured prompt JSON, and print the portrait result."
        )
    )
    parser.add_argument(
        "--url",
        default="https://www.youtube.com/watch?v=MdTAJ1J2LeM",
        help=(
            "YouTube URL to analyse (default uses a valid 11-char video id). "
            "Note: some examples online include typos like an extra trailing character."
        ),
    )
    parser.add_argument("--order", choices=["hot", "time"], default="hot")
    parser.add_argument("--max-comments", type=int, default=20)
    parser.add_argument(
        "--prompt",
        default=None,
        help="Prompt JSON path (default: env AI_PROMPT or AI_PROMPT/AI_PROMPT_Default.json)",
    )
    parser.add_argument(
        "--print-pipeline",
        action="store_true",
        help="Also print pipeline response JSON",
    )

    args = parser.parse_args()

    base_url = _resolve_base_url()
    pipeline_data = _pipeline_call(
        base_url=base_url,
        url=str(args.url),
        order=str(args.order),
        max_comments=int(args.max_comments),
    )

    if args.print_pipeline:
        print("# Pipeline response")
        print(json.dumps(pipeline_data, ensure_ascii=False, indent=2))

    prompt_path = _resolve_prompt_path(args.prompt)
    prompt_obj = _load_prompt_json(prompt_path)

    portrait_input = _to_portrait_input(pipeline_data)
    user_content = json.dumps(portrait_input, ensure_ascii=False)

    ai_cfg = load_ai_config_from_env()
    resp_json = chat_completions(
        api_url=ai_cfg["api_url"],
        api_key=ai_cfg["api_key"],
        model=ai_cfg["model"],
        system_prompt=prompt_obj["system_prompt"],
        user_content=user_content,
        temperature=float(ai_cfg["temperature"]),
        max_tokens=int(ai_cfg["max_tokens"]),
    )

    raw = extract_message_content(resp_json)

    print("# Portrait result")
    try:
        parsed = json.loads(_extract_json_text(raw))
        print(json.dumps(parsed, ensure_ascii=False, indent=2))
        return 0
    except Exception:  # noqa: BLE001
        # If the model ever violates the "strict JSON" constraint, still show output.
        print(raw)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
