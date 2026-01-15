# api/routers/kb.py
# -*- coding: utf-8 -*-

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_deps
from api.schemas.kb import (
    KBInfo,
    KBStats,
    KBDocument,
    KBDocumentList,
    KBDocumentUpsert,
    KBDocumentUpdate,
)

router = APIRouter(prefix="/kb", tags=["knowledge-base"])


def _resolve_kb_config(deps, app_id: str, kb_key: str) -> dict:
    spec = deps.app_registry.get(app_id)
    kb_cfg = (spec.config or {}).get("knowledge_bases", {}) or {}
    if not isinstance(kb_cfg, dict) or kb_key not in kb_cfg:
        raise KeyError(f"kb_key={kb_key} not found for app_id={app_id}")
    cfg = kb_cfg[kb_key] or {}
    if not isinstance(cfg, dict):
        raise KeyError(f"kb_key={kb_key} config invalid for app_id={app_id}")
    return cfg


def _text_field_from_cfg(cfg: dict) -> str:
    return str(cfg.get("text_field") or "text").strip() or "text"


@router.get("/list", response_model=list[KBInfo])
def list_kbs(deps=Depends(get_deps)):
    try:
        app_status_map = {
            row.get("app_id"): row.get("status")
            for row in deps.datasource.app_store.list_all(status=None)
            if row.get("app_id")
        }

        out: list[KBInfo] = []
        for app_id in deps.app_registry.list_apps():
            try:
                spec = deps.app_registry.get(app_id)
            except Exception:
                continue
            kb_cfg = (spec.config or {}).get("knowledge_bases", {}) or {}
            if not isinstance(kb_cfg, dict):
                continue
            for kb_key, cfg in kb_cfg.items():
                if not isinstance(cfg, dict):
                    continue
                out.append(
                    KBInfo(
                        app_id=app_id,
                        kb_key=str(kb_key),
                        kb_type=str(cfg.get("type") or ""),
                        collection=str(cfg.get("collection") or ""),
                        text_field=_text_field_from_cfg(cfg),
                        top_k=int(cfg.get("top_k") or 0),
                        weight=float(cfg.get("weight") or 0.0),
                        use_allowed_apps_filter=bool(cfg.get("use_allowed_apps_filter")),
                        status=app_status_map.get(app_id),
                    )
                )
        return out
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{app_id}/{kb_key}/stats", response_model=KBStats)
def kb_stats(app_id: str, kb_key: str, deps=Depends(get_deps)):
    try:
        cfg = _resolve_kb_config(deps, app_id, kb_key)
        collection = str(cfg.get("collection") or "")
        if not collection:
            raise ValueError("collection is empty")
        if not deps.datasource.weaviate:
            raise RuntimeError("Weaviate is not enabled")
        total = deps.datasource.weaviate.count(collection)
        return KBStats(
            app_id=app_id,
            kb_key=kb_key,
            collection=collection,
            total_count=total,
            chunk_count=total,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{app_id}/{kb_key}/documents", response_model=KBDocumentList)
def list_documents(app_id: str, kb_key: str, limit: int = 20, offset: int = 0, deps=Depends(get_deps)):
    try:
        cfg = _resolve_kb_config(deps, app_id, kb_key)
        collection = str(cfg.get("collection") or "")
        if not collection:
            raise ValueError("collection is empty")
        if not deps.datasource.weaviate:
            raise RuntimeError("Weaviate is not enabled")
        items = deps.datasource.weaviate.fetch_objects(collection, limit=limit, offset=offset)
        normalized = []
        for item in items:
            normalized.append(
                KBDocument(
                    id=item.get("id") or "",
                    properties=item.get("properties") or {},
                    created_at=_to_iso(item.get("created_at")),
                    updated_at=_to_iso(item.get("updated_at")),
                )
            )
        total = deps.datasource.weaviate.count(collection)
        return KBDocumentList(items=normalized, total=total)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def _to_iso(val) -> str | None:
    if not val:
        return None
    try:
        return val.isoformat()
    except Exception:
        return str(val)


def _prepare_properties(cfg: dict, payload: dict) -> dict:
    props = dict(payload or {})
    text_field = _text_field_from_cfg(cfg)
    text_val = props.get(text_field)
    if text_val is None:
        return props
    props[text_field] = str(text_val)
    return props


def _resolve_text_and_vector(cfg: dict, req, deps, app_id: str) -> tuple[dict, list | None]:
    props = _prepare_properties(cfg, req.properties)
    text_field = _text_field_from_cfg(cfg)

    text = req.text
    if not text and props.get(text_field):
        text = props.get(text_field)
    if text:
        props[text_field] = text

    vector = req.vector
    if vector is None and text:
        vector = deps.embedding_client.embed_one(str(text), app_id=app_id)
    return props, vector


@router.post("/{app_id}/{kb_key}/documents", response_model=KBDocument)
def create_document(app_id: str, kb_key: str, req: KBDocumentUpsert, deps=Depends(get_deps)):
    try:
        cfg = _resolve_kb_config(deps, app_id, kb_key)
        collection = str(cfg.get("collection") or "")
        if not collection:
            raise ValueError("collection is empty")
        if not deps.datasource.weaviate:
            raise RuntimeError("Weaviate is not enabled")

        props, vector = _resolve_text_and_vector(cfg, req, deps, app_id)
        if vector is None:
            raise ValueError("vector is required (text or vector must be provided)")

        obj_id = deps.datasource.weaviate.upsert(
            collection=collection,
            vector=vector,
            properties=props,
            object_id=req.id,
        )
        obj = deps.datasource.weaviate.fetch_object_by_id(collection, obj_id)
        if not obj:
            return KBDocument(id=obj_id, properties=props)
        return KBDocument(
            id=obj.get("id") or obj_id,
            properties=obj.get("properties") or props,
            created_at=_to_iso(obj.get("created_at")),
            updated_at=_to_iso(obj.get("updated_at")),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{app_id}/{kb_key}/documents/{doc_id}", response_model=KBDocument)
def replace_document(app_id: str, kb_key: str, doc_id: str, req: KBDocumentUpsert, deps=Depends(get_deps)):
    try:
        cfg = _resolve_kb_config(deps, app_id, kb_key)
        collection = str(cfg.get("collection") or "")
        if not collection:
            raise ValueError("collection is empty")
        if not deps.datasource.weaviate:
            raise RuntimeError("Weaviate is not enabled")

        props, vector = _resolve_text_and_vector(cfg, req, deps, app_id)
        if vector is None:
            raise ValueError("vector is required (text or vector must be provided)")

        deps.datasource.weaviate.upsert(
            collection=collection,
            vector=vector,
            properties=props,
            object_id=doc_id,
        )
        obj = deps.datasource.weaviate.fetch_object_by_id(collection, doc_id)
        if not obj:
            return KBDocument(id=doc_id, properties=props)
        return KBDocument(
            id=obj.get("id") or doc_id,
            properties=obj.get("properties") or props,
            created_at=_to_iso(obj.get("created_at")),
            updated_at=_to_iso(obj.get("updated_at")),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{app_id}/{kb_key}/documents/{doc_id}", response_model=KBDocument)
def update_document(app_id: str, kb_key: str, doc_id: str, req: KBDocumentUpdate, deps=Depends(get_deps)):
    try:
        cfg = _resolve_kb_config(deps, app_id, kb_key)
        collection = str(cfg.get("collection") or "")
        if not collection:
            raise ValueError("collection is empty")
        if not deps.datasource.weaviate:
            raise RuntimeError("Weaviate is not enabled")

        props, vector = _resolve_text_and_vector(cfg, req, deps, app_id)
        deps.datasource.weaviate.update(
            collection=collection,
            object_id=doc_id,
            properties=props if props else None,
            vector=vector,
        )
        obj = deps.datasource.weaviate.fetch_object_by_id(collection, doc_id)
        if not obj:
            return KBDocument(id=doc_id, properties=props or {})
        return KBDocument(
            id=obj.get("id") or doc_id,
            properties=obj.get("properties") or props,
            created_at=_to_iso(obj.get("created_at")),
            updated_at=_to_iso(obj.get("updated_at")),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{app_id}/{kb_key}/documents/{doc_id}")
def delete_document(app_id: str, kb_key: str, doc_id: str, deps=Depends(get_deps)):
    try:
        cfg = _resolve_kb_config(deps, app_id, kb_key)
        collection = str(cfg.get("collection") or "")
        if not collection:
            raise ValueError("collection is empty")
        if not deps.datasource.weaviate:
            raise RuntimeError("Weaviate is not enabled")
        deps.datasource.weaviate.delete_by_id(collection, doc_id)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
