# api/routers/query.py

from fastapi import APIRouter, Depends

from api.schemas.query import QueryRequest, QueryResponse
from api.deps import get_orchestrator
from core.orchestrator.query_orchestrator import QueryOrchestrator

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
def query(
    req: QueryRequest,
    orchestrator: QueryOrchestrator = Depends(get_orchestrator),
):
    result = orchestrator.run(
        wallet_id=req.wallet_id,
        app_id=req.app_id,
        session_id=req.session_id,
        intent=req.intent,
        user_query=req.query if req.query else None,
        intent_params=req.intent_params or {},
    )
    return QueryResponse(answer=result["answer"],meta=result["debug"])
