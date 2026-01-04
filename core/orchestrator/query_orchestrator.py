# core/orchestrator/query_orchestrator.py
# -*- coding: utf-8 -*-

from typing import Dict, Any, List, Optional

from identity.identity_manager import IdentityManager
from ..memory.memory_manager import MemoryManager
from ..kb.kb_manager import KnowledgeBaseManager
from ..prompt.prompt_builder import PromptBuilder
from ..llm.llm_client import LLMClient


class QueryOrchestrator:
    """
    中台 Query Orchestrator（稳定版）

    职责：
    - 串联 Identity / Memory / KB / Prompt / LLM
    - 统一 ContextBlock 结构
    - 不包含业务 if/else
    """

    def __init__(
        self,
        *,
        identity_manager: IdentityManager,
        memory_manager: MemoryManager,
        kb_manager: KnowledgeBaseManager,
        prompt_builder: PromptBuilder,
        llm_client: LLMClient,
        default_kb_top_k: int = 8,
    ):
        self.identity_manager = identity_manager
        self.memory_manager = memory_manager
        self.kb_manager = kb_manager
        self.prompt_builder = prompt_builder
        self.llm_client = llm_client
        self.default_kb_top_k = default_kb_top_k

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------
    def run(
        self,
        *,
        wallet_id: str,
        app_id: str,
        session_id: str,
        intent: str,
        user_query: str = None,
        intent_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        # 1) 身份解析
        identity = self.identity_manager.resolve_identity(
            wallet_id=wallet_id,
            app_id=app_id,
            session_id=session_id,
        )

        # 2) 读取 Memory（summary + auxiliary）
        memory_ctx = self.memory_manager.get_context(
            identity=identity,
            query=user_query,
        )

        context_blocks: List[Dict[str, Any]] = []

        # 2.1 summary → context
        if memory_ctx.get("summary"):
            context_blocks.append({
                "type": "memory_summary",
                "text": memory_ctx["summary"],
                "source": "memory",
            })

        # 2.2 auxiliary memory → context
        for item in memory_ctx.get("auxiliary", []):
            context_blocks.append({
                "type": "memory",
                "text": item.get("text"),
                "score": item.get("score", 0.0),
                "metadata": item,
            })

        # 3) KB 检索
        kb_blocks = self.kb_manager.search(
            identity=identity,
            query=user_query,
            global_top_k=self.default_kb_top_k,
        )

        # KBContextBlock 已经是统一结构，直接合并
        context_blocks.extend(kb_blocks)

        # 4) 构建 Prompt
        messages = self.prompt_builder.build(
            identity=identity,
            app_id=app_id,
            intent=intent,
            user_query=user_query,
            context_blocks=context_blocks,
            intent_params=intent_params or {},
        )

        # 5) 调用 LLM
        llm_result = self.llm_client.chat(messages)

        # 6) 返回
        return {
            "answer": llm_result.get("content") if isinstance(llm_result, dict) else llm_result,
            "debug": {
                "intent": intent,
                "memory_summary": bool(memory_ctx.get("summary")),
                "memory_hits": len(memory_ctx.get("auxiliary", [])),
                "kb_hits": len(kb_blocks or []),
            },
        }
