from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MemoryPushRequest(BaseModel):
    wallet_id: str = Field(..., description="用户钱包 ID")
    app_id: str = Field(..., description="业务插件 ID")
    session_id: str = Field(..., description="业务侧会话 ID")
    filename: str = Field(..., description="业务上传的 session 历史文件名")
    description: Optional[str] = Field(None, description="文件说明（可选）")
    summary_threshold: Optional[int] = Field(None, description="摘要触发阈值（可选，覆盖插件配置）")


class MemoryPushResponse(BaseModel):
    status: str
    messages_written: int
    metas: List[Dict[str, Any]] = Field(default_factory=list)
