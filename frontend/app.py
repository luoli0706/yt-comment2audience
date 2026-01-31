from __future__ import annotations

import os
from pathlib import Path

import flet as ft
from dotenv import load_dotenv


def _load_frontend_env() -> None:
    """Load frontend .env (if present) and fall back to root .env."""

    frontend_env = Path(__file__).resolve().parent / ".env"
    root_env = Path(__file__).resolve().parents[1] / ".env"

    if frontend_env.exists():
        load_dotenv(frontend_env)
    elif root_env.exists():
        load_dotenv(root_env)


def _server_url() -> str:
    return os.getenv("SERVER_URL", "http://127.0.0.1:5076").rstrip("/")


def _main_view(page: ft.Page) -> ft.View:
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
            ft.Text(f"当前服务端：{_server_url()}", size=12, color=ft.Colors.GREY_600),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.START,
        padding=20,
        spacing=12,
    )


def _query_view(page: ft.Page) -> ft.View:
    return ft.View(
        route="/query",
        controls=[
            ft.AppBar(title=ft.Text("查询画像"), leading=ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: page.go("/"))),
            ft.Text("（占位）此页面后续用于查询画像。"),
        ],
        padding=20,
    )


def _generate_view(page: ft.Page) -> ft.View:
    return ft.View(
        route="/generate",
        controls=[
            ft.AppBar(title=ft.Text("画像生成"), leading=ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda _: page.go("/"))),
            ft.Text("（占位）此页面后续用于生成画像。"),
        ],
        padding=20,
    )


def main(page: ft.Page) -> None:
    _load_frontend_env()

    page.title = "yt-comment2audience"
    page.theme_mode = ft.ThemeMode.LIGHT

    def on_route_change(route: ft.RouteChangeEvent) -> None:
        page.views.clear()
        if page.route == "/":
            page.views.append(_main_view(page))
        elif page.route == "/query":
            page.views.append(_query_view(page))
        elif page.route == "/generate":
            page.views.append(_generate_view(page))
        else:
            page.views.append(_main_view(page))
        page.update()

    page.on_route_change = on_route_change
    page.go(page.route or "/")


if __name__ == "__main__":
    ft.app(target=main)
