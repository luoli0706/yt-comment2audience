from __future__ import annotations

import json
import requests
import flet as ft


def query_view(page: ft.Page, server_url: str) -> ft.View:
    run_id_field = ft.TextField(label="run_id", width=200)
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

    def _parse_run_id() -> int | None:
        raw = (run_id_field.value or "").strip()
        if not raw:
            _set_output("请输入 run_id")
            return None
        try:
            value = int(raw)
        except ValueError:
            _set_output("run_id 必须为整数")
            return None
        if value <= 0:
            _set_output("run_id 必须为正整数")
            return None
        return value

    def on_query_click(_: ft.ControlEvent) -> None:
        run_id = _parse_run_id()
        if run_id is None:
            return
        try:
            resp = requests.post(
                f"{server_url}/api/portrait/query",
                json={"run_id": run_id},
                timeout=60,
            )
            data = resp.json()
        except Exception as e:  # noqa: BLE001
            _set_output(f"请求失败: {e}")
            return
        _set_output(data)

    def on_delete_click(_: ft.ControlEvent) -> None:
        run_id = _parse_run_id()
        if run_id is None:
            return
        try:
            resp = requests.post(
                f"{server_url}/api/portrait/delete",
                json={"run_id": run_id},
                timeout=60,
            )
            data = resp.json()
        except Exception as e:  # noqa: BLE001
            _set_output(f"请求失败: {e}")
            return
        _set_output(data)

    left = ft.Column(
        controls=[
            ft.Text("查询画像", size=18, weight=ft.FontWeight.W_600),
            run_id_field,
            ft.Row(
                controls=[
                    ft.ElevatedButton("查询", on_click=on_query_click),
                    ft.OutlinedButton("删除", on_click=on_delete_click),
                ]
            ),
            ft.Text(f"服务端：{server_url}", size=12, color=ft.colors.GREY_600),
        ],
        width=260,
        spacing=12,
    )

    right = ft.Container(content=output, expand=True)

    return ft.View(
        route="/query",
        controls=[
            ft.AppBar(
                title=ft.Text("查询画像"),
                leading=ft.IconButton(ft.icons.ARROW_BACK, on_click=lambda _: page.go("/")),
            ),
            ft.Row([left, right], expand=True),
        ],
        padding=20,
    )
