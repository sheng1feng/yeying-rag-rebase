# api/routers/query.py
# -*- coding: utf-8 -*-

import json
from typing import Any, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException

from api.schemas.query import QueryRequest, QueryResponse
from api.deps import get_deps
from api.routers.kb import _ensure_collection, _text_field_from_cfg

router = APIRouter()


def _resolve_user_upload_kb(deps, app_id: str) -> Tuple[Optional[str], Optional[dict]]:
    try:
        spec = deps.app_registry.get(app_id)
    except Exception:
        return None, None
    cfg = spec.config or {}
    kb_cfg = cfg.get("knowledge_bases", {}) or {}
    if not isinstance(kb_cfg, dict):
        return None, None
    kb_aliases = (cfg.get("prompt", {}) or {}).get("kb_aliases", {}) or {}
    alias_key = kb_aliases.get("resume_text")
    if alias_key and alias_key in kb_cfg:
        return str(alias_key), kb_cfg.get(alias_key) or {}
    for key, item in kb_cfg.items():
        if not isinstance(item, dict):
            continue
        if str(item.get("type") or "").strip() == "user_upload":
            return str(key), item
    return None, None


def _resolve_kb_aliases(deps, app_id: str) -> dict:
    try:
        spec = deps.app_registry.get(app_id)
    except Exception:
        return {}
    cfg = spec.config or {}
    kb_aliases = (cfg.get("prompt", {}) or {}).get("kb_aliases", {}) or {}
    if not isinstance(kb_aliases, dict):
        return {}
    return kb_aliases


def _extract_text_from_raw(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    if text[:1] not in ("{", "["):
        return text
    try:
        data = json.loads(text)
    except Exception:
        return text
    if isinstance(data, dict):
        for key in ("text", "content", "resume"):
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
        segments = data.get("segments")
        if isinstance(segments, list):
            return "\n".join(str(x) for x in segments if x)
        return text
    if isinstance(data, list):
        return "\n".join(str(x) for x in data if x)
    return text


@router.post("/query", response_model=QueryResponse)
def query(req: QueryRequest, deps=Depends(get_deps)):
    """
    /query 的职责：
    1) 查 DB：app 是否 active
    2) 生成 Identity（IdentityManager 内部也会查 DB）
    3) 校验 intent（仅 exposed intents）
    4) 按需加载 pipeline（不依赖内存预注册）
    5) 调用 pipeline.run(...)（业务预处理由插件完成）
    """
    try:
        # 0) DB 单一事实源：必须 active
        row = deps.datasource.app_store.get(req.app_id)
        if not row or row.get("status") != "active":
            raise HTTPException(status_code=400, detail=f"app_id={req.app_id} not active in DB")

        # 1) Identity（内部会再校验一次 active）
        identity = deps.identity_manager.resolve_identity(
            wallet_id=req.wallet_id,
            app_id=req.app_id,
            session_id=req.session_id,
        )

        # 2) intent 校验：只允许 exposed intents
        if not deps.app_registry.is_intent_exposed(req.app_id, req.intent):
            exposed = deps.app_registry.list_exposed_intents(req.app_id)
            raise HTTPException(
                status_code=400,
                detail=(
                    f"intent={req.intent} 未对外暴露（internal intent）。"
                    f"请使用对外 intent：{exposed}"
                ),
            )

        # 3) 按需加载 pipeline（不依赖 /app/register 预注册）
        pipeline = deps.pipeline_registry.get(req.app_id)
        pipeline.orchestrator = deps.orchestrator

        # 4) intent params passthrough（插件负责预处理）
        intent_params = dict(req.intent_params or {})
        if req.resume_url and "resume_url" not in intent_params:
            intent_params["resume_url"] = req.resume_url
        if req.jd_url and "jd_url" not in intent_params:
            intent_params["jd_url"] = req.jd_url
        if req.resume_id and "resume_id" not in intent_params:
            intent_params["resume_id"] = req.resume_id
        if req.jd_id and "jd_id" not in intent_params:
            intent_params["jd_id"] = req.jd_id
        if req.target and "target_position" not in intent_params:
            intent_params["target_position"] = req.target
        if req.company and "company" not in intent_params:
            intent_params["company"] = req.company

        if req.resume_id and "resume_text" not in intent_params and not req.resume_url:
            try:
                _, kb_cfg = _resolve_user_upload_kb(deps, req.app_id)
                if kb_cfg:
                    collection = _ensure_collection(deps, kb_cfg)
                    filters: dict[str, Any] = {"resume_id": req.resume_id, "wallet_id": req.wallet_id}
                    if kb_cfg.get("use_allowed_apps_filter"):
                        filters["allowed_apps"] = req.app_id
                    docs = deps.datasource.weaviate.fetch_objects(
                        collection,
                        limit=1,
                        offset=0,
                        filters=filters,
                    )
                    if docs:
                        props = docs[0].get("properties") or {}
                        text_field = _text_field_from_cfg(kb_cfg)
                        resume_text = (
                            props.get(text_field)
                            or props.get("text")
                            or props.get("content")
                            or ""
                        )
                        if not resume_text:
                            resume_text = _extract_text_from_raw(props.get("metadata_json") or "")
                        if resume_text:
                            intent_params["resume_text"] = resume_text
            except Exception:
                pass

        if req.jd_id and "jd_text" not in intent_params and not req.jd_url:
            try:
                _, kb_cfg = _resolve_user_upload_kb(deps, req.app_id)
                if kb_cfg:
                    collection = _ensure_collection(deps, kb_cfg)
                    filters: dict[str, Any] = {"jd_id": req.jd_id, "wallet_id": req.wallet_id}
                    if kb_cfg.get("use_allowed_apps_filter"):
                        filters["allowed_apps"] = req.app_id
                    docs = deps.datasource.weaviate.fetch_objects(
                        collection,
                        limit=1,
                        offset=0,
                        filters=filters,
                    )
                    if docs:
                        props = docs[0].get("properties") or {}
                        text_field = _text_field_from_cfg(kb_cfg)
                        jd_text = (
                            props.get(text_field)
                            or props.get("text")
                            or props.get("content")
                            or ""
                        )
                        if not jd_text:
                            jd_text = _extract_text_from_raw(props.get("metadata_json") or "")
                        if jd_text:
                            intent_params["jd_text"] = jd_text
                            kb_aliases = _resolve_kb_aliases(deps, req.app_id)
                            jd_kb_key = kb_aliases.get("jd_text")
                            if jd_kb_key:
                                exclude = list(intent_params.get("_kb_exclude") or [])
                                if jd_kb_key not in exclude:
                                    exclude.append(jd_kb_key)
                                intent_params["_kb_exclude"] = exclude
            except Exception:
                pass

        user_query = req.query or ""
        if not user_query and not intent_params:
            raise HTTPException(status_code=400, detail="query or intent_params is required")

        # 5) run
        result = pipeline.run(
            identity=identity,
            intent=req.intent,
            user_query=user_query,
            intent_params=intent_params,
        )

        return QueryResponse(answer=result)

    except HTTPException:
        raise
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
