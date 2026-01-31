from __future__ import annotations

import json
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
        try:
            resp = requests.post(
                f"{server_url}/api/portrait",
                json={"run_id": last_run_id, "overwrite": True},
                timeout=300,
            )
            data = resp.json()
        except Exception as e:  # noqa: BLE001
            _set_output(f"请求失败: {e}")
            return
        _set_output(data)
        if isinstance(data, dict) and data.get("ok") is True:
            page.data["selected_run_id"] = last_run_id
            page.data["prev_route"] = "/generate"
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
                ]
            ),
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
