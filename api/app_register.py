# api/app_register.py
# -*- coding: utf-8 -*-

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.deps import get_deps

router = APIRouter(prefix="/app", tags=["app"])


# -------------------------
# Schemas
# -------------------------
class AppRegisterReq(BaseModel):
    app_id: str


class AppRegisterResp(BaseModel):
    app_id: str
    status: str = "ok"


# -------------------------
# API
# -------------------------
@router.post("/register", response_model=AppRegisterResp)
def register_app(req: AppRegisterReq, deps=Depends(get_deps)):
    """
    注册/启用一个业务插件（App）
    - 不再写入内存 registry
    - 注册事实只落 SQLite（app_registry 表）
    - 仍然会校验 plugins/<app_id> 是否可加载（防止写入垃圾 app_id）
    """
    app_id = req.app_id

    try:
        # 1) 校验插件目录与声明文件（按需加载，不落内存）
        deps.app_registry.register_app(app_id)

        # 2) 写 DB：active
        deps.datasource.app_store.upsert(app_id, status="active")

        return AppRegisterResp(app_id=app_id, status="ok")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))