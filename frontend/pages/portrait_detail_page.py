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
                    ft.Text(label, width=200, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
                    ft.ProgressBar(value=max(0.0, min(1.0, val)), width=220),
                    ft.Text(f"{val:.2f}", width=50),
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
    charts_container = ft.Column(spacing=12, expand=True)

    def _safe_update(ctrl: ft.Control) -> None:
        if getattr(ctrl, "page", None) is not None:
            ctrl.update()

    def _load_portrait() -> None:
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
        left_container.controls = [
            meta,
            ft.Text("摘要"),
            summary,
            ft.Text("标签"),
            tags,
            ft.Text("兴趣"),
            ft.Text("、".join(insights.get("interests") or []), selectable=True),
            ft.Text("价值观"),
            ft.Text("、".join(insights.get("values") or []), selectable=True),
            ft.Text("内容偏好"),
            ft.Text("、".join(insights.get("content_preferences") or []), selectable=True),
            ft.Row(
                controls=[
                    ft.ElevatedButton("生成画像", on_click=on_generate_click),
                    ft.OutlinedButton("刷新", on_click=lambda _: _load_portrait()),
                ]
            ),
        ]

        status.value = ""
        charts_container.controls = [
            _pie_chart("语言分布", portrait.get("language_distribution") or {}),
            _pie_chart("情感分布", portrait.get("sentiment") or {}),
            _progress_list("核心话题权重", portrait.get("topics") or [], "name", "weight"),
            _progress_list(
                "置信度",
                [{"name": "confidence", "weight": portrait.get("confidence") or 0}],
                "name",
                "weight",
            ),
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

    controls = [
        ft.AppBar(
            title=ft.Text("画像详情"),
            leading=ft.IconButton(ft.icons.ARROW_BACK, on_click=_go_back),
            actions=[ft.IconButton(ft.icons.REFRESH, on_click=lambda _: _load_portrait())],
        ),
        status,
        ft.Row(
            controls=[
                left_container,
                charts_container,
            ],
            expand=True,
        ),
    ]

    view = ft.View(route="/portrait-detail", controls=controls, padding=20)
    view.on_mount = lambda _: _load_portrait()
    return view
