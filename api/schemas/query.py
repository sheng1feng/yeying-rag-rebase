from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    wallet_id: str = Field(..., description="用户钱包 ID")
    app_id: str = Field(..., description="业务插件 ID，如 interviewer")
    session_id: str = Field(..., description="业务侧会话 ID")
    intent: str = Field(..., description="业务意图，如 generate_questions")
    query: str = Field(..., description="用户输入")
    intent_params: Optional[Dict[str, Any]] = Field(default_factory=dict)


class QueryResponse(BaseModel):
    answer: dict
