from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def load_frontend_env() -> None:
    """Load frontend .env (if present) and fall back to project root .env."""

    frontend_env = Path(__file__).resolve().parent / ".env"
    root_env = Path(__file__).resolve().parents[1] / ".env"

    if frontend_env.exists():
        load_dotenv(frontend_env)
    elif root_env.exists():
        load_dotenv(root_env)


def server_url() -> str:
    return os.getenv("SERVER_URL", "http://127.0.0.1:5076").rstrip("/")
