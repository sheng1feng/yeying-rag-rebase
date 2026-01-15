# RAG 中台接口文档

基础说明：
- Base URL：由部署环境决定
- 统一返回 JSON
- `app_id` 对应 `plugins/<app_id>` 目录
- 前端控制台（如启用）：`/console/`

---

## Health

GET `/health`

响应示例：
```json
{"status": "ok"}
```

---

## 应用注册

POST `/app/register`

请求体：
```json
{"app_id": "interviewer"}
```

响应示例：
```json
{"app_id": "interviewer", "status": "ok"}
```

---

## 应用列表

GET `/app/list`

响应示例：
```json
[
  {"app_id": "interviewer", "status": "active", "has_plugin": true}
]
```

说明：
- `status` 来自 DB（`active/disabled/deleted/unregistered`）
- `has_plugin` 表示插件目录存在

---

## Intent 列表

GET `/app/{app_id}/intents`

响应示例：
```json
{
  "app_id": "interviewer",
  "intents": ["basic_questions", "generate_questions", "project_questions", "scenario_questions"],
  "exposed_intents": ["generate_questions"]
}
```

---

## Knowledge Base 列表

GET `/kb/list`

响应示例：
```json
[
  {
    "app_id": "interviewer",
    "kb_key": "jd_kb",
    "kb_type": "static_kb",
    "collection": "kb_interviewer_jd",
    "text_field": "content",
    "top_k": 3,
    "weight": 0.4,
    "use_allowed_apps_filter": false,
    "status": "active"
  }
]
```

---

## Knowledge Base 统计

GET `/kb/{app_id}/{kb_key}/stats`

响应示例：
```json
{
  "app_id": "interviewer",
  "kb_key": "jd_kb",
  "collection": "kb_interviewer_jd",
  "total_count": 1280,
  "chunk_count": 1280
}
```

---

## Knowledge Base 文档列表

GET `/kb/{app_id}/{kb_key}/documents?limit=20&offset=0`

响应示例：
```json
{
  "items": [
    {
      "id": "uuid",
      "properties": {"content": "..."},
      "created_at": "2024-09-04T10:11:12Z",
      "updated_at": "2024-09-04T11:11:12Z"
    }
  ],
  "total": 1280
}
```

---

## Knowledge Base 新增文档

POST `/kb/{app_id}/{kb_key}/documents`

请求体：
```json
{
  "id": "optional-uuid",
  "text": "optional text for embedding",
  "properties": {"content": "..."},
  "vector": null
}
```

响应示例：
```json
{
  "id": "uuid",
  "properties": {"content": "..."},
  "created_at": "2024-09-04T10:11:12Z",
  "updated_at": "2024-09-04T10:11:12Z"
}
```

---

## Knowledge Base 替换文档

PUT `/kb/{app_id}/{kb_key}/documents/{doc_id}`

请求体同新增文档。

---

## Knowledge Base 更新文档

PATCH `/kb/{app_id}/{kb_key}/documents/{doc_id}`

请求体：
```json
{
  "text": "optional text for embedding",
  "properties": {"content": "..."},
  "vector": null
}
```

---

## Knowledge Base 删除文档

DELETE `/kb/{app_id}/{kb_key}/documents/{doc_id}`

响应示例：
```json
{"status": "ok"}
```

---

## Store Health

GET `/stores/health`

响应示例：
```json
{
  "stores": [
    {"name": "sqlite", "status": "ok", "details": "SELECT 1 ok"},
    {"name": "minio", "status": "ok", "details": "list_buckets ok"},
    {"name": "weaviate", "status": "ok", "details": "client.is_ready ok"},
    {"name": "llm", "status": "configured", "details": "openai configured"}
  ]
}
```

---

## Ingestion Logs

GET `/ingestion/logs?limit=50&offset=0&app_id=interviewer&kb_key=jd_kb&status=success`

响应示例：
```json
{
  "items": [
    {
      "id": 1,
      "status": "success",
      "message": "jd rebuild finished",
      "app_id": "interviewer",
      "kb_key": "jd_kb",
      "collection": "kb_interviewer_jd",
      "meta_json": "{\"total\": 100}",
      "created_at": "2024-09-04 10:11:12"
    }
  ]
}
```

POST `/ingestion/logs`

请求体：
```json
{
  "status": "started",
  "message": "ingestion started",
  "app_id": "interviewer",
  "kb_key": "jd_kb",
  "collection": "kb_interviewer_jd",
  "meta": {"bucket": "company-jd"}
}
```

---

## 查询入口

POST `/query`

请求体：
```json
{
  "wallet_id": "user_123",
  "app_id": "interviewer",
  "session_id": "session_001",
  "intent": "generate_questions",
  "query": "我是后端工程师，准备面试，请给我一些问题。",
  "resume_url": "minio://bucket/memory/.../resume.json",
  "jd_url": "minio://bucket/memory/.../jd.json",
  "intent_params": {
    "basic_count": 2,
    "project_count": 1,
    "scenario_count": 1,
    "target_position": "后端工程师",
    "company": "示例公司"
  }
}
```

响应示例（interviewer）：
```json
{
  "answer": {
    "questions": ["..."],
    "meta": {"basic_count": 2, "project_count": 1, "scenario_count": 1}
  }
}
```

说明：
- `intent_params` 为插件自定义参数
- `resume_url/jd_url` 会透传给插件处理（如 interviewer 可在 pipeline 中读取 MinIO 内容）
- 若不提供 `query`，则插件可根据 `resume/jd` 补全

---

## 记忆写入

POST `/memory/push`

请求体：
```json
{
  "wallet_id": "user_123",
  "app_id": "interviewer",
  "session_id": "session_001",
  "filename": "history/session_history.json",
  "description": "可选说明",
  "summary_threshold": 20
}
```

响应示例：
```json
{
  "status": "ok",
  "messages_written": 2,
  "metas": [
    {
      "uid": "uuid",
      "memory_key": "sha256",
      "role": "user",
      "url": "memory/user_123/interviewer/session_001/history/session_history.json",
      "description": "history/session_history.json",
      "content_sha256": "..."
    }
  ]
}
```

说明：
- `filename` 对应 MinIO 路径：`memory/<wallet>/<app>/<session>/<filename>`
- 文件内容示例：
  ```json
  {"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
  ```
- `summary_threshold` 可覆盖插件配置中的 `memory.summary_threshold`
