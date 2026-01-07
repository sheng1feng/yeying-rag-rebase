# api/routers/query.py
# -*- coding: utf-8 -*-

from fastapi import APIRouter, Depends, HTTPException

from api.schemas.query import QueryRequest, QueryResponse
from api.deps import get_deps

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
def query(req: QueryRequest, deps=Depends(get_deps)):
    """
    /query 的职责：
    1) 查 DB：app 是否 active
    2) 生成 Identity（IdentityManager 内部也会查 DB）
    3) 校验 intent（仅 exposed intents）
    4) 按需加载 pipeline（不依赖内存预注册）
    5) 调用 pipeline.run(...)
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

        # 4) run
        result = pipeline.run(
            identity=identity,
            intent=req.intent,
            user_query=req.query,
            intent_params=req.intent_params or {},
        )

        return QueryResponse(answer=result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
