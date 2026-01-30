from __future__ import annotations

import json
import os
import sys

import requests
from dotenv import load_dotenv


def main() -> int:
    """Call POST /api/portrait and print DeepSeek portrait JSON."""

    load_dotenv()

    host = os.getenv("HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = os.getenv("PORT", "5076").strip() or "5076"
    base_url = os.getenv("BASE_URL", f"http://{host}:{port}").rstrip("/")
    endpoint = f"{base_url}/api/portrait"

    payload = {
        "url": "https://www.youtube.com/watch?v=MdTAJ1J2LeM",
        "order": "hot",
        "max_comments": 20,
        "overwrite": True,
    }

    try:
        resp = requests.post(endpoint, json=payload, timeout=300)
    except Exception as e:  # noqa: BLE001
        print(f"Request failed: {e}", file=sys.stderr)
        return 2

    try:
        data = resp.json()
    except Exception:  # noqa: BLE001
        print(f"HTTP {resp.status_code} (non-JSON): {resp.text[:800]}", file=sys.stderr)
        return 2

    print(json.dumps(data, ensure_ascii=False, indent=2))

    return 0 if resp.ok and data.get("ok") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
