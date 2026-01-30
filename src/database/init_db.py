from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import db_path, load_settings  # noqa: E402
from src.database.sqlite import connect, init_schema  # noqa: E402


def main() -> int:
    load_dotenv()
    settings = load_settings()
    path = db_path(settings)

    conn = connect(path)
    try:
        init_schema(conn)
    finally:
        conn.close()

    # EN: Prints the final DB path for convenience.
    # 中文：输出最终 DB 路径，方便确认创建位置。
    print(f"SQLite DB ready: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
