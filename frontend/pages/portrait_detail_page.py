from __future__ import annotations

import json
from typing import Any, Dict

import flet as ft
import requests


def _pie_chart(title: str, data: Dict[str, Any]) -> ft.Control:
    if not data:
        return ft.Text(f"{title}: 无数据")

    sections = []
    for key, value in data.items():
        try:
            val = float(value or 0)
        except Exception:
            val = 0.0
        sections.append(
            ft.PieChartSection(
                value=val,
                title=str(key),
                radius=80,
            )
        )

    return ft.Column(
        controls=[
            ft.Text(title, weight=ft.FontWeight.W_600),
            ft.PieChart(sections=sections, sections_space=2, center_space_radius=20),
        ],
        spacing=8,
    )


def _bar_chart(title: str, items: list[dict], key_name: str, key_value: str) -> ft.Control:
    if not items:
        return ft.Text(f"{title}: 无数据")

    groups = []
    for item in items:
        label = str(item.get(key_name, ""))
        try:
            val = float(item.get(key_value, 0) or 0)
        except Exception:
            val = 0.0
        groups.append(
            ft.BarChartGroup(
                x=label,
                bar_rods=[ft.BarChartRod(from_y=0, to_y=val)],
            )
        )

    return ft.Column(
        controls=[
            ft.Text(title, weight=ft.FontWeight.W_600),
            ft.BarChart(
                bar_groups=groups,
                groups_space=12,
                border=ft.Border.all(1, ft.colors.GREY_300),
                max_y=1.0,
                expand=True,
            ),
        ],
        spacing=8,
    )


def portrait_detail_view(page: ft.Page, server_url: str) -> ft.View:
    status = ft.Text("", color=ft.colors.RED_600)
    summary = ft.Text("", selectable=True)
    tags = ft.Text("", selectable=True)
    meta = ft.Text("", size=12, color=ft.colors.GREY_600)

    charts_container = ft.Column(spacing=12, expand=True)

    def _load_portrait() -> None:
        run_id = (page.data or {}).get("selected_run_id")
        if not run_id:
            status.value = "未选择 run_id，请从列表进入。"
            status.update()
            return

        try:
            resp = requests.post(
                f"{server_url}/api/portrait/query",
                json={"run_id": run_id},
                timeout=120,
            )
            data = resp.json()
        except Exception as e:  # noqa: BLE001
            status.value = f"请求失败: {e}"
            status.update()
            return

        if not data.get("ok"):
            status.value = f"服务端错误: {data}"
            status.update()
            return

        portrait = data.get("portrait") or {}
        summary.value = str(portrait.get("summary") or "")
        tags.value = ", ".join(portrait.get("tags") or [])
        meta.value = (
            f"run_id={data.get('run_id')} | 标题: {data.get('video_title') or ''} | 频道: {data.get('channel_title') or ''}"
        )

        summary.update()
        tags.update()
        meta.update()
        status.value = ""
        status.update()
        charts_container.controls = [
            _pie_chart("语言分布", portrait.get("language_distribution") or {}),
            _pie_chart("情感分布", portrait.get("sentiment") or {}),
            _bar_chart("核心话题权重", portrait.get("topics") or [], "name", "weight"),
        ]
        charts_container.update()

    def on_generate_click(_: ft.ControlEvent) -> None:
        run_id = (page.data or {}).get("selected_run_id")
        if not run_id:
            status.value = "未选择 run_id"
            status.update()
            return
        try:
            resp = requests.post(
                f"{server_url}/api/portrait",
                json={"run_id": run_id, "overwrite": True},
                timeout=300,
            )
            data = resp.json()
        except Exception as e:  # noqa: BLE001
            status.value = f"请求失败: {e}"
            status.update()
            return
        if not data.get("ok"):
            status.value = f"服务端错误: {data}"
            status.update()
            return
        _load_portrait()

    def _go_back(_: ft.ControlEvent) -> None:
        prev = (page.data or {}).get("prev_route") or "/portraits"
        page.go(str(prev))

    controls = [
        ft.AppBar(
            title=ft.Text("画像详情"),
            leading=ft.IconButton(ft.icons.ARROW_BACK, on_click=_go_back),
            actions=[ft.IconButton(ft.icons.REFRESH, on_click=lambda _: _load_portrait())],
        ),
        meta,
        status,
        ft.Row(
            controls=[
                ft.Column(
                    controls=[
                        ft.Text("摘要"),
                        summary,
                        ft.Text("标签"),
                        tags,
                        ft.Row(
                            controls=[
                                ft.ElevatedButton("生成画像", on_click=on_generate_click),
                                ft.OutlinedButton("刷新", on_click=lambda _: _load_portrait()),
                            ]
                        ),
                    ],
                    width=420,
                ),
                charts_container,
            ],
            expand=True,
        ),
    ]

    view = ft.View(route="/portrait-detail", controls=controls, padding=20)
    # Load once on enter
    _load_portrait()
    return view
