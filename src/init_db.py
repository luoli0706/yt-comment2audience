from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

# Allow `python src/init_db.py`
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import db_path, load_settings  # noqa: E402
from src.db_sqlite import connect, init_schema  # noqa: E402


def main() -> int:
    load_dotenv()
    settings = load_settings()
    path = db_path(settings)

    conn = connect(path)
    try:
        init_schema(conn)
    finally:
        conn.close()

    print(f"SQLite DB ready: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
