# datasource/base.py
# -*- coding: utf-8 -*-

from __future__ import annotations
from typing import Optional

from settings.config import Settings

from datasource.connections.sqlite_connection import SQLiteConnection
from datasource.connections.minio_connection import MinioConnection
from datasource.connections.weaviate_connection import WeaviateConnection

from datasource.objectstores.minio_store import MinIOStore
from datasource.vectorstores.weaviate_store import WeaviateStore

from datasource.sqlstores.identity_session_store import IdentitySessionStore
from datasource.sqlstores.memory_primary_store import MemoryPrimaryStore
from datasource.sqlstores.memory_contexts_store import MemoryContextsStore
from datasource.sqlstores.memory_metadata_store import MemoryMetadataStore


class Datasource:
    """
    RAG 中台统一 Datasource
    - 只负责连接与 store 聚合
    - 不包含任何业务逻辑
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()

        # ---------- SQLite ----------
        self.sqlite_conn = SQLiteConnection(
            db_path=self.settings.sqlite_path
        )
        self.identity_session = IdentitySessionStore(self.sqlite_conn)
        self.memory_primary = MemoryPrimaryStore(self.sqlite_conn)
        self.memory_contexts = MemoryContextsStore(self.sqlite_conn)
        self.memory_metadata = MemoryMetadataStore(self.sqlite_conn)

        # ---------- MinIO ----------
        self.minio_conn = MinioConnection(
            endpoint=self.settings.minio_endpoint,
            access_key=self.settings.minio_access_key,
            secret_key=self.settings.minio_secret_key,
            secure=self.settings.minio_secure,
        )
        self.minio = MinIOStore(self.minio_conn)

        # ⭐ 统一 bucket（来自 MINIO_BUCKET_KB）
        self.bucket = self.settings.minio_bucket
        # MinIOStore 内部已处理“已存在则跳过”
        self.minio.create_bucket(self.bucket)

        # ---------- Weaviate ----------
        self.weaviate_conn = None
        self.weaviate = None
        if self.settings.weaviate_enabled:
            self.weaviate_conn = WeaviateConnection(
                scheme=self.settings.weaviate_scheme,
                host=self.settings.weaviate_host,
                port=self.settings.weaviate_port,
                grpc_port=self.settings.weaviate_grpc_port,
                api_key=self.settings.weaviate_api_key,
            )
            self.weaviate = WeaviateStore(self.weaviate_conn)

    def close(self):
        # SQLite 是唯一需要显式 close 的资源
        try:
            if self.sqlite_conn:
                self.sqlite_conn.close()
        except Exception:
            pass

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
