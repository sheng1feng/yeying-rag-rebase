# rag/datasource/sqlstores/app_registry_store.py
# -*- coding: utf-8 -*-

from __future__ import annotations
from typing import Optional, Dict, Any, List
from ..connections.sqlite_connection import SQLiteConnection

Row = Dict[str, Any]


class AppRegistryStore:
    """
    AppRegistryStore
    - 只负责 app_id 是否被注册（持久化）
    - 不存插件内容、不存 pipeline 信息
    """

    def __init__(self, conn: SQLiteConnection | None = None) -> None:
        self.conn = conn or SQLiteConnection()

    def upsert(self, app_id: str, status: str = "active") -> None:
        self.conn.execute(
            """
            INSERT INTO app_registry(app_id, status)
            VALUES (?, ?)
            ON CONFLICT(app_id) DO UPDATE SET
              status = excluded.status,
              updated_at = datetime('now')
            """,
            (app_id, status),
        )

    def get(self, app_id: str) -> Optional[Row]:
        return self.conn.query_one(
            "SELECT * FROM app_registry WHERE app_id = ?",
            (app_id,),
        )

    def list_all(self, status: Optional[str] = "active") -> List[Row]:
        if status:
            return self.conn.query_all(
                """
                SELECT * FROM app_registry
                 WHERE status = ?
                 ORDER BY created_at ASC
                """,
                (status,),
            )
        return self.conn.query_all(
            "SELECT * FROM app_registry ORDER BY created_at ASC"
        )

    def disable(self, app_id: str) -> None:
        self.conn.execute(
            """
            UPDATE app_registry
               SET status = 'disabled',
                   updated_at = datetime('now')
             WHERE app_id = ?
            """,
            (app_id,),
        )

    def delete(self, app_id: str) -> None:
        """
        逻辑删除（保留记录，便于审计）
        """
        self.conn.execute(
            """
            UPDATE app_registry
               SET status = 'deleted',
                   updated_at = datetime('now')
             WHERE app_id = ?
            """,
            (app_id,),
        )
