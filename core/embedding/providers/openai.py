# core/embedding/providers/openai.py
# -*- coding: utf-8 -*-

from typing import List
import openai
import os


class OpenAIEmbeddingProvider:
    def __init__(self, model: str = "text-embedding-3-large"):
        self.model = model
        openai.api_key = os.getenv("OPENAI_API_KEY")

    def embed(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        resp = openai.embeddings.create(
            model=self.model,
            input=texts,
        )
        return [item.embedding for item in resp.data]
