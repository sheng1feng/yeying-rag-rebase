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

GET `/kb/{app_id}/{kb_key}/stats?wallet_id=optional`

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
说明：
- 当 KB 类型为 `user_upload` 且开启 `use_allowed_apps_filter` 时，会按 `app_id` 过滤
- 传入 `wallet_id` 时会进一步按用户过滤

---

## Knowledge Base 文档列表

GET `/kb/{app_id}/{kb_key}/documents?limit=20&offset=0&wallet_id=optional`

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
说明：
- 当 KB 类型为 `user_upload` 且开启 `use_allowed_apps_filter` 时，会按 `app_id` 过滤
- 传入 `wallet_id` 时会进一步按用户过滤

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

## 简历上传

POST `/resume/upload`

请求体：
```json
{
  "wallet_id": "user_123",
  "app_id": "interviewer",
  "resume_id": "optional-resume-id",
  "kb_key": "optional-user-upload-kb",
  "metadata": {"source": "biz"},
  "resume": {
    "name": "Alex Chen",
    "skills": ["python", "golang"],
    "text": "Backend engineer with 5 years of experience."
  }
}
```

响应示例：
```json
{
  "resume_id": "a8a3c9c0-2fd5-4d32-9c95-0f7c4c8763f4",
  "kb_key": "user_profile_kb",
  "collection": "kb_user_profile",
  "doc_id": "b367956c-41b6-444c-881c-ef8bd62bcc98",
  "source_url": "minio://bucket/kb/user_123/interviewer/resume/a8a3c9c0-2fd5-4d32-9c95-0f7c4c8763f4.json"
}
```

说明：
- 默认写入 app 下第一个 `user_upload` 类型 KB
- `resume_id` 用于后续 `/query` 调用

---

## JD 上传

POST `/{app_id}/jd/upload`

请求体：
```json
{
  "wallet_id": "user_123",
  "app_id": "interviewer",
  "jd_id": "optional-jd-id",
  "kb_key": "optional-user-upload-kb",
  "metadata": {"source": "biz"},
  "jd": {
    "title": "Backend Engineer",
    "requirements": ["Python", "Distributed Systems"],
    "text": "We are looking for a Backend Engineer..."
  }
}
```

响应示例：
```json
{
  "jd_id": "7a4f0b4e-9d9f-4b9f-9b25-8f7b5a92a8a1",
  "kb_key": "user_profile_kb",
  "collection": "kb_user_profile",
  "doc_id": "d2b5d3e4-1c1b-4d3f-8b5d-9e1f2a3b4c5d",
  "source_url": "minio://bucket/kb/user_123/interviewer/jd/7a4f0b4e-9d9f-4b9f-9b25-8f7b5a92a8a1.json"
}
```

说明：
- 默认写入 app 下第一个 `user_upload` 类型 KB
- `jd_id` 用于后续 `/query` 调用
- 路径中的 `app_id` 为必填，Body 的 `app_id` 可选

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
  "resume_id": "optional-resume-id",
  "jd_id": "optional-jd-id",
  "resume_url": "minio://bucket/memory/.../resume.json",
  "jd_url": "minio://bucket/memory/.../jd.json",
  "target": "后端工程师",
  "company": "示例公司",
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
- `resume_id` 为 `/resume/upload` 返回的简历 ID
- `jd_id` 为 `/{app_id}/jd/upload` 返回的 JD ID
- `target/company` 为快捷参数，内部会映射到 `intent_params.target_position/company`
- 当 `resume_id` 不存在时，会走默认路径生成通用问题（不报错）
- 当 `jd_id` 存在且可读取时，将跳过 JD 静态库检索
- 当 `jd_id` 缺失或无效时，仍走默认 JD 检索通路

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
