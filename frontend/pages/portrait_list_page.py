from __future__ import annotations

import json
import requests
import flet as ft


def portrait_list_view(page: ft.Page, server_url: str) -> ft.View:
    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("run_id")),
            ft.DataColumn(ft.Text("video_title")),
            ft.DataColumn(ft.Text("channel")),
            ft.DataColumn(ft.Text("collected_at")),
            ft.DataColumn(ft.Text("portrait_at")),
            ft.DataColumn(ft.Text("parse_ok")),
        ],
        rows=[],
        expand=True,
    )

    status = ft.Text("", size=12, color=ft.colors.GREY_600)

    def _set_rows(items: list[dict]) -> None:
        rows = []
        for it in items:
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(it.get("run_id", "")))),
                        ft.DataCell(ft.Text(str(it.get("video_title") or ""), max_lines=2)),
                        ft.DataCell(ft.Text(str(it.get("channel_title") or ""), max_lines=1)),
                        ft.DataCell(ft.Text(str(it.get("collected_at") or ""))),
                        ft.DataCell(ft.Text(str(it.get("portrait_created_at") or ""))),
                        ft.DataCell(ft.Text(str(it.get("parse_ok")))),
                    ]
                )
            )
        table.rows = rows
        table.update()

    def on_refresh(_: ft.ControlEvent) -> None:
        try:
            resp = requests.get(f"{server_url}/api/portraits", timeout=60)
            data = resp.json()
            items = data.get("items") or []
            _set_rows(items if isinstance(items, list) else [])
            status.value = f"共 {len(items) if isinstance(items, list) else 0} 条"
        except Exception as e:  # noqa: BLE001
            status.value = f"加载失败: {e}"
        status.update()

    on_refresh(None)

    return ft.View(
        route="/portraits",
        controls=[
            ft.AppBar(
                title=ft.Text("画像总表"),
                leading=ft.IconButton(ft.icons.ARROW_BACK, on_click=lambda _: page.go("/query")),
            ),
            ft.Row(
                controls=[
                    ft.ElevatedButton("刷新", on_click=on_refresh),
                    status,
                ]
            ),
            ft.Container(content=table, expand=True),
        ],
        padding=20,
    )
