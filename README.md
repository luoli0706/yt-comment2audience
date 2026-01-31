# 📊 yt-comment2audience

<div align="center">

**YouTube 评论 → 观众画像 的 Flask + SQLite 数据流水线示例**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python)](https://python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.x-000000?logo=flask)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/SQLite-3.x-003B57?logo=sqlite)](https://sqlite.org/)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [API](#-api) • [Frontend](#-frontend-flet)

</div>

---

## 📖 项目简介

一个基于 Flask + SQLite 的小型数据流水线示例项目（YouTube 评论 → 观众画像）：
- 数据采集：从 YouTube Data API v3 拉取评论线程并入库
- 数据清洗：从数据库读取原始数据，规格化后写入新表
- 数据画像：调用 DeepSeek（OpenAI-compatible）生成聚合层面的观众画像并写入 SQLite

A minimal Flask + SQLite pipeline demo (YouTube comments → audience portrait):
- Collection: fetch YouTube commentThreads and store raw data
- Cleaning: normalize raw data into a clean table
- Portrait: generate aggregated audience portrait via DeepSeek and store into SQLite

---

## ✨ 功能特性

- 🔎 **一键调度**：采集 → 清洗 → 画像统一接口
- 🧹 **清洗入库**：原始表 + 规格化表
- 🤖 **画像生成**：DeepSeek 输出结构化受众画像
- 🧩 **模板可切换**：prompt JSON 可自定义
- 🖥️ **可视化前端**：Flet 总表/详情页 + 图表

---

## 🗂️ 目录结构

- [main.py](main.py): Flask 主进程入口（默认端口 5076）
- [settings.json](settings.json): API 参数配置
- [src/database/](src/database/): SQLite 相关代码
- [src/data_analyse/](src/data_analyse/): 数据采集/清洗/画像脚本
- [data/](data/): 数据库文件目录（DB 文件不进 git）

---

## 🔐 环境变量

复制并填写：
- [.env.example](.env.example) → `.env`

Required:
- `YOUTUBE_API_KEY`
- `AI_API_KEY`
- `YOUTUBE_API_VIDEOS_URL`（用于获取视频标题/频道信息）

说明：`.env` 不会被 git 追踪。
Note: `.env` is not tracked by git.

---

## ⚙️ settings.json

两个主要参数：
- `youtube.order`: `hot`（默认，热门/相关度）或 `time`（按时间）
- `youtube.max_comments`: 最大评论线程数量（默认 50）

Two main params:
- `youtube.order`: `hot` (default, relevance) or `time` (latest)
- `youtube.max_comments`: cap of threads (default 50)

---

## 🚀 快速开始

### 1) 依赖与虚拟环境

本仓库“追踪 `.venv` 目录，但不追踪依赖本体（site-packages）与依赖清单（requirements.txt）”，
目的是避免把第三方依赖固定到仓库里。

This repo tracks the `.venv` folder, but does NOT track dependency payload (site-packages) nor `requirements.txt`.

在 Windows PowerShell 下建议：

```powershell
python -m venv .venv
\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2) 初始化数据库

```powershell
\.venv\Scripts\python -m src.database.init_db
```

### 3) 数据采集（默认静默入库）

默认行为：不打印到 stdout，仅写入 SQLite。
Default: no stdout; store into SQLite.

```powershell
\.venv\Scripts\python -m src.data_analyse.collect_youtube_comments "https://www.youtube.com/watch?v=MdTAJ1J2LeM"
```

如需输出 JSON：
To output JSON:

```powershell
\.venv\Scripts\python -m src.data_analyse.collect_youtube_comments "https://www.youtube.com/watch?v=MdTAJ1J2LeM" --print
```

### 4) 数据清洗

```powershell
\.venv\Scripts\python -m src.data_analyse.clean_data
```

### 5) 运行 Flask

```powershell
\.venv\Scripts\python main.py
```

Open:
- http://127.0.0.1:5076/
- http://127.0.0.1:5076/health

---

## 🔌 API

### 统一调度接口 / Unified Dispatch

`POST /api/pipeline`

Request JSON:
```json
{
	"url": "https://www.youtube.com/watch?v=MdTAJ1J2LeM",
	"order": "hot",
	"max_comments": 10
}
```

Response JSON:
- `result`: 规格化后的评论列表 / normalized comments
- UTF-8 输出，支持中文/日文/韩文/英文等字符

测试脚本（先启动服务，再运行）：
```powershell
\.venv\Scripts\python scripts\test_dispatch_api.py
```

### 画像接口 / Portrait

`POST /api/portrait`

两种用法：
1) 直接给 URL（服务端会自动：采集→清洗→画像）：

```json
{
	"url": "https://www.youtube.com/watch?v=MdTAJ1J2LeM",
	"order": "hot",
	"max_comments": 20,
	"overwrite": true
}
```

2) 给已有的 `run_id`（只做画像，复用已清洗数据）：

```json
{
	"run_id": 3,
	"overwrite": true
}
```

Response JSON:
- `portrait`: DeepSeek 返回并解析后的 JSON（若解析失败则可能为 null）
- `parse_ok`: 是否成功解析为 JSON
- `portrait_raw`: 原始输出（过长会截断）

测试脚本（先启动服务，再运行）：
```powershell
\.venv\Scripts\python scripts\test_portrait_api.py
```

### API 文档

详见 [docs/API.md](docs/API.md)

---

## 🧩 自定义画像模板

通过编辑 prompt JSON 文件，并在 `.env` 中指定 `AI_PROMPT` 即可切换模板：

1) 在 [AI_PROMPT/](AI_PROMPT/) 下创建或复制一个 prompt JSON（必须包含字段：`system_prompt`）。
2) 在 `.env` 中设置：

```dotenv
AI_PROMPT="AI_PROMPT/your_custom_prompt.json"
```

默认推荐使用优化模板：
`AI_PROMPT="AI_PROMPT/AI_PROMPT_Optimized.zh.json"`

---

## 🖥️ Frontend (Flet)

在 [frontend/](frontend/) 提供一个基础 Flet 图形界面：
- 主页面包含两个路由按钮：查询画像 / 画像生成
- 查询画像页：画像总表、原始数据总表（支持拖动横向滚动）
- 画像详情页：左侧文本摘要 + 右侧图表（自动刷新）
- 原始数据详情页：详情面板 + JSON 视图（自动刷新）
- 服务端地址通过 `frontend/.env` 中的 `SERVER_URL` 配置（默认 http://127.0.0.1:5076）

运行示例（需先安装 flet）：
```powershell
\.venv\Scripts\python frontend\app.py
```

---

## 📄 License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE).

---

<div align="center">

**⭐ 如果这个项目对你有帮助，请给个 Star！**

</div>
