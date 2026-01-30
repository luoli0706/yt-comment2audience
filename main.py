from __future__ import annotations

import os
from typing import Any, Dict

from dotenv import load_dotenv
from flask import Flask, jsonify, request


load_dotenv()

app = Flask(__name__)

# EN: Ensure JSON responses keep non-ASCII characters (Chinese/Japanese/Korean/etc.).
# 中文：确保 JSON 响应保留非 ASCII 字符（中文/日文/韩文等）。
app.json.ensure_ascii = False


@app.get("/")
def index():
    return jsonify(
        {
            "name": "Image_Analyse",
            "status": "ok",
            "model_provider": "deepseek",
            "ai_api_url": os.getenv("AI_API_URL", ""),
        }
    )


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/api/pipeline")
def pipeline_dispatch():
    """Unified dispatch endpoint: collect -> clean -> return result.

    EN: Frontend posts {url, order, max_comments}. Server stores raw data, cleans it,
        then returns normalized comments.
    中文：前端提交 {url, order, max_comments}，后端依次执行采集、清洗，并返回最终规格化结果。
    """

    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    url = str(payload.get("url") or "").strip()
    order = str(payload.get("order") or "hot").strip().lower()
    max_comments_raw = payload.get("max_comments", 50)

    if not url:
        return jsonify({"ok": False, "error": "Missing url"}), 400
    if order not in {"hot", "time"}:
        return jsonify({"ok": False, "error": "order must be hot|time"}), 400

    try:
        max_comments = int(max_comments_raw)
    except Exception:
        return jsonify({"ok": False, "error": "max_comments must be int"}), 400

    max_comments = max(1, min(100, max_comments))

    # Local import to keep Flask startup fast and avoid side effects.
    from src.data_analyse.pipeline import (  # noqa: WPS433
        clean_run_to_db,
        collect_raw_to_db,
        fetch_clean_result,
    )
    from src.config import load_settings  # noqa: WPS433

    settings = load_settings()

    try:
        run_id, video_id, raw_count = collect_raw_to_db(
            url=url,
            order=order,  # type: ignore[arg-type]
            max_comments=max_comments,
            settings=settings,
        )
        clean_count = clean_run_to_db(run_id=run_id, settings=settings)
        result = fetch_clean_result(run_id=run_id, settings=settings)
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500

    return jsonify(
        {
            "ok": True,
            "run_id": run_id,
            "video_id": video_id,
            "raw_count": raw_count,
            "clean_count": clean_count,
            "result_count": len(result),
            "result": result,
        }
    )


if __name__ == "__main__":
    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5076")),
        debug=True,
    )
