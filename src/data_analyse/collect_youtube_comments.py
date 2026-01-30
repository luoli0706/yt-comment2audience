from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import requests
from dotenv import load_dotenv


def _ensure_project_root_on_syspath() -> None:
    """Ensure imports like `from src...` work when run as a script.

    EN: When using `python -m ...`, this is unnecessary.
    中文：若用 `python -m ...` 运行则不需要；直接运行脚本时需要把项目根目录加入 sys.path。
    """

    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


_ensure_project_root_on_syspath()

from src.config import db_path, load_settings, youtube_max_comments, youtube_order  # noqa: E402
from src.database.sqlite import (  # noqa: E402
    connect,
    init_schema,
    insert_collection_run,
    insert_raw_thread,
)


def _parse_video_id(url: str) -> str:
    parsed = urlparse(url.strip())
    host = (parsed.netloc or "").lower()

    # EN: Supported URL examples
    # 中文：支持的 URL 示例
    # - https://www.youtube.com/watch?v=MdTAJ1J2LeM
    # - https://youtu.be/MdTAJ1J2LeM
    # - https://www.youtube.com/shorts/MdTAJ1J2LeM
    if "youtu.be" in host:
        candidate = parsed.path.lstrip("/").split("/")[0]
        if candidate:
            return candidate

    if "youtube.com" in host or "m.youtube.com" in host:
        if parsed.path.rstrip("/") == "/watch":
            q = parse_qs(parsed.query)
            vid = (q.get("v") or [""])[0]
            if vid:
                return vid

        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) >= 2 and parts[0] in {"shorts", "embed"} and parts[1]:
            return parts[1]

    raise ValueError(f"Unsupported/invalid YouTube URL: {url}")


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _request_with_retries(
    url: str,
    params: Dict[str, Any],
    retry_times: int,
    retry_interval: int,
    timeout_seconds: int = 30,
) -> Dict[str, Any]:
    last_err: Optional[Exception] = None
    for attempt in range(retry_times + 1):
        try:
            resp = requests.get(url, params=params, timeout=timeout_seconds)
            if resp.status_code == 200:
                return resp.json()

            # EN: Retry on transient HTTP errors
            # 中文：遇到临时性错误时重试
            if resp.status_code in {429, 500, 502, 503, 504}:
                time.sleep(retry_interval)
                continue

            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:500]}")
        except Exception as e:  # noqa: BLE001
            last_err = e
            if attempt < retry_times:
                time.sleep(retry_interval)
            else:
                break

    raise RuntimeError(f"Request failed after retries: {last_err}")


def fetch_comment_threads(
    *,
    video_id: str,
    api_key: str,
    base_url: str,
    order_mode: str,
    max_results_total: int,
    retry_times: int,
    retry_interval: int,
) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    page_token: Optional[str] = None

    while len(items) < max_results_total:
        per_page = min(100, max_results_total - len(items))
        params: Dict[str, Any] = {
            "part": "snippet",
            "videoId": video_id,
            "maxResults": per_page,
            "textFormat": "plainText",
            "key": api_key,
            "order": order_mode,
        }
        if page_token:
            params["pageToken"] = page_token

        data = _request_with_retries(
            base_url,
            params=params,
            retry_times=retry_times,
            retry_interval=retry_interval,
        )

        batch = data.get("items") or []
        if not isinstance(batch, list):
            raise RuntimeError("Unexpected API response: items is not a list")
        items.extend(batch)

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return items


def main(argv: Optional[List[str]] = None) -> int:
    load_dotenv()
    settings = load_settings()

    parser = argparse.ArgumentParser(
        description=(
            "Collect YouTube commentThreads using YOUTUBE_API_KEY from .env; "
            "store raw data into SQLite. (Silent by default)"
        )
    )
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument(
        "--order",
        choices=["hot", "time"],
        default="hot",
        help="Sort order: hot=relevance (default), time=latest",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=youtube_max_comments(settings) if settings else 50,
        help="Total commentThreads to fetch (default from settings.json youtube.max_comments)",
    )
    parser.add_argument(
        "--no-db",
        action="store_true",
        help="Do not store results into SQLite",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Write raw JSON payload to a file",
    )
    parser.add_argument(
        "--print",
        action="store_true",
        help="Print raw JSON payload to stdout (otherwise silent)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only validate/parse URL and print video_id without calling API",
    )

    args = parser.parse_args(argv)

    try:
        video_id = _parse_video_id(args.url)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2

    if args.dry_run:
        print(video_id)
        return 0

    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        print("Missing YOUTUBE_API_KEY in .env", file=sys.stderr)
        return 2

    base_url = os.getenv(
        "YOUTUBE_API_URL", "https://www.googleapis.com/youtube/v3/commentThreads"
    ).strip()

    retry_times = _env_int("RETRY_TIMES", 3)
    retry_interval = _env_int("RETRY_INTERVAL", 5)

    # EN: Map settings.json style to YouTube API 'order' values.
    # 中文：将 settings.json 里的排序偏好映射到 YouTube API 的 order 参数。
    order_mode = "relevance" if args.order == "hot" else "time"

    items = fetch_comment_threads(
        video_id=video_id,
        api_key=api_key,
        base_url=base_url,
        order_mode=order_mode,
        max_results_total=max(1, int(args.max_results)),
        retry_times=max(0, retry_times),
        retry_interval=max(0, retry_interval),
    )

    payload = {"video_id": video_id, "count": len(items), "items": items}

    if not args.no_db:
        conn = connect(db_path(settings))
        try:
            init_schema(conn)
            run_id = insert_collection_run(
                conn,
                video_id=video_id,
                video_url=args.url,
                order_mode=order_mode,
                max_comments=max(1, int(args.max_results)),
            )
            for item in items:
                insert_raw_thread(conn, run_id=run_id, video_id=video_id, item=item)
            conn.commit()
        finally:
            conn.close()

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    if args.print:
        json.dump(payload, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
