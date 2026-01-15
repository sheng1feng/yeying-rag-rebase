from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    wallet_id: str = Field(..., description="用户钱包 ID")
    app_id: str = Field(..., description="业务插件 ID")
    session_id: str = Field(..., description="业务侧会话 ID")
    intent: str = Field(..., description="业务意图，如 generate_questions")
    query: Optional[str] = Field(None, description="用户输入（未提供简历时的兜底）")
    resume_url: Optional[str] = Field(None, description="可选：业务侧文件 URL（插件自定义用途）")
    jd_url: Optional[str] = Field(None, description="可选：业务侧文件 URL（插件自定义用途）")
    intent_params: Optional[Dict[str, Any]] = Field(default_factory=dict)


class QueryResponse(BaseModel):
    answer: dict
