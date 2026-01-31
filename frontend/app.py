from __future__ import annotations

import flet as ft

# NOTE: When running `python frontend/app.py`, the script directory is on sys.path,
# so we import local modules directly.
from config import load_frontend_env, server_url
from pages import (
    collection_detail_view,
    collection_list_view,
    generate_view,
    main_view,
    portrait_detail_view,
    portrait_list_view,
    query_view,
)


def main(page: ft.Page) -> None:
    load_frontend_env()

    page.title = "yt-comment2audience"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.data = {"selected_run_id": None}

    def on_route_change(route: ft.RouteChangeEvent) -> None:
        page.views.clear()
        if page.route == "/":
            page.views.append(main_view(page, server_url()))
        elif page.route == "/query":
            page.views.append(query_view(page, server_url()))
        elif page.route == "/generate":
            page.views.append(generate_view(page, server_url()))
        elif page.route == "/portrait-detail":
            page.views.append(portrait_detail_view(page, server_url()))
        elif page.route == "/portraits":
            page.views.append(portrait_list_view(page, server_url()))
        elif page.route == "/collections":
            page.views.append(collection_list_view(page, server_url()))
        elif page.route == "/collections/detail":
            page.views.append(collection_detail_view(page, server_url()))
        else:
            page.views.append(main_view(page, server_url()))
        page.update()

    page.on_route_change = on_route_change
    page.go(page.route or "/")


if __name__ == "__main__":
    ft.app(target=main)
