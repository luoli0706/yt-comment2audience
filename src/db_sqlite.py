from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def connect(db_file: Path) -> sqlite3.Connection:
    db_file.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS collection_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            video_id TEXT NOT NULL,
            video_url TEXT NOT NULL,
            collected_at TEXT NOT NULL,
            order_mode TEXT NOT NULL,
            max_comments INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS raw_comment_threads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            video_id TEXT NOT NULL,
            thread_id TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            published_at TEXT,
            author TEXT,
            like_count INTEGER,
            reply_count INTEGER,
            text_original TEXT,
            item_json TEXT NOT NULL,
            FOREIGN KEY(run_id) REFERENCES collection_runs(id) ON DELETE CASCADE,
            UNIQUE(video_id, thread_id)
        );

        CREATE TABLE IF NOT EXISTS clean_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            raw_thread_id INTEGER NOT NULL,
            video_id TEXT NOT NULL,
            comment_id TEXT NOT NULL,
            cleaned_at TEXT NOT NULL,
            published_at TEXT,
            author TEXT,
            like_count INTEGER,
            reply_count INTEGER,
            text TEXT NOT NULL,
            text_original TEXT,
            FOREIGN KEY(raw_thread_id) REFERENCES raw_comment_threads(id) ON DELETE CASCADE,
            UNIQUE(video_id, comment_id)
        );
        """
    )
    conn.commit()


def insert_collection_run(
    conn: sqlite3.Connection,
    *,
    video_id: str,
    video_url: str,
    order_mode: str,
    max_comments: int,
) -> int:
    cur = conn.execute(
        """
        INSERT INTO collection_runs (video_id, video_url, collected_at, order_mode, max_comments)
        VALUES (?, ?, ?, ?, ?)
        """,
        (video_id, video_url, utc_now_iso(), order_mode, int(max_comments)),
    )
    conn.commit()
    return int(cur.lastrowid)


def insert_raw_thread(
    conn: sqlite3.Connection,
    *,
    run_id: int,
    video_id: str,
    item: Dict[str, Any],
) -> None:
    thread_id = str(item.get("id") or "").strip()
    snippet = (item.get("snippet") or {}) if isinstance(item.get("snippet"), dict) else {}
    top = snippet.get("topLevelComment") or {}
    top_snippet = (top.get("snippet") or {}) if isinstance(top.get("snippet"), dict) else {}

    published_at = top_snippet.get("publishedAt")
    author = top_snippet.get("authorDisplayName")
    text_original = top_snippet.get("textDisplay")
    like_count = top_snippet.get("likeCount")
    reply_count = snippet.get("totalReplyCount")

    conn.execute(
        """
        INSERT OR IGNORE INTO raw_comment_threads (
            run_id, video_id, thread_id, fetched_at,
            published_at, author, like_count, reply_count,
            text_original, item_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(run_id),
            video_id,
            thread_id,
            utc_now_iso(),
            published_at,
            author,
            like_count,
            reply_count,
            text_original,
            json.dumps(item, ensure_ascii=False),
        ),
    )


def latest_run_id(conn: sqlite3.Connection) -> Optional[int]:
    row = conn.execute("SELECT id FROM collection_runs ORDER BY id DESC LIMIT 1").fetchone()
    if not row:
        return None
    return int(row[0])


def iter_raw_threads(conn: sqlite3.Connection, run_id: int) -> Iterable[sqlite3.Row]:
    return conn.execute(
        """
        SELECT id, video_id, thread_id, item_json
        FROM raw_comment_threads
        WHERE run_id = ?
        ORDER BY id ASC
        """,
        (int(run_id),),
    )


def insert_clean_comment(
    conn: sqlite3.Connection,
    *,
    raw_thread_id: int,
    video_id: str,
    comment_id: str,
    published_at: Optional[str],
    author: Optional[str],
    like_count: Optional[int],
    reply_count: Optional[int],
    text: str,
    text_original: Optional[str],
) -> None:
    conn.execute(
        """
        INSERT OR IGNORE INTO clean_comments (
            raw_thread_id, video_id, comment_id, cleaned_at,
            published_at, author, like_count, reply_count,
            text, text_original
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(raw_thread_id),
            video_id,
            comment_id,
            utc_now_iso(),
            published_at,
            author,
            like_count,
            reply_count,
            text,
            text_original,
        ),
    )
