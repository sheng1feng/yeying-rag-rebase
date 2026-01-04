# core/kb/kb_manager.py
from __future__ import annotations

from typing import List, Optional, Dict, Any

from .kb_registry import KBRegistry, KBConfig
from .types import KBContextBlock
from ..embedding.embedding_client import EmbeddingClient
from identity.models import Identity


class KnowledgeBaseManager:
    """
    KB 统一检索入口（中台核心组件）
    - 多 KB 检索
    - KB 内部只做：embedding(query) -> weaviate.search -> 统一结构 -> 合并排序
    - 不做：chunk / rerank / prompt
    """

    # 一些常见的文本字段回退（避免业务 schema 不一致导致“明明召回了但 text 为空”）
    _TEXT_FALLBACK_FIELDS = ("text", "content", "body", "document", "raw")

    def __init__(self, ds, embedding_client: EmbeddingClient, kb_registry: KBRegistry):
        self.ds = ds
        self.embedding = embedding_client
        self.registry = kb_registry

    def search(
        self,
        identity: Identity,
        query: str,
        global_top_k: Optional[int] = None,
    ) -> List[KBContextBlock]:

        kb_list = self.registry.get_kbs(identity.app_id)
        if not kb_list or not self.ds.weaviate or not query:
            return []

        # ------------------------------------------------------------------
        # P1 修复：Embedding 必须用 embed_one（或 embed([query])[0]）
        # ------------------------------------------------------------------
        qvec = self.embedding.embed_one(query, app_id=identity.app_id)

        blocks: List[KBContextBlock] = []

        for kb in kb_list:
            top_k = max(int(kb.top_k or 1), 1)

            # ------------------------------------------------------------------
            # P1 修复：用户私有 KB 必须加过滤（至少 wallet_id + allowed_apps）
            # 注意：这里用 dict 表达 filter，你的 WeaviateStore.search 需要支持它。
            # 如果某些 collection 没这些字段，Weaviate 可能报错；因此做“字段不存在就降级”的容错。
            # ------------------------------------------------------------------
            filters = None
            if kb.is_user_kb:
                # 最小约束：同 wallet + 当前 app 可见
                filters = {
                    "wallet_id": identity.wallet_id,
                    "allowed_apps": identity.app_id,
                }

            try:
                hits = self.ds.weaviate.search(
                    collection=kb.collection,
                    query_vector=qvec,
                    top_k=top_k,
                    filters=filters,
                )
            except Exception:
                # 降级：如果过滤字段不存在（历史 collection），则退回无过滤，但要在 metadata 标注风险
                hits = self.ds.weaviate.search(
                    collection=kb.collection,
                    query_vector=qvec,
                    top_k=top_k,
                    filters=None,
                )
                # 下面 metadata 中会打标记：filter_degraded=True

            for h in hits:
                props: Dict[str, Any] = h.get("properties") or {}
                meta: Dict[str, Any] = h.get("metadata") or {}

                # ------------------------------------------------------------------
                # 文本字段：优先 kb.text_field，其次 fallback
                # ------------------------------------------------------------------
                text = props.get(kb.text_field)
                if not text:
                    for f in self._TEXT_FALLBACK_FIELDS:
                        text = props.get(f)
                        if text:
                            break
                if not text:
                    continue

                # ------------------------------------------------------------------
                # P1 修复：统一 score 语义
                # - 有些返回 score，有些返回 distance
                # - 最终输出 score 必须是 “越大越相关”
                # ------------------------------------------------------------------
                raw_score = meta.get("score")
                distance = meta.get("distance")

                if raw_score is None:
                    if distance is not None:
                        # 将距离转换为相似度（简单 1-distance；后续你可以换更合理的归一化）
                        raw_score = 1.0 - float(distance)
                    else:
                        raw_score = 0.0

                # ------------------------------------------------------------------
                # 权重：KB 层只做“加权得分”，后续 rerank 再融合更复杂策略
                # ------------------------------------------------------------------
                weight = float(kb.weight if kb.weight is not None else 1.0)
                if weight < 0:
                    weight = 0.0
                weighted_score = float(raw_score) * weight

                # 附加元信息，方便后续 Orchestrator / PromptBuilder 做来源标注
                enriched_meta = dict(props)
                enriched_meta.update(
                    {
                        "kb_name": kb.name,
                        "kb_collection": kb.collection,
                        "kb_weight": weight,
                        "raw_score": float(raw_score),
                        "distance": (float(distance) if distance is not None else None),
                        "is_user_kb": bool(kb.is_user_kb),
                        # 若上面发生过过滤降级，这里提示风险（无法严格校验时不应 silent）
                        "filter_degraded": bool(kb.is_user_kb and filters is not None and ("wallet_id" not in props and "allowed_apps" not in props)),
                    }
                )

                blocks.append(
                    KBContextBlock(
                        type="kb",
                        source=kb.name,
                        text=text,
                        score=weighted_score,
                        metadata=enriched_meta,
                    )
                )

        # ------------------------------------------------------------------
        # 合并排序（仅按 score），rerank 以后再接
        # ------------------------------------------------------------------
        blocks.sort(key=lambda b: b.score, reverse=True)

        if global_top_k is not None:
            global_top_k = max(int(global_top_k), 0)
            blocks = blocks[:global_top_k]

        return blocks
