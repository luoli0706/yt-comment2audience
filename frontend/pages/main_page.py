from __future__ import annotations

import flet as ft


def main_view(page: ft.Page, server_url: str) -> ft.View:
    return ft.View(
        route="/",
        controls=[
            ft.AppBar(title=ft.Text("yt-comment2audience")),
            ft.Text("选择功能：", size=18, weight=ft.FontWeight.W_600),
            ft.ElevatedButton(
                "查询画像",
                on_click=lambda _: page.go("/query"),
            ),
            ft.ElevatedButton(
                "画像生成",
                on_click=lambda _: page.go("/generate"),
            ),
            ft.Divider(),
            ft.Text(f"当前服务端：{server_url}", size=12, color=ft.colors.GREY_600),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.START,
        padding=20,
        spacing=12,
    )
