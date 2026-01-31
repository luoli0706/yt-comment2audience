from __future__ import annotations

import base64
import io
import json
from typing import Any, Dict

import flet as ft
import matplotlib.pyplot as plt
import requests


def _fig_to_base64(fig: plt.Figure) -> str:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=120)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _pie_chart(title: str, data: Dict[str, Any]) -> str | None:
    if not data:
        return None
    labels = list(data.keys())
    values = [float(data.get(k) or 0) for k in labels]
    fig, ax = plt.subplots(figsize=(4.2, 3.2))
    ax.pie(values, labels=labels, autopct="%1.0f%%")
    ax.set_title(title)
    return _fig_to_base64(fig)


def _bar_chart(title: str, items: list[dict], key_name: str, key_value: str) -> str | None:
    if not items:
        return None
    labels = [str(i.get(key_name, "")) for i in items]
    values = [float(i.get(key_value, 0) or 0) for i in items]
    fig, ax = plt.subplots(figsize=(5.2, 3.2))
    ax.bar(labels, values)
    ax.set_title(title)
    ax.tick_params(axis="x", rotation=30)
    return _fig_to_base64(fig)


def portrait_detail_view(page: ft.Page, server_url: str) -> ft.View:
    status = ft.Text("", color=ft.colors.RED_600)
    summary = ft.Text("", selectable=True)
    tags = ft.Text("", selectable=True)
    meta = ft.Text("", size=12, color=ft.colors.GREY_600)

    img_lang = ft.Image(width=420, height=320, fit=ft.ImageFit.CONTAIN)
    img_sent = ft.Image(width=420, height=320, fit=ft.ImageFit.CONTAIN)
    img_topics = ft.Image(width=520, height=320, fit=ft.ImageFit.CONTAIN)

    def _set_images(portrait: dict) -> None:
        lang_img = _pie_chart("语言分布", portrait.get("language_distribution") or {})
        sent_img = _pie_chart("情感分布", portrait.get("sentiment") or {})
        topics_img = _bar_chart("核心话题权重", portrait.get("topics") or [], "name", "weight")

        if lang_img:
            img_lang.src_base64 = lang_img
        if sent_img:
            img_sent.src_base64 = sent_img
        if topics_img:
            img_topics.src_base64 = topics_img

        img_lang.update()
        img_sent.update()
        img_topics.update()

    def _load_portrait() -> None:
        run_id = (page.data or {}).get("selected_run_id")
        if not run_id:
            status.value = "未选择 run_id，请从列表进入。"
            status.update()
            return

        try:
            resp = requests.post(
                f"{server_url}/api/portrait/query",
                json={"run_id": run_id},
                timeout=120,
            )
            data = resp.json()
        except Exception as e:  # noqa: BLE001
            status.value = f"请求失败: {e}"
            status.update()
            return

        if not data.get("ok"):
            status.value = f"服务端错误: {data}"
            status.update()
            return

        portrait = data.get("portrait") or {}
        summary.value = str(portrait.get("summary") or "")
        tags.value = ", ".join(portrait.get("tags") or [])
        meta.value = (
            f"run_id={data.get('run_id')} | 标题: {data.get('video_title') or ''} | 频道: {data.get('channel_title') or ''}"
        )

        summary.update()
        tags.update()
        meta.update()
        status.value = ""
        status.update()
        _set_images(portrait if isinstance(portrait, dict) else {})

    def on_generate_click(_: ft.ControlEvent) -> None:
        run_id = (page.data or {}).get("selected_run_id")
        if not run_id:
            status.value = "未选择 run_id"
            status.update()
            return
        try:
            resp = requests.post(
                f"{server_url}/api/portrait",
                json={"run_id": run_id, "overwrite": True},
                timeout=300,
            )
            data = resp.json()
        except Exception as e:  # noqa: BLE001
            status.value = f"请求失败: {e}"
            status.update()
            return
        if not data.get("ok"):
            status.value = f"服务端错误: {data}"
            status.update()
            return
        _load_portrait()

    def _go_back(_: ft.ControlEvent) -> None:
        prev = (page.data or {}).get("prev_route") or "/portraits"
        page.go(str(prev))

    controls = [
        ft.AppBar(
            title=ft.Text("画像详情"),
            leading=ft.IconButton(ft.icons.ARROW_BACK, on_click=_go_back),
            actions=[ft.IconButton(ft.icons.REFRESH, on_click=lambda _: _load_portrait())],
        ),
        meta,
        status,
        ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text("摘要"),
                        summary,
                        ft.Text("标签"),
                        tags,
                        ft.Row(
                            controls=[
                                ft.ElevatedButton("生成画像", on_click=on_generate_click),
                                ft.OutlinedButton("刷新", on_click=lambda _: _load_portrait()),
                            ]
                        ),
                    ],
                    width=420,
                ),
                ft.Column(
                    controls=[
                        img_lang,
                        img_sent,
                        img_topics,
                    ],
                    expand=True,
                ),
            ],
            expand=True,
        ),
    ]

    view = ft.View(route="/portrait-detail", controls=controls, padding=20)
    # Load once on enter
    _load_portrait()
    return view
