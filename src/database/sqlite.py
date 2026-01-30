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


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=? LIMIT 1", (name,)
    ).fetchone()
    return row is not None


def _migrate_v1_to_v2(conn: sqlite3.Connection) -> None:
    """Migrate old schema to run-scoped schema.

    EN: Previous versions used UNIQUE(video_id, thread_id) and UNIQUE(video_id, comment_id),
        which prevents storing multiple runs for the same video.
    中文：旧版本用 video_id 作为唯一键会导致同一视频多次调度无法入库；这里迁移为按 run_id 维度存储。
    """

    if not _table_exists(conn, "raw_comment_threads"):
        return

    # Detect v1 by checking whether clean_comments has run_id column.
    cols = {
        r[1] for r in conn.execute("PRAGMA table_info(clean_comments)").fetchall()
    } if _table_exists(conn, "clean_comments") else set()

    if "run_id" in cols:
        return

    conn.execute("BEGIN")
    try:
        conn.execute("ALTER TABLE raw_comment_threads RENAME TO raw_comment_threads_v1")
        if _table_exists(conn, "clean_comments"):
            conn.execute("ALTER TABLE clean_comments RENAME TO clean_comments_v1")

        # Recreate with v2 schema
        conn.executescript(
            """
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
                UNIQUE(run_id, thread_id)
            );

            CREATE TABLE IF NOT EXISTS clean_comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id INTEGER NOT NULL,
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
                FOREIGN KEY(run_id) REFERENCES collection_runs(id) ON DELETE CASCADE,
                FOREIGN KEY(raw_thread_id) REFERENCES raw_comment_threads(id) ON DELETE CASCADE,
                UNIQUE(run_id, comment_id)
            );
            """
        )

        # Copy raw threads
        conn.execute(
            """
            INSERT INTO raw_comment_threads (
                id, run_id, video_id, thread_id, fetched_at,
                published_at, author, like_count, reply_count,
                text_original, item_json
            )
            SELECT id, run_id, video_id, thread_id, fetched_at,
                   published_at, author, like_count, reply_count,
                   text_original, item_json
            FROM raw_comment_threads_v1
            """
        )

        # Copy clean comments if existed (derive run_id from raw_thread)
        if _table_exists(conn, "clean_comments_v1"):
            conn.execute(
                """
                INSERT INTO clean_comments (
                    run_id, raw_thread_id, video_id, comment_id, cleaned_at,
                    published_at, author, like_count, reply_count,
                    text, text_original
                )
                SELECT r.run_id, c.raw_thread_id, c.video_id, c.comment_id, c.cleaned_at,
                       c.published_at, c.author, c.like_count, c.reply_count,
                       c.text, c.text_original
                FROM clean_comments_v1 c
                JOIN raw_comment_threads_v1 r ON r.id = c.raw_thread_id
                """
            )

        conn.execute("DROP TABLE IF EXISTS clean_comments_v1")
        conn.execute("DROP TABLE IF EXISTS raw_comment_threads_v1")
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise


def init_schema(conn: sqlite3.Connection) -> None:
    # EN: Best-effort migration to keep old DBs usable.
    # 中文：做一次尽力迁移，保证旧 DB 仍可用。
    _migrate_v1_to_v2(conn)

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
            UNIQUE(run_id, thread_id)
        );

        CREATE TABLE IF NOT EXISTS clean_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
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
            FOREIGN KEY(run_id) REFERENCES collection_runs(id) ON DELETE CASCADE,
            FOREIGN KEY(raw_thread_id) REFERENCES raw_comment_threads(id) ON DELETE CASCADE,
            UNIQUE(run_id, comment_id)
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
    row = conn.execute(
        "SELECT id FROM collection_runs ORDER BY id DESC LIMIT 1"
    ).fetchone()
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
    run_id: int,
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
            run_id, raw_thread_id, video_id, comment_id, cleaned_at,
            published_at, author, like_count, reply_count,
            text, text_original
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(run_id),
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


def iter_clean_comments(conn: sqlite3.Connection, run_id: int) -> Iterable[sqlite3.Row]:
    """Return normalized comments for a given run.

    EN: This is what the dispatch endpoint returns to frontend.
    中文：这是调度接口返回给前端的最终结果。
    """

    return conn.execute(
        """
        SELECT
            video_id, comment_id,
            published_at, author,
            like_count, reply_count,
            text
        FROM clean_comments
        WHERE run_id = ?
        ORDER BY id ASC
        """,
        (int(run_id),),
    )
