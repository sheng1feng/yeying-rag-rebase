# rag/datasource/sqlstores/identity_session_store.py
# -*- coding: utf-8 -*-
"""
IdentitySessionStore
- 管理 wallet_id + app_id + session_id ↔ memory_key 的映射
"""

from __future__ import annotations
from typing import Optional, Dict, Any
from ..connections.sqlite_connection import SQLiteConnection

Row = Dict[str, Any]


class IdentitySessionStore:
    def __init__(self, conn: SQLiteConnection | None = None) -> None:
        self.conn = conn or SQLiteConnection()

    def upsert(self, memory_key: str, wallet_id: str, app_id: str, session_id: str) -> None:
        self.conn.execute(
            """
            INSERT INTO identity_session(memory_key, wallet_id, app_id, session_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(memory_key) DO UPDATE SET
              wallet_id = excluded.wallet_id,
              app_id = excluded.app_id,
              session_id = excluded.session_id,
              updated_at = datetime('now')
            """,
            (memory_key, wallet_id, app_id, session_id),
        )

    def get_by_memory_key(self, memory_key: str) -> Optional[Row]:
        return self.conn.query_one(
            "SELECT * FROM identity_session WHERE memory_key = ?",
            (memory_key,),
        )

    def get(self, wallet_id: str, app_id: str, session_id: str) -> Optional[Row]:
        return self.conn.query_one(
            """
            SELECT * FROM identity_session
             WHERE wallet_id = ? AND app_id = ? AND session_id = ?
            """,
            (wallet_id, app_id, session_id),
        )
