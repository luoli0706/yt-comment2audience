from __future__ import annotations

import flet as ft


def portrait_detail_view(page: ft.Page) -> ft.View:
    return ft.View(
        route="/portrait-detail",
        controls=[
            ft.AppBar(
                title=ft.Text("画像详情"),
                leading=ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: page.go("/generate")),
            ),
            ft.Text("（占位）此页面后续展示画像详情。"),
        ],
        padding=20,
    )
