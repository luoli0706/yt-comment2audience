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
            "name": "yt-comment2audience",
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


@app.post("/api/portrait")
def portrait_dispatch():
    """Portrait endpoint: (optional) collect+clean -> build portrait -> store+return.

    Request JSON supports either:
    - {run_id, overwrite?}
    - {url, order, max_comments, overwrite?}
    """

    payload: Dict[str, Any] = request.get_json(silent=True) or {}
    overwrite = bool(payload.get("overwrite") is True)

    run_id_raw = payload.get("run_id")
    url = str(payload.get("url") or "").strip()
    order = str(payload.get("order") or "hot").strip().lower()
    max_comments_raw = payload.get("max_comments", 50)

    from src.config import load_settings  # noqa: WPS433

    settings = load_settings()

    try:
        if run_id_raw not in (None, ""):
            run_id = int(run_id_raw)
            if run_id <= 0:
                return jsonify({"ok": False, "error": "run_id must be positive int"}), 400
            video_id = ""
        else:
            if not url:
                return jsonify({"ok": False, "error": "Missing url or run_id"}), 400
            if order not in {"hot", "time"}:
                return jsonify({"ok": False, "error": "order must be hot|time"}), 400

            try:
                max_comments = int(max_comments_raw)
            except Exception:
                return jsonify({"ok": False, "error": "max_comments must be int"}), 400

            max_comments = max(1, min(100, max_comments))

            from src.data_analyse.pipeline import (  # noqa: WPS433
                clean_run_to_db,
                collect_raw_to_db,
            )

            run_id, video_id, _raw_count = collect_raw_to_db(
                url=url,
                order=order,  # type: ignore[arg-type]
                max_comments=max_comments,
                settings=settings,
            )
            clean_run_to_db(run_id=run_id, settings=settings)

        from src.data_analyse.portrait import generate_portrait_for_run  # noqa: WPS433

        portrait_result = generate_portrait_for_run(
            run_id=int(run_id),
            settings=settings,
            overwrite=overwrite,
        )

        # Avoid returning huge raw payload by default.
        raw = portrait_result.get("portrait_raw")
        if isinstance(raw, str) and len(raw) > 6000:
            portrait_result["portrait_raw"] = raw[:6000] + "\n...(truncated)"

        # If video_id was derived during generation, surface it.
        if not video_id:
            video_id = str(portrait_result.get("video_id") or "")

        return jsonify(
            {
                "ok": True,
                "run_id": int(run_id),
                "video_id": video_id,
                "portrait": portrait_result.get("portrait"),
                "parse_ok": bool(portrait_result.get("parse_ok")),
                "error": portrait_result.get("error"),
                "prompt_name": portrait_result.get("prompt_name"),
                "prompt_version": portrait_result.get("prompt_version"),
                "provider": portrait_result.get("provider"),
                "model": portrait_result.get("model"),
                "cached": bool(portrait_result.get("cached")),
                "portrait_raw": portrait_result.get("portrait_raw"),
            }
        )
    except Exception as e:  # noqa: BLE001
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "5076")),
        debug=True,
    )
