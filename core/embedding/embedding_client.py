# core/embedding/embedding_client.py
# -*- coding: utf-8 -*-

from typing import List, Iterable
from .model_router import EmbeddingModelRouter


class EmbeddingClient:
    """
    中台 Embedding Client
    Memory / KB 只能依赖这个类
    """

    def __init__(self):
        self.router = EmbeddingModelRouter()

    def embed(
        self,
        texts: Iterable[str],
        *,
        app_id: str | None = None,
    ) -> List[List[float]]:
        texts = list(texts)
        if not texts:
            return []

        provider = self.router.get_provider(app_id=app_id)
        return provider.embed(texts)

    def embed_one(self, text: str, *, app_id: str | None = None) -> List[float]:
        return self.embed([text], app_id=app_id)[0]
