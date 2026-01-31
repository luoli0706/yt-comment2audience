from __future__ import annotations

import requests
import flet as ft


def collection_list_view(page: ft.Page, server_url: str) -> ft.View:
    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("run_id")),
            ft.DataColumn(ft.Text("video_url")),
            ft.DataColumn(ft.Text("title")),
            ft.DataColumn(ft.Text("channel")),
            ft.DataColumn(ft.Text("collected_at")),
            ft.DataColumn(ft.Text("raw")),
            ft.DataColumn(ft.Text("clean")),
            ft.DataColumn(ft.Text("action")),
        ],
        rows=[],
        expand=True,
    )

    status = ft.Text("", size=12, color=ft.colors.GREY_600)

    def _safe_update(ctrl: ft.Control) -> None:
        if getattr(ctrl, "page", None) is not None:
            ctrl.update()

    def _set_rows(items: list[dict]) -> None:
        try:
            items = sorted(items, key=lambda x: int(x.get("run_id") or 0), reverse=True)
        except Exception:
            pass
        rows = []
        for it in items:
            run_id = it.get("run_id")
            def _on_delete(e: ft.ControlEvent, rid=run_id) -> None:
                try:
                    resp = requests.post(
                        f"{server_url}/api/collections/delete",
                        json={"run_id": rid},
                        timeout=60,
                    )
                    data = resp.json()
                except Exception as ex:  # noqa: BLE001
                    status.value = f"删除失败: {ex}"
                    _safe_update(status)
                    return
                if not data.get("ok"):
                    status.value = f"删除失败: {data}"
                    _safe_update(status)
                    return
                on_refresh(None)
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(it.get("run_id", "")))),
                        ft.DataCell(
                            ft.Text(str(it.get("video_url") or ""), max_lines=2, overflow=ft.TextOverflow.ELLIPSIS)
                        ),
                        ft.DataCell(
                            ft.Text(str(it.get("video_title") or ""), max_lines=2, overflow=ft.TextOverflow.ELLIPSIS)
                        ),
                        ft.DataCell(ft.Text(str(it.get("channel_title") or ""), max_lines=1)),
                        ft.DataCell(ft.Text(str(it.get("collected_at") or ""))),
                        ft.DataCell(ft.Text(str(it.get("raw_count") or ""))),
                        ft.DataCell(ft.Text(str(it.get("clean_count") or ""))),
                        ft.DataCell(ft.OutlinedButton("删除", on_click=_on_delete)),
                    ]
                )
            )
        table.rows = rows
        _safe_update(table)

    def on_refresh(_: ft.ControlEvent) -> None:
        try:
            resp = requests.get(f"{server_url}/api/collections", timeout=60)
            data = resp.json()
            items = data.get("items") or []
            _set_rows(items if isinstance(items, list) else [])
            status.value = f"共 {len(items) if isinstance(items, list) else 0} 条"
        except Exception as e:  # noqa: BLE001
            status.value = f"加载失败: {e}"
        _safe_update(status)

    view = ft.View(
        route="/collections",
        controls=[
            ft.AppBar(
                title=ft.Text("原始数据总表"),
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

    view.on_mount = lambda _: on_refresh(None)
    return view
