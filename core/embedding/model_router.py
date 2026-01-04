# core/embedding/model_router.py
# -*- coding: utf-8 -*-

from .providers.openai import OpenAIEmbeddingProvider


class EmbeddingModelRouter:
    """
    后续可以按：
    - app_id
    - 数据类型（memory / kb / code）
    做路由
    """

    def get_provider(self, *, app_id: str | None = None):
        # v1：现在暂时统一用 OpenAI
        return OpenAIEmbeddingProvider()
