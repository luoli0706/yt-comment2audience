from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

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

from src.config import db_path, load_settings  # noqa: E402
from src.database.sqlite import (  # noqa: E402
    connect,
    init_schema,
    insert_clean_comment,
    iter_raw_threads,
    latest_run_id,
)


_WS_RE = re.compile(r"\s+")


def _normalize_text(text: str) -> str:
    # EN: Normalize whitespace (newline/tab/multiple spaces) into single spaces.
    # 中文：将换行/制表符/多空格等统一折叠成单个空格。
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    return _WS_RE.sub(" ", text).strip()


def _extract_top_level(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    # EN: Extract top-level comment fields from a commentThread item.
    # 中文：从 commentThread 原始结构中提取顶层评论字段。
    snippet = item.get("snippet")
    if not isinstance(snippet, dict):
        return None

    top = snippet.get("topLevelComment")
    if not isinstance(top, dict):
        return None

    top_snippet = top.get("snippet")
    if not isinstance(top_snippet, dict):
        return None

    comment_id = str(top.get("id") or "").strip()
    if not comment_id:
        return None

    return {
        "comment_id": comment_id,
        "published_at": top_snippet.get("publishedAt"),
        "author": top_snippet.get("authorDisplayName"),
        "like_count": top_snippet.get("likeCount"),
        "reply_count": snippet.get("totalReplyCount"),
        "text_original": top_snippet.get("textDisplay") or "",
    }


def main(argv: Optional[list[str]] = None) -> int:
    load_dotenv()
    settings = load_settings()

    parser = argparse.ArgumentParser(
        description="Read raw_comment_threads from SQLite and normalize into clean_comments."
    )
    parser.add_argument(
        "--run-id",
        type=int,
        default=0,
        help="Process a specific collection run id (default: latest)",
    )
    args = parser.parse_args(argv)

    conn = connect(db_path(settings))
    try:
        init_schema(conn)
        run_id = int(args.run_id) if int(args.run_id) > 0 else (latest_run_id(conn) or 0)
        if run_id <= 0:
            raise SystemExit("No collection_runs found. Run collection first.")

        scanned = 0
        inserted_or_ignored = 0
        for row in iter_raw_threads(conn, run_id=run_id):
            scanned += 1
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
    finally:
        conn.close()

    print(f"Clean done. run_id={run_id} scanned={scanned} inserted_or_ignored={inserted_or_ignored}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
