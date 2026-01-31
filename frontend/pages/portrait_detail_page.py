from __future__ import annotations

import json
from typing import Any, Dict

import flet as ft
import requests


def _pie_chart(title: str, data: Dict[str, Any], *, width: int = 260) -> ft.Control:
    if not data:
        return ft.Text(f"{title}: 无数据")

    palette = [
        ft.colors.BLUE_500,
        ft.colors.GREEN_500,
        ft.colors.ORANGE_500,
        ft.colors.PURPLE_500,
        ft.colors.RED_500,
        ft.colors.TEAL_500,
    ]

    sections = []
    legend_rows = []
    for idx, (key, value) in enumerate(data.items()):
        try:
            val = float(value or 0)
        except Exception:
            val = 0.0
        color = palette[idx % len(palette)]
        sections.append(
            ft.PieChartSection(
                value=val,
                title="",
                radius=70,
                color=color,
            )
        )
        legend_rows.append(
            ft.Row(
                [
                    ft.Container(width=10, height=10, bgcolor=color, border_radius=2),
                    ft.Text(f"{key}: {val:.2f}"),
                ],
                spacing=6,
            )
        )

    return ft.Column(
        controls=[
            ft.Text(title, weight=ft.FontWeight.W_600),
            ft.Row(
                [
                    ft.Container(
                        content=ft.PieChart(
                            sections=sections,
                            sections_space=2,
                            center_space_radius=16,
                        ),
                        width=width,
                        height=200,
                    ),
                    ft.Column(legend_rows, spacing=4),
                ],
                spacing=12,
            ),
        ],
        spacing=8,
    )


def _bar_chart(title: str, data: Dict[str, Any], *, width: int = 360) -> ft.Control:
    if not data:
        return ft.Text(f"{title}: 无数据")

    groups = []
    for idx, (key, value) in enumerate(data.items()):
        try:
            val = float(value or 0)
        except Exception:
            val = 0.0
        groups.append(
            ft.BarChartGroup(
                x=idx,
                bar_rods=[ft.BarChartRod(from_y=0, to_y=val)],
            )
        )

    labels = [ft.ChartAxisLabel(value=i, label=ft.Text(str(k))) for i, k in enumerate(data.keys())]

    return ft.Column(
        controls=[
            ft.Text(title, weight=ft.FontWeight.W_600),
            ft.Container(
                content=ft.BarChart(
                    bar_groups=groups,
                    groups_space=14,
                    max_y=1.0,
                    border=ft.border.all(1, ft.colors.GREY_300),
                    bottom_axis=ft.ChartAxis(labels=labels, labels_interval=1),
                    left_axis=ft.ChartAxis(labels_interval=0.25),
                ),
                width=width,
                height=220,
            ),
        ],
        spacing=8,
    )


def _progress_list(title: str, items: list[dict], key_name: str, key_value: str) -> ft.Control:
    if not items:
        return ft.Text(f"{title}: 无数据")

    rows = [ft.Text(title, weight=ft.FontWeight.W_600)]
    for item in items:
        label = str(item.get(key_name, ""))
        try:
            val = float(item.get(key_value, 0) or 0)
        except Exception:
            val = 0.0
        rows.append(
            ft.Row(
                [
                    ft.Text(label, width=220, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.ProgressBar(value=max(0.0, min(1.0, val)), width=200),
                    ft.Text(f"{val:.2f}", width=60),
                ]
            )
        )

    return ft.Column(controls=rows, spacing=6)


def portrait_detail_view(page: ft.Page, server_url: str) -> ft.View:
    status = ft.Text("", color=ft.colors.RED_600)
    summary = ft.Text("", selectable=True)
    tags = ft.Text("", selectable=True)
    meta = ft.Text("", size=12, color=ft.colors.GREY_600)

    left_container = ft.Column(spacing=8, width=520)
    charts_container = ft.Column(spacing=10, width=520)

    def _safe_update(ctrl: ft.Control) -> None:
        if getattr(ctrl, "page", None) is not None:
            ctrl.update()

    def _load_portrait(_: ft.ControlEvent | None = None) -> None:
        run_id = (page.data or {}).get("selected_run_id")
        if not run_id:
            status.value = "未选择 run_id，请从列表进入。"
            _safe_update(status)
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
            _safe_update(status)
            return

        if not data.get("ok"):
            status.value = f"服务端错误: {data}"
            _safe_update(status)
            return

        portrait = data.get("portrait") or {}
        summary.value = str(portrait.get("summary") or "")
        tags.value = ", ".join(portrait.get("tags") or [])
        meta.value = (
            f"run_id={data.get('run_id')} | 标题: {data.get('video_title') or ''} | 频道: {data.get('channel_title') or ''}"
        )

        insights = portrait.get("audience_insights") or {}
        confidence = portrait.get("confidence") or 0

        def _card(title: str, body: ft.Control) -> ft.Container:
            return ft.Container(
                content=ft.Column([ft.Text(title, weight=ft.FontWeight.W_600), body], spacing=6),
                padding=12,
                border=ft.border.all(1, ft.colors.GREY_300),
                border_radius=8,
            )

        left_container.controls = [
            ft.Text(meta.value, size=12, color=ft.colors.GREY_600),
            ft.Row(
                [
                    _card("置信度", ft.Text(f"{float(confidence):.2f}")),
                    _card("parse_ok", ft.Text(str(data.get("parse_ok")))),
                ]
            ),
            _card("摘要", summary),
            _card("标签", tags),
            _card("兴趣", ft.Text("、".join(insights.get("interests") or []), selectable=True)),
            _card("价值观", ft.Text("、".join(insights.get("values") or []), selectable=True)),
            _card("内容偏好", ft.Text("、".join(insights.get("content_preferences") or []), selectable=True)),
            ft.Row(
                controls=[
                    ft.ElevatedButton("生成画像", on_click=on_generate_click),
                    ft.OutlinedButton("刷新", on_click=lambda _: _load_portrait()),
                ]
            ),
        ]

        status.value = ""
        language_dist = portrait.get("language_distribution") or {}
        sentiment = portrait.get("sentiment") or {}

        charts_container.controls = [
            ft.Text("分布概览", weight=ft.FontWeight.W_600, size=16),
            _pie_chart("语言分布", language_dist, width=240),
            _bar_chart("语言分布（柱状）", language_dist, width=420),
            ft.Divider(),
            _pie_chart("情感分布", sentiment, width=240),
            _bar_chart("情感分布（柱状）", sentiment, width=420),
            ft.Divider(),
            _progress_list("核心话题权重", portrait.get("topics") or [], "name", "weight"),
        ]

        _safe_update(left_container)
        _safe_update(status)
        _safe_update(charts_container)

    def on_generate_click(_: ft.ControlEvent) -> None:
        run_id = (page.data or {}).get("selected_run_id")
        if not run_id:
            status.value = "未选择 run_id"
            _safe_update(status)
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
            _safe_update(status)
            return
        if not data.get("ok"):
            status.value = f"服务端错误: {data}"
            _safe_update(status)
            return
        _load_portrait()

    def _go_back(_: ft.ControlEvent) -> None:
        prev = (page.data or {}).get("prev_route") or "/portraits"
        page.go(str(prev))

    content = ft.Column(
        controls=[
            status,
            ft.Row(
                controls=[
                    left_container,
                    ft.VerticalDivider(),
                    charts_container,
                ],
                expand=True,
                spacing=10,
            ),
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    view = ft.View(
        route="/portrait-detail",
        controls=[
            ft.AppBar(
                title=ft.Text("画像详情"),
                leading=ft.IconButton(ft.icons.ARROW_BACK, on_click=_go_back),
                actions=[ft.IconButton(ft.icons.REFRESH, on_click=lambda _: _load_portrait())],
            ),
            content,
        ],
        padding=20,
        scroll=ft.ScrollMode.AUTO,
    )
    view.data = {"refresh": _load_portrait}
    return view
