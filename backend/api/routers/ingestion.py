# api/routers/ingestion.py
# -*- coding: utf-8 -*-

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_deps
from api.schemas.ingestion import IngestionLogCreate, IngestionLogList, IngestionLogItem

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.get("/logs", response_model=IngestionLogList)
def list_logs(
    limit: int = 50,
    offset: int = 0,
    app_id: str | None = None,
    kb_key: str | None = None,
    status: str | None = None,
    deps=Depends(get_deps),
):
    rows = deps.datasource.ingestion_logs.list(
        limit=limit,
        offset=offset,
        app_id=app_id,
        kb_key=kb_key,
        status=status,
    )
    items = []
    for row in rows:
        items.append(
            IngestionLogItem(
                id=row.get("id"),
                status=row.get("status"),
                message=row.get("message"),
                app_id=row.get("app_id"),
                kb_key=row.get("kb_key"),
                collection=row.get("collection"),
                meta_json=row.get("meta_json"),
                created_at=row.get("created_at"),
            )
        )
    return IngestionLogList(items=items)


@router.post("/logs")
def create_log(req: IngestionLogCreate, deps=Depends(get_deps)):
    try:
        deps.datasource.ingestion_logs.create(
            status=req.status,
            message=req.message or "",
            app_id=req.app_id,
            kb_key=req.kb_key,
            collection=req.collection,
            meta=req.meta or {},
        )
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
