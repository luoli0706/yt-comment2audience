from __future__ import annotations

import os

from dotenv import load_dotenv
from flask import Flask, jsonify


load_dotenv()

app = Flask(__name__)


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


if __name__ == "__main__":
    app.run(host=os.getenv("HOST", "127.0.0.1"), port=int(os.getenv("PORT", "5000")), debug=True)
