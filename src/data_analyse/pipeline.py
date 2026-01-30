from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple

from dotenv import load_dotenv


def _ensure_project_root_on_syspath() -> None:
    """Ensure `src.*` imports work in all execution modes.

    EN: Running via `python -m` usually sets import path correctly.
    中文：使用 `python -m` 一般无需处理；直接执行脚本时需要把项目根目录加入 sys.path。
    """

    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))


_ensure_project_root_on_syspath()

from src.config import db_path, load_settings  # noqa: E402
from src.data_analyse.collect_youtube_comments import (  # noqa: E402
    _parse_video_id,
    fetch_comment_threads,
)
from src.database.sqlite import (  # noqa: E402
    connect,
    init_schema,
    insert_collection_run,
    insert_raw_thread,
    iter_clean_comments,
)

OrderInput = Literal["hot", "time"]


def collect_raw_to_db(
    *,
    url: str,
    order: OrderInput,
    max_comments: int,
    settings: Optional[Dict[str, Any]] = None,
) -> Tuple[int, str, int]:
    """Collect YouTube commentThreads and store them as raw rows.

    Returns: (run_id, video_id, raw_count)

    EN: Uses `YOUTUBE_API_KEY` from `.env`.
    中文：使用 `.env` 中的 `YOUTUBE_API_KEY`。
    """

    load_dotenv()
    settings = settings or load_settings()

    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Missing YOUTUBE_API_KEY in .env")

    base_url = os.getenv(
        "YOUTUBE_API_URL", "https://www.googleapis.com/youtube/v3/commentThreads"
    ).strip()

    retry_times = int(os.getenv("RETRY_TIMES", "3") or 3)
    retry_interval = int(os.getenv("RETRY_INTERVAL", "5") or 5)

    video_id = _parse_video_id(url)

    # EN: YouTube API uses 'relevance' for hot/popular sorting.
    # 中文：YouTube API 用 relevance 表示热门/相关度排序。
    order_mode = "relevance" if order == "hot" else "time"

    items = fetch_comment_threads(
        video_id=video_id,
        api_key=api_key,
        base_url=base_url,
        order_mode=order_mode,
        max_results_total=max(1, int(max_comments)),
        retry_times=max(0, int(retry_times)),
        retry_interval=max(0, int(retry_interval)),
    )

    conn = connect(db_path(settings))
    try:
        init_schema(conn)
        run_id = insert_collection_run(
            conn,
            video_id=video_id,
            video_url=url,
            order_mode=order_mode,
            max_comments=max(1, int(max_comments)),
        )
        for item in items:
            insert_raw_thread(conn, run_id=run_id, video_id=video_id, item=item)
        conn.commit()
    finally:
        conn.close()

    return run_id, video_id, len(items)


def clean_run_to_db(*, run_id: int, settings: Optional[Dict[str, Any]] = None) -> int:
    """Clean raw rows for a given run into `clean_comments`.

    Returns: inserted_or_ignored count.

    EN: Cleaning logic reuses the same normalization as the CLI script.
    中文：清洗逻辑与命令行脚本保持一致。
    """

    from src.data_analyse.clean_data import _extract_top_level, _normalize_text  # noqa: E402
    from src.database.sqlite import iter_raw_threads, insert_clean_comment  # noqa: E402

    load_dotenv()
    settings = settings or load_settings()

    conn = connect(db_path(settings))
    try:
        init_schema(conn)
        inserted_or_ignored = 0
        for row in iter_raw_threads(conn, run_id=run_id):
            raw_thread_id = int(row["id"])
            video_id = str(row["video_id"])
            item = json.loads(row["item_json"])

            extracted = _extract_top_level(item)
            if not extracted:
                continue

            text_original = str(extracted["text_original"] or "")
            text = _normalize_text(text_original)
            if not text:
                continue

            insert_clean_comment(
                conn,
                run_id=run_id,
                raw_thread_id=raw_thread_id,
                video_id=video_id,
                comment_id=str(extracted["comment_id"]),
                published_at=extracted.get("published_at"),
                author=extracted.get("author"),
                like_count=extracted.get("like_count"),
                reply_count=extracted.get("reply_count"),
                text=text,
                text_original=text_original,
            )
            inserted_or_ignored += 1

        conn.commit()
        return inserted_or_ignored
    finally:
        conn.close()


def fetch_clean_result(*, run_id: int, settings: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Fetch cleaned comments for a run.

    EN: Returns a JSON-serializable list.
    中文：返回可直接 JSON 序列化的列表。
    """

    load_dotenv()
    settings = settings or load_settings()

    conn = connect(db_path(settings))
    try:
        init_schema(conn)
        rows = list(iter_clean_comments(conn, run_id=run_id))
        return [
            {
                "video_id": r["video_id"],
                "comment_id": r["comment_id"],
                "published_at": r["published_at"],
                "author": r["author"],
                "like_count": r["like_count"],
                "reply_count": r["reply_count"],
                "text": r["text"],
            }
            for r in rows
        ]
    finally:
        conn.close()
