# api/routers/memory.py
# -*- coding: utf-8 -*-

from fastapi import APIRouter, Depends, HTTPException

from api.deps import get_deps
from api.schemas.memory import MemoryPushRequest, MemoryPushResponse

router = APIRouter(prefix="/memory", tags=["memory"])


@router.post("/push", response_model=MemoryPushResponse)
def push_memory(req: MemoryPushRequest, deps=Depends(get_deps)):
    try:
        row = deps.datasource.app_store.get(req.app_id)
        if not row or row.get("status") != "active":
            raise HTTPException(status_code=400, detail=f"app_id={req.app_id} not active in DB")

        identity = deps.identity_manager.resolve_identity(
            wallet_id=req.wallet_id,
            app_id=req.app_id,
            session_id=req.session_id,
        )

        summary_threshold = req.summary_threshold
        if summary_threshold is None:
            app_spec = deps.app_registry.get(req.app_id)
            memory_cfg = (app_spec.config or {}).get("memory", {}) or {}
            if "summary_threshold" in memory_cfg:
                try:
                    summary_threshold = int(memory_cfg.get("summary_threshold") or 0)
                except Exception:
                    summary_threshold = 0

        result = deps.memory_manager.push_session_file(
            identity=identity,
            filename=req.filename,
            description=req.description,
            summary_threshold=summary_threshold,
        )

        return MemoryPushResponse(**result)
    except HTTPException:
        raise
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
