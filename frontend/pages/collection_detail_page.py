from __future__ import annotations

import json
import flet as ft
import requests


def collection_detail_view(page: ft.Page, server_url: str) -> ft.View:
    status = ft.Text("", color=ft.colors.RED_600)
    meta = ft.Text("", size=12, color=ft.colors.GREY_600)

    left = ft.Column(spacing=8, width=420)
    raw_json = ft.TextField(label="详情 JSON", multiline=True, read_only=True, expand=True, min_lines=18)

    def _safe_update(ctrl: ft.Control) -> None:
        if getattr(ctrl, "page", None) is not None:
            ctrl.update()

    def _render_row(label: str, value: object) -> ft.Row:
        return ft.Row([ft.Text(f"{label}:"), ft.Text(str(value or ""), selectable=True)], wrap=True)

    def _load_detail() -> None:
        run_id = (page.data or {}).get("selected_run_id")
        if not run_id:
            status.value = "未选择 run_id，请从列表进入。"
            _safe_update(status)
            return

        try:
            resp = requests.post(
                f"{server_url}/api/collections/detail",
                json={"run_id": run_id},
                timeout=60,
            )
            data = resp.json()
        except Exception as e:  # noqa: BLE001
            status.value = f"请求失败: {e}"
            _safe_update(status)
            return

        if not data.get("ok"):
            status.value = f"服务端错误: {data}"
            _safe_update(status)
            return

        left.controls = [
            _render_row("run_id", data.get("run_id")),
            _render_row("video_url", data.get("video_url")),
            _render_row("video_title", data.get("video_title")),
            _render_row("channel_title", data.get("channel_title")),
            _render_row("channel_id", data.get("channel_id")),
            _render_row("collected_at", data.get("collected_at")),
            _render_row("order_mode", data.get("order_mode")),
            _render_row("max_comments", data.get("max_comments")),
            _render_row("raw_count", data.get("raw_count")),
            _render_row("clean_count", data.get("clean_count")),
        ]
        raw_json.value = json.dumps(data, ensure_ascii=False, indent=2)
        meta.value = f"run_id={data.get('run_id')} | {data.get('video_title') or ''}"
        status.value = ""

        _safe_update(left)
        _safe_update(raw_json)
        _safe_update(meta)
        _safe_update(status)

    def _go_back(_: ft.ControlEvent) -> None:
        prev = (page.data or {}).get("prev_route") or "/collections"
        page.go(str(prev))

    view = ft.View(
        route="/collections/detail",
        controls=[
            ft.AppBar(
                title=ft.Text("原始数据详情"),
                leading=ft.IconButton(ft.icons.ARROW_BACK, on_click=_go_back),
                actions=[ft.IconButton(ft.icons.REFRESH, on_click=lambda _: _load_detail())],
            ),
            meta,
            status,
            ft.Row([left, raw_json], expand=True),
        ],
        padding=20,
    )
    view.data = {"refresh": _load_detail}
    view.on_mount = lambda _: _load_detail()
    return view
