# api/app_register.py
# -*- coding: utf-8 -*-

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List

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


class AppInfoResp(BaseModel):
    app_id: str
    status: str
    has_plugin: bool


class AppIntentsResp(BaseModel):
    app_id: str
    intents: List[str]
    exposed_intents: List[str]


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


@router.get("/list", response_model=List[AppInfoResp])
def list_apps(deps=Depends(get_deps)):
    """
    返回插件目录 + DB 注册状态的融合视图
    """
    rows = deps.datasource.app_store.list_all(status=None)
    db_map = {row.get("app_id"): row.get("status") for row in rows if row.get("app_id")}

    plugin_ids = set(deps.app_registry.list_apps())
    all_ids = sorted(set(db_map) | plugin_ids)

    return [
        AppInfoResp(
            app_id=app_id,
            status=db_map.get(app_id, "unregistered"),
            has_plugin=app_id in plugin_ids,
        )
        for app_id in all_ids
    ]


@router.get("/{app_id}/intents", response_model=AppIntentsResp)
def list_intents(app_id: str, deps=Depends(get_deps)):
    """
    返回插件 intents（含 exposed intents）
    """
    try:
        intents = deps.app_registry.list_intents(app_id)
        exposed = deps.app_registry.list_exposed_intents(app_id)
        return AppIntentsResp(app_id=app_id, intents=intents, exposed_intents=exposed)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
