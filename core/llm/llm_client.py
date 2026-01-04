# core/llm/llm_client.py
# -*- coding: utf-8 -*-

from typing import List, Dict, Any
from .model_registry import ModelRegistry


class LLMClient:
    """
    中台 LLM Client
    Orchestrator 只能依赖这个类
    """

    def __init__(self):
        self.registry = ModelRegistry()

    def chat(
        self,
        messages: List[Dict[str, str]],
        *,
        app_id: str | None = None,
        intent: str | None = None,
    ) -> Dict[str, Any]:
        provider = self.registry.get_provider(app_id=app_id, intent=intent)
        return provider.chat(messages)
