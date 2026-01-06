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
    注册一个业务插件（App）

    流程：
    1. 校验 plugins/<app_id> 是否存在
    2. 读取 config.yaml / intents.yaml / prompts
    3. 注册 AppSpec 到 AppRegistry
    4. 注册 pipeline 到 PipelineRegistry
    """
    app_id = req.app_id

    try:
        app_registry = deps.app_registry
        pipeline_registry = deps.pipeline_registry

        # # 1️⃣ 注册 App（加载 config / intents / prompts）
        # # 兼容不同命名方式
        # if hasattr(app_registry, "register_app"):
        #     app_spec = app_registry.register_app(app_id)
        # elif hasattr(app_registry, "register"):
        #     app_spec = app_registry.register(app_id)
        # elif hasattr(app_registry, "load_app"):
        #     app_spec = app_registry.load_app(app_id)
        # else:
        #     raise RuntimeError(
        #         "AppRegistry 缺少 register_app / register / load_app 方法"
        #     )
        #
        # # 2️⃣ 注册 Pipeline
        # # PipelineRegistry 只关心 app_id / pipeline.py
        # pipeline_registry.register_pipeline(app_spec, orchestrator=deps.orchestrator)
        app_spec = app_registry.register_app(app_id)
        pipeline_registry.register_pipeline(app_spec=app_spec,orchestrator=deps.orchestrator,)

        return AppRegisterResp(app_id=app_id, status="ok")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
