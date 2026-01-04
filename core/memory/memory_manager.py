# core/memory/memory_manager.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import uuid
import hashlib
from typing import Any, Dict, Optional

from identity.models import Identity
from datasource.base import Datasource
from core.llm.llm_client import LLMClient
from core.embedding.embedding_client import EmbeddingClient

from core.memory.primary_memory import PrimaryMemory
from core.memory.auxiliary_memory import AuxiliaryMemory
from datasource.objectstores.path_builder import PathBuilder


class MemoryManager:
    """
    Memory 服务门面：
    - push：从 MinIO 读取业务端已写入的 session_history.json，然后写入主记忆(SQLite)+辅助记忆(Weaviate)
    - get_context：摘要 + 向量检索
    """

    def __init__(self, ds: Datasource, llm: LLMClient, embedder: EmbeddingClient):
        self.ds = ds
        self.llm = llm
        self.embedder = embedder

        self.primary = PrimaryMemory(ds=ds)
        self.aux = AuxiliaryMemory(ds=ds, embedding_client=embedder)

    def push_session_file(
        self,
        identity: Identity,
        filename: str,
        *,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        业务端约定：先把一个 session 的历史记录写进 MinIO，然后调用 RAG 的 push。
        RAG 按约定路径拼接读取：
          memory/{wallet_id}/{app_id}/{session_id}/{filename}
        """
        # 1) 拼接 url（key）
        url = PathBuilder.business_file(identity, filename)

        if not self.ds.minio:
            raise RuntimeError("MinIO is not enabled")

        bucket = self.ds.bucket
        raw = self.ds.minio.get_text(bucket=bucket, key=url)
        if not raw:
            raise FileNotFoundError(f"MinIO file not found: bucket={bucket}, key={url}")

        data = json.loads(raw)
        messages = data.get("messages", [])
        if not isinstance(messages, list):
            raise ValueError("Invalid session history json: messages must be a list")

        results = []

        for msg in messages:
            role = (msg.get("role") or "user").strip()
            content = (msg.get("content") or "").strip()
            if not content:
                continue

            uid = str(uuid.uuid4())
            sha = hashlib.sha256(content.encode("utf-8")).hexdigest()

            # A) SQLite：主记忆元信息（逐条）
            meta = self.primary.record_message(
                identity=identity,
                uid=uid,
                role=role,
                url=url,  # 每条消息指向同一个业务文件
                content_sha256=sha,
                description=description or filename,
            )

            # B) Weaviate：辅助记忆（逐条）
            self.aux.write(identity=identity, uid=uid, text=content, role=role)

            results.append(meta)

        # C) bump_qa：按本次写入消息条数递增（你已修正为 delta=len(messages) 的方向）
        self.ds.memory_primary.bump_qa(identity.memory_key, delta=len(results))

        # D) 尝试摘要（内部会读取未摘要条目 + 写入 summary）
        self.primary.maybe_summarize(identity, self.llm)

        return {
            "status": "ok",
            "messages_written": len(results),
            "metas": results,
        }

    def get_context(self, identity: Identity, query: str) -> Dict[str, Any]:
        summary = self.primary.get_summary(identity)
        aux_hits = self.aux.search(identity, query)
        return {"summary": summary, "auxiliary": aux_hits}
