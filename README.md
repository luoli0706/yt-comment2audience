# yt-comment2audience

一个基于 Flask + SQLite 的小型数据流水线示例项目（YouTube 评论 → 观众画像）：
- 数据采集：从 YouTube Data API v3 拉取评论线程并入库
- 数据清洗：从数据库读取原始数据，规格化后写入新表
- 数据画像：调用 DeepSeek（OpenAI-compatible）生成聚合层面的观众画像并写入 SQLite

A minimal Flask + SQLite pipeline demo (YouTube comments → audience portrait):
- Collection: fetch YouTube commentThreads and store raw data
- Cleaning: normalize raw data into a clean table
- Portrait: generate aggregated audience portrait via DeepSeek and store into SQLite

## 目录结构 / Structure

- [main.py](main.py): Flask 主进程入口（默认端口 5076）/ Flask entrypoint (default port 5076)
- [settings.json](settings.json): API 参数配置 / API settings
- [src/database/](src/database/): SQLite 相关代码 / SQLite helpers
- [src/data_analyse/](src/data_analyse/): 数据采集/清洗/画像脚本 / collection/cleaning/portrait scripts
- [data/](data/): 数据库文件目录（DB 文件不进 git）/ DB folder (DB file is git-ignored)

## 环境变量 / Environment

复制并填写：
- [.env.example](.env.example) → `.env`

Required:
- `YOUTUBE_API_KEY`
 - `AI_API_KEY`

说明：`.env` 不会被 git 追踪。
Note: `.env` is not tracked by git.

## settings.json 配置 / settings.json

两个主要参数：
- `youtube.order`: `hot`（默认，热门/相关度）或 `time`（按时间）
- `youtube.max_comments`: 最大评论线程数量（默认 50）

Two main params:
- `youtube.order`: `hot` (default, relevance) or `time` (latest)
- `youtube.max_comments`: cap of threads (default 50)

## 依赖与虚拟环境 / Dependencies & venv

本仓库“追踪 `.venv` 目录，但不追踪依赖本体（site-packages）与依赖清单（requirements.txt）”，
目的是避免把第三方依赖固定到仓库里。

This repo tracks the `.venv` folder, but does NOT track dependency payload (site-packages) nor `requirements.txt`.

在 Windows PowerShell 下建议：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install Flask python-dotenv requests
```

## 初始化数据库 / Init DB

```powershell
.\.venv\Scripts\python -m src.database.init_db
```

## 数据采集（默认静默入库）/ Collect (silent by default)

默认行为：不打印到 stdout，仅写入 SQLite。
Default: no stdout; store into SQLite.

```powershell
.\.venv\Scripts\python -m src.data_analyse.collect_youtube_comments "https://www.youtube.com/watch?v=MdTAJ1J2LeM"
```

如需输出 JSON：
To output JSON:

```powershell
.\.venv\Scripts\python -m src.data_analyse.collect_youtube_comments "https://www.youtube.com/watch?v=MdTAJ1J2LeM" --print
```

## 数据清洗 / Clean

```powershell
.\.venv\Scripts\python -m src.data_analyse.clean_data
```

## 运行 Flask / Run Flask

```powershell
.\.venv\Scripts\python main.py
```

Open:
- http://127.0.0.1:5076/
- http://127.0.0.1:5076/health

## 统一调度接口 / Unified Dispatch API

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

## 调度接口测试脚本 / Dispatch API Test Script

先启动服务：
```powershell
.\.venv\Scripts\python main.py
```

再运行测试脚本（会把结果打印到控制台，确保多语言字符正常显示）：
```powershell
.\.venv\Scripts\python scripts\test_dispatch_api.py
```

## 画像接口 / Portrait API

`POST /api/portrait`

两种用法：
1) 直接给 URL（服务端会自动：采集→清洗→画像）：

Request JSON:
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
.\.venv\Scripts\python scripts\test_portrait_api.py
```

## 自定义画像模板 / Custom Prompt Templates

通过编辑 prompt JSON 文件，并在 `.env` 中指定 `AI_PROMPT` 即可切换模板：

1) 在 [AI_PROMPT/](AI_PROMPT/) 下创建或复制一个 prompt JSON（必须包含字段：`system_prompt`）。
2) 在 `.env` 中设置：

```dotenv
AI_PROMPT="AI_PROMPT/your_custom_prompt.json"
```

默认推荐使用优化模板：
`AI_PROMPT="AI_PROMPT/AI_PROMPT_Optimized.zh.json"`

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE).
