from __future__ import annotations

import flet as ft

from frontend.config import load_frontend_env, server_url
from frontend.pages import generate_view, main_view, portrait_detail_view, query_view


def main(page: ft.Page) -> None:
    load_frontend_env()

    page.title = "yt-comment2audience"
    page.theme_mode = ft.ThemeMode.LIGHT

    def on_route_change(route: ft.RouteChangeEvent) -> None:
        page.views.clear()
        if page.route == "/":
            page.views.append(main_view(page, server_url()))
        elif page.route == "/query":
            page.views.append(query_view(page, server_url()))
        elif page.route == "/generate":
            page.views.append(generate_view(page, server_url()))
        elif page.route == "/portrait-detail":
            page.views.append(portrait_detail_view(page))
        else:
            page.views.append(main_view(page, server_url()))
        page.update()

    page.on_route_change = on_route_change
    page.go(page.route or "/")


if __name__ == "__main__":
    ft.app(target=main)
