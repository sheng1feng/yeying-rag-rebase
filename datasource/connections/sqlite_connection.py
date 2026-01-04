# rag/datasource/connections/sqlite_connection.py
# -*- coding: utf-8 -*-
"""
SQLiteConnection（核心版）
- 初始化 identity + memory 相关表
- 不包含业务表
"""

from __future__ import annotations
import os
import sqlite3
import threading
from pathlib import Path
from typing import Any, Iterable, Optional


CORE_DDL = r"""
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys=ON;

-- 身份层： wallet_id + app_id + session_id → memory_key
CREATE TABLE IF NOT EXISTS identity_session (
  memory_key   TEXT PRIMARY KEY,
  wallet_id    TEXT NOT NULL,
  app_id       TEXT NOT NULL,
  session_id   TEXT NOT NULL,
  created_at   TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at   TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(wallet_id, app_id, session_id)
);

CREATE INDEX IF NOT EXISTS idx_identity_session_wallet_app
  ON identity_session (wallet_id, app_id, created_at DESC);

-- 会话元信息（替代 mem_registry）
CREATE TABLE IF NOT EXISTS memory_metadata (
  memory_key    TEXT PRIMARY KEY,
  wallet_id     TEXT NOT NULL,
  app_id        TEXT NOT NULL,
  session_id    TEXT NOT NULL,
  params_json   TEXT,
  status        TEXT NOT NULL DEFAULT 'active',
  created_at    TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at    TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE(wallet_id, app_id, session_id)
);

CREATE INDEX IF NOT EXISTS idx_memory_metadata_wallet
  ON memory_metadata (wallet_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_memory_metadata_app
  ON memory_metadata (app_id, created_at DESC);

-- 主记忆摘要
CREATE TABLE IF NOT EXISTS memory_primary (
  memory_key          TEXT PRIMARY KEY,
  wallet_id           TEXT NOT NULL,
  app_id              TEXT NOT NULL,
  summary_url         TEXT,
  summary_version     INTEGER NOT NULL DEFAULT 0,
  recent_qa_count     INTEGER NOT NULL DEFAULT 0,
  total_qa_count      INTEGER NOT NULL DEFAULT 0,
  last_summary_index  INTEGER NOT NULL DEFAULT 0,
  last_summary_at     TEXT,
  created_at          TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_memory_primary_wallet
  ON memory_primary (wallet_id, created_at DESC);

-- 辅助记忆目录（存元信息，不存向量）
CREATE TABLE IF NOT EXISTS memory_contexts (
  uid            TEXT PRIMARY KEY,
  memory_key     TEXT NOT NULL,
  wallet_id      TEXT NOT NULL,
  app_id         TEXT NOT NULL,
  role           TEXT NOT NULL,
  url            TEXT NOT NULL,
  description    TEXT,
  content_sha256 TEXT NOT NULL UNIQUE,
  qa_count       INTEGER NOT NULL DEFAULT 0,
  is_summarized  INTEGER NOT NULL DEFAULT 0,
  summarized_at  TEXT,
  created_at     TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_memory_contexts_memory_created
  ON memory_contexts (memory_key, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_memory_contexts_wallet_created
  ON memory_contexts (wallet_id, created_at DESC);
"""


class SQLiteConnection:
    """SQLite 核心连接层（无业务，无逻辑删除）"""

    def __init__(self, db_path: Optional[str] = None) -> None:
        default_path = Path(os.getcwd()) / "db" / "rag.sqlite3"
        self.db_path = Path(db_path or os.getenv("RAG_DB_PATH", default_path))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(self.db_path.as_posix(), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()

        self._init_core_schema()

    def _init_core_schema(self) -> None:
        with self._lock, self._conn:
            self._conn.executescript(CORE_DDL)

    # ---------- 基础操作 ----------
    def execute(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        with self._lock, self._conn:
            return self._conn.execute(sql, params)

    def query_all(self, sql: str, params: Iterable[Any] = ()) -> list[dict]:
        with self._lock:
            cur = self._conn.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]

    def query_one(self, sql: str, params: Iterable[Any] = ()) -> Optional[dict]:
        with self._lock:
            cur = self._conn.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass
