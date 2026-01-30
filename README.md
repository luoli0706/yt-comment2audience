# Image_Analyse

一个基于 Flask + SQLite 的小型数据流水线示例项目：
- 数据采集：从 YouTube Data API v3 拉取评论线程并入库
- 数据清洗：从数据库读取原始数据，规格化后写入新表
- 数据画像：当前占位（暂不实现）

A minimal Flask + SQLite data pipeline demo:
- Collection: fetch YouTube commentThreads and store raw data
- Cleaning: normalize raw data into a clean table
- Portrait: placeholder (not implemented yet)

## 目录结构 / Structure

- [main.py](main.py): Flask 主进程入口（默认端口 5076）/ Flask entrypoint (default port 5076)
- [settings.json](settings.json): API 参数配置 / API settings
- [src/database/](src/database/): SQLite 相关代码 / SQLite helpers
- [src/data_analyse/](src/data_analyse/): 数据采集/清洗/画像脚本 / collection/cleaning/portrait scripts
- [data/](data/): 数据库文件目录（DB 文件不进 git）/ DB folder (DB file is git-ignored)

## 环境变量 / Environment

复制并填写：
- [Image_Analyse/.env.example](Image_Analyse/.env.example) → `.env`

Required:
- `YOUTUBE_API_KEY`

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

## License

Licensed under the Apache License 2.0. See [LICENSE](LICENSE).
