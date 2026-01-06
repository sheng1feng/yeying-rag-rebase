# rag/datasource/vectorstores/weaviate_store.py
# -*- coding: utf-8 -*-
"""
WeaviateStore（新版，无业务，无 schema）
核心原则：
- 不自动创建 collection
- 不写任何业务字段（memory_id / app）
- schema 全由 Memory/Kb 模块控制
"""

from __future__ import annotations
import json
from typing import List, Dict, Any, Optional

import weaviate
import weaviate.classes.config as wc
import weaviate.classes.query as wq
from weaviate.classes.query import Filter
from weaviate.exceptions import UnexpectedStatusCodeError

from datasource.connections.weaviate_connection import WeaviateConnection


def norm(name: str) -> str:
    """合法化 collection 名"""
    s = "".join(ch for ch in name if ch.isalnum()) or "C"
    if not s[0].isalpha():
        s = "C" + s
    return s[0].upper() + s[1:]


class WeaviateStore:
    """纯向量数据库客户端"""

    def __init__(self, conn: WeaviateConnection):
        self.conn = conn
        self.client: weaviate.WeaviateClient = conn.client

    # ---------------- Collection 管理 ----------------

    def create_collection(self, name: str, properties: List[wc.Property], embedding: bool = True):
        col = norm(name)
        vector_cfg = wc.Configure.Vectors.self_provided() if embedding else None

        self.client.collections.create(
            name=col,
            properties=properties,
            vector_config=vector_cfg,
        )

    def ensure_collection(self, name: str, properties: List[wc.Property]):
        """Memory/Kb 模块用，Datasource 不会调用"""
        col = norm(name)
        try:
            existing = self.client.collections.get(col)
            # 尝试补字段
            for p in properties:
                try:
                    existing.config.add_property(p)
                except:
                    pass
        except:
            # 创建
            self.client.collections.create(
                name=col,
                properties=properties,
                vector_config=wc.Configure.Vectors.self_provided(),
            )

    def list_collections(self) -> List[str]:
        cols = self.client.collections.list_all()
        result = []
        for c in cols:
            result.append(c if isinstance(c, str) else getattr(c, "name", str(c)))
        return result

    # ---------------- 写入 ----------------

    def upsert(
        self,
        collection: str,
        vector: List[float],
        properties: Dict[str, Any],
        object_id: Optional[str] = None,
    ) -> str:
        col = self.client.collections.get(norm(collection))

        if object_id:
            col.data.replace(uuid=object_id, properties=properties, vector=vector)
            return object_id

        res = col.data.insert(properties=properties, vector=vector)
        return str(res)

    def batch_upsert(
        self,
        collection: str,
        vectors: List[List[float]],
        properties_list: List[Dict[str, Any]],
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        col = self.client.collections.get(norm(collection))
        out: List[str] = []

        with col.batch.dynamic() as batch:
            for i, props in enumerate(properties_list):
                uid = ids[i] if ids else None
                vec = vectors[i]
                if uid:
                    batch.add_object(properties=props, vector=vec, uuid=uid)
                    out.append(uid)
                else:
                    r = batch.add_object(properties=props, vector=vec)
                    out.append(str(r))

        return out

    # ---------------- 搜索 ----------------

    def search(
        self,
        collection: str,
        query_vector: List[float],
        top_k: int = 8,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        col = self.client.collections.get(norm(collection))
        where = None

        if filters:
            clauses = [Filter.by_property(k).equal(v) for k, v in filters.items()]
            where = Filter.all_of(clauses)

        res = col.query.near_vector(
            near_vector=query_vector,
            limit=top_k,
            return_metadata=wq.MetadataQuery(distance=True),
            filters=where,
        )

        hits = []
        for obj in res.objects or []:
            props = obj.properties or {}
            dist = getattr(obj.metadata, "distance", None)
            score = 1 / (1 + dist) if dist is not None else 0.0
            hits.append({
                "properties": props,
                "metadata": {
                    "score": score,
                    "distance": dist,
                },
            })
        return hits

    # ---------------- 文本/HYBRID ----------------

    def hybrid(
        self,
        collection: str,
        text: str,
        vector: Optional[List[float]] = None,
        alpha: float = 0.5,
        top_k: int = 8,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        col = self.client.collections.get(norm(collection))

        where = None
        if filters:
            clauses = [Filter.by_property(k).equal(v) for k, v in filters.items()]
            where = Filter.all_of(clauses)

        res = col.query.hybrid(
            query=text,
            vector=vector,
            alpha=alpha,
            limit=top_k,
            filters=where,
            return_metadata=wq.MetadataQuery(score=True),
        )

        hits = []
        for obj in res.objects or []:
            props = obj.properties or {}
            hits.append({
                "properties": props,
                "metadata": {
                    "score": getattr(obj.metadata, "score", None),
                },
            })
        return hits

    # ---------------- 删除 ----------------

    def delete_by_id(self, collection: str, object_id: str):
        col = self.client.collections.get(norm(collection))
        col.data.delete_by_id(object_id)

    def delete_by_filter(self, collection: str, filters: Dict[str, Any]):
        col = self.client.collections.get(norm(collection))
        clauses = [Filter.by_property(k).equal(v) for k, v in filters.items()]
        where = Filter.all_of(clauses)
        col.data.delete_many(where=where)
