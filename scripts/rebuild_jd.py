# scripts/rebuild_jd.py
# -*- coding: utf-8 -*-

from settings.config import Settings
from datasource.connections.minio_connection import MinioConnection
from datasource.objectstores.minio_store import MinIOStore

from datasource.connections.weaviate_connection import WeaviateConnection
from datasource.vectorstores.weaviate_store import WeaviateStore

from core.embedding.embedding_client import EmbeddingClient
from core.kb.ingestion.jd_rebuild import rebuild_jd_kb


def main():
    settings = Settings()

    # ---- MinIO（不经过 Datasource，因此不会初始化 sqlite）----
    minio = MinIOStore(MinioConnection(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    ))

    # ---- Weaviate ----
    if not settings.weaviate_enabled:
        raise RuntimeError("Weaviate is not enabled (settings.weaviate_enabled=false)")

    weaviate = WeaviateStore(WeaviateConnection(
        scheme=settings.weaviate_scheme,
        host=settings.weaviate_host,
        port=settings.weaviate_port,
        grpc_port=settings.weaviate_grpc_port,
        api_key=settings.weaviate_api_key,
    ))

    # ---- Embedding ----
    embedder = EmbeddingClient(settings)

    stats = rebuild_jd_kb(
        minio_store=minio,
        embedding_client=embedder,
        weaviate_store=weaviate,
        bucket="company-jd",
        collection="Kb_interviewer_jd",
        batch_size=8,
    )

    print("JD rebuild finished:", stats)


if __name__ == "__main__":
    main()
