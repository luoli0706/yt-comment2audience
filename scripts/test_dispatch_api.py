from __future__ import annotations

import json
import os
import sys

import requests


def main() -> int:
    """Call the unified dispatch API and print the result.

    EN: Prints JSON with ensure_ascii=False so CJK/English characters display correctly.
    中文：使用 ensure_ascii=False 打印 JSON，确保中文/日文/韩文/英文等字符正常显示。

    Note/注意：
    - Start the server first: `python main.py`
    - Endpoint: POST /api/pipeline
    """

    base_url = os.getenv("BASE_URL", "http://127.0.0.1:5076").rstrip("/")
    endpoint = f"{base_url}/api/pipeline"

    payload = {
        "url": "https://www.youtube.com/watch?v=MdTAJ1J2LeM",
        "order": "hot",
        "max_comments": 10,
    }

    try:
        resp = requests.post(endpoint, json=payload, timeout=180)
    except Exception as e:  # noqa: BLE001
        print(f"Request failed: {e}", file=sys.stderr)
        return 2

    try:
        data = resp.json()
    except Exception:  # noqa: BLE001
        print(f"HTTP {resp.status_code} (non-JSON): {resp.text[:500]}", file=sys.stderr)
        return 2

    print(json.dumps(data, ensure_ascii=False, indent=2))

    return 0 if resp.ok and data.get("ok") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
