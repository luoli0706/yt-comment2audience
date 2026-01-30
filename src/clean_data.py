from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import db_path, load_settings  # noqa: E402
from src.db_sqlite import connect, init_schema, insert_clean_comment, iter_raw_threads, latest_run_id  # noqa: E402


_WS_RE = re.compile(r"\s+")


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    # Collapse all whitespace (including newlines/tabs) into a single space
    return _WS_RE.sub(" ", text).strip()


def _extract_top_level(item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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


def main() -> int:
    load_dotenv()
    settings = load_settings()
    path = db_path(settings)

    conn = connect(path)
    try:
        init_schema(conn)
        run_id = latest_run_id(conn)
        if run_id is None:
            raise SystemExit("No collection_runs found. Run collection first.")

        inserted = 0
        seen = 0
        for row in iter_raw_threads(conn, run_id=run_id):
            seen += 1
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
            inserted += 1

        conn.commit()
    finally:
        conn.close()

    print(f"Cleaned comments stored. scanned={seen} inserted_or_ignored={inserted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
