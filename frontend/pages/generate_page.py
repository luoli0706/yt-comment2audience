from __future__ import annotations

import json
import threading
import time

import requests
import flet as ft


def generate_view(page: ft.Page, server_url: str) -> ft.View:
    url_field = ft.TextField(label="YouTube URL", width=400)
    max_comments_field = ft.TextField(label="max_comments", width=150, value="20")
    output = ft.TextField(
        label="结果",
        multiline=True,
        read_only=True,
        expand=True,
        min_lines=20,
    )

    def _set_output(data: object) -> None:
        if isinstance(data, (dict, list)):
            output.value = json.dumps(data, ensure_ascii=False, indent=2)
        else:
            output.value = str(data)
        output.update()

    last_run_id: int | None = None

    loading_text = ft.Text("生成中，请稍作等候", size=12, color=ft.colors.GREY_600)
    dot_colors = [ft.colors.GREY_400] * 6
    dots = [
        ft.Container(width=10, height=10, bgcolor=dot_colors[i], border_radius=999)
        for i in range(6)
    ]
    loading_row = ft.Row(controls=dots, spacing=6)
    loading_box = ft.Column(
        controls=[loading_text, loading_row],
        spacing=8,
        visible=False,
    )

    loading_running = False

    def _can_update(ctrl: ft.Control) -> bool:
        return getattr(ctrl, "page", None) is not None

    def _animate_loading() -> None:
        nonlocal loading_running
        step = 0
        while loading_running:
            if not _can_update(loading_row):
                time.sleep(0.1)
                continue
            for i, dot in enumerate(dots):
                phase = (step + i) % 6
                size = 8 + (phase if phase <= 3 else 6 - phase)
                dot.width = size
                dot.height = size
                dot.bgcolor = ft.colors.with_opacity(1.0, ft.colors.BLUE_500)
                dot.opacity = min(1.0, 0.35 + phase * 0.08)
            if _can_update(loading_row):
                loading_row.update()
            step = (step + 1) % 6
            time.sleep(0.25)

    def _set_loading(on: bool) -> None:
        nonlocal loading_running
        loading_running = on
        loading_box.visible = on
        if _can_update(loading_box):
            loading_box.update()
        if on:
            threading.Thread(target=_animate_loading, daemon=True).start()

    def on_collect_click(_: ft.ControlEvent) -> None:
        url = (url_field.value or "").strip()
        if not url:
            _set_output("请输入 URL")
            return
        try:
            max_comments = int((max_comments_field.value or "20").strip())
        except ValueError:
            _set_output("max_comments 必须为整数")
            return
        try:
            resp = requests.post(
                f"{server_url}/api/pipeline",
                json={"url": url, "order": "hot", "max_comments": max_comments},
                timeout=180,
            )
            data = resp.json()
        except Exception as e:  # noqa: BLE001
            _set_output(f"请求失败: {e}")
            return
        _set_output(data)
        if isinstance(data, dict) and data.get("ok") is True:
            try:
                nonlocal last_run_id
                last_run_id = int(data.get("run_id"))
            except Exception:
                last_run_id = None

    def on_generate_portrait(_: ft.ControlEvent) -> None:
        nonlocal last_run_id
        if not last_run_id:
            _set_output("请先采集并清洗，确保获得 run_id")
            return
        _set_loading(True)
        try:
            resp = requests.post(
                f"{server_url}/api/portrait",
                json={"run_id": last_run_id, "overwrite": True},
                timeout=600,
            )
            data = resp.json()
        except Exception as e:  # noqa: BLE001
            _set_loading(False)
            _set_output(f"请求失败: {e}")
            return
        _set_loading(False)
        _set_output(data)
        if isinstance(data, dict) and data.get("ok") is True:
            page.data["selected_run_id"] = last_run_id
            page.data["prev_route"] = "/generate"
            page.data["force_refresh"] = True
            page.go("/portrait-detail")

    def on_view_detail(_: ft.ControlEvent) -> None:
        nonlocal last_run_id
        if not last_run_id:
            _set_output("暂无可查看的 run_id，请先采集或生成")
            return
        page.data["selected_run_id"] = last_run_id
        page.data["prev_route"] = "/generate"
        page.data["force_refresh"] = True
        page.go("/portrait-detail")

    left = ft.Column(
        controls=[
            ft.Text("画像生成", size=18, weight=ft.FontWeight.W_600),
            url_field,
            max_comments_field,
            ft.Row(
                controls=[
                    ft.ElevatedButton("采集并清洗", on_click=on_collect_click),
                    ft.OutlinedButton(
                        "画像生成",
                        on_click=on_generate_portrait,
                    ),
                    ft.OutlinedButton(
                        "查看画像详情",
                        on_click=on_view_detail,
                    ),
                ]
            ),
            loading_box,
            ft.Text(f"服务端：{server_url}", size=12, color=ft.colors.GREY_600),
        ],
        width=420,
        spacing=12,
    )

    right = ft.Container(content=output, expand=True)

    return ft.View(
        route="/generate",
        controls=[
            ft.AppBar(
                title=ft.Text("画像生成"),
                leading=ft.IconButton(ft.icons.ARROW_BACK, on_click=lambda _: page.go("/")),
            ),
            ft.Row([left, right], expand=True),
        ],
        padding=20,
    )
