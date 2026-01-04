# api/routers/query.py
# -*- coding: utf-8 -*-

from fastapi import APIRouter, Depends, HTTPException

from api.schemas.query import QueryRequest, QueryResponse
from api.deps import get_deps

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
def query(req: QueryRequest, deps=Depends(get_deps)):
    """
    /query 的唯一职责：
    1. 生成 Identity
    2. 校验 intent（仅允许 exposed intents）
    3. 找到对应 app 的 pipeline
    4. 把 orchestrator 注入 pipeline
    5. 调用 pipeline.run(...)
    """
    try:
        # 1️⃣ 生成 Identity（统一入口）
        identity = deps.identity_manager.resolve_identity(
            wallet_id=req.wallet_id,
            app_id=req.app_id,
            session_id=req.session_id,
        )

        # 2️⃣ 确保 app 已加载到 AppRegistry（以便做 exposed intent 校验）
        # 说明：/app/register 会做更完整的注册（含 pipeline 注册），这里仅保证 app_spec 可用
        if hasattr(deps, "app_registry") and deps.app_registry is not None:
            if not deps.app_registry.is_registered(req.app_id):
                deps.app_registry.register_app(req.app_id)

        # 3️⃣ intent 校验：只允许 exposed intents（避免对子 intent 直接调用）
        if hasattr(deps, "app_registry") and deps.app_registry is not None:
            if not deps.app_registry.is_intent_exposed(req.app_id, req.intent):
                exposed = deps.app_registry.list_exposed_intents(req.app_id)
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"intent={req.intent} 未对外暴露（internal intent）。"
                        f"请使用对外 intent：{exposed}"
                    ),
                )

        # 4️⃣ 获取 pipeline
        pipeline = deps.pipeline_registry.get(req.app_id)
        if pipeline is None:
            raise HTTPException(
                status_code=400,
                detail=f"app_id={req.app_id} 未注册 pipeline，请先调用 /app/register",
            )

        # 5️⃣ 注入 orchestrator（运行期）
        pipeline.orchestrator = deps.orchestrator

        # 6️⃣ 调用 pipeline
        result = pipeline.run(
            identity=identity,
            intent=req.intent,
            user_query=req.query,
            intent_params=req.intent_params or {},
        )

        # 7️⃣ 返回（保持 QueryResponse 兼容）
        return QueryResponse(
            answer=result,
            meta={},
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
