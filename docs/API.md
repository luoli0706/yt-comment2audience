# API 文档（yt-comment2audience）

基础 URL（默认）：`http://127.0.0.1:5076`

> 说明：所有接口均返回 JSON，字符集 UTF-8。

## 1. 统一调度接口

### POST /api/pipeline

**用途**：采集评论 → 清洗 → 返回清洗结果（并写入数据库）。

**请求体**：
```json
{
  "url": "https://www.youtube.com/watch?v=MdTAJ1J2LeM",
  "order": "hot",
  "max_comments": 20
}
```

**响应体（示例）**：
```json
{
  "ok": true,
  "run_id": 10,
  "video_id": "MdTAJ1J2LeM",
  "raw_count": 20,
  "clean_count": 20,
  "result_count": 20,
  "result": [
    {"comment_id": "...", "text": "..."}
  ]
}
```

---

## 2. 画像生成接口

### POST /api/portrait

**用途**：
- 传 `url` 时：采集 → 清洗 → 画像 → 返回
- 传 `run_id` 时：基于已有 run 生成画像 → 返回

**请求体（url 方式）**：
```json
{
  "url": "https://www.youtube.com/watch?v=MdTAJ1J2LeM",
  "order": "hot",
  "max_comments": 20,
  "overwrite": true
}
```

**请求体（run_id 方式）**：
```json
{
  "run_id": 10,
  "overwrite": true
}
```

**响应体（示例）**：
```json
{
  "ok": true,
  "run_id": 10,
  "video_id": "MdTAJ1J2LeM",
  "portrait": {"summary": "..."},
  "parse_ok": true,
  "prompt_name": "AI_PROMPT_Final_zh_v3",
  "prompt_version": 3,
  "provider": "deepseek",
  "model": "deepseek-chat",
  "cached": false,
  "portrait_raw": "..."
}
```

---

## 3. 画像查询与删除

### POST /api/portrait/query

**用途**：根据 `run_id` 查询画像详情。

**请求体**：
```json
{ "run_id": 10 }
```

**响应体（示例）**：
```json
{
  "ok": true,
  "run_id": 10,
  "portrait": {"summary": "..."},
  "parse_ok": true,
  "video_url": "https://www.youtube.com/watch?v=...",
  "video_title": "...",
  "channel_title": "...",
  "created_at": "2026-01-31T10:00:00Z"
}
```

### POST /api/portrait/delete

**用途**：删除指定 `run_id` 的画像记录。

**请求体**：
```json
{ "run_id": 10 }
```

---

## 4. 画像总表

### GET /api/portraits

**用途**：返回画像总表（简要信息，用于列表展示）。

**响应体（示例）**：
```json
{
  "ok": true,
  "count": 2,
  "items": [
    {
      "run_id": 10,
      "video_url": "https://www.youtube.com/watch?v=...",
      "video_title": "...",
      "channel_title": "...",
      "portrait_created_at": "2026-01-31T10:00:00Z",
      "parse_ok": true
    }
  ]
}
```

---

## 5. 原始数据总表与详情

### GET /api/collections

**用途**：返回原始采集总表（简要信息）。

**响应体（示例）**：
```json
{
  "ok": true,
  "count": 2,
  "items": [
    {
      "run_id": 10,
      "video_url": "https://www.youtube.com/watch?v=...",
      "video_title": "...",
      "channel_title": "...",
      "collected_at": "2026-01-31T10:00:00Z",
      "raw_count": 20,
      "clean_count": 20
    }
  ]
}
```

### POST /api/collections/detail

**用途**：根据 `run_id` 查询原始采集的详细信息。

**请求体**：
```json
{ "run_id": 10 }
```

### POST /api/collections/delete

**用途**：删除指定 `run_id` 的采集记录（级联删除 raw/clean/portrait）。

**请求体**：
```json
{ "run_id": 10 }
```
