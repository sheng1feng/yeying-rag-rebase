# datasource/objectstores/path_builder.py
# -*- coding: utf-8 -*-

from identity.models import Identity


class PathBuilder:
    """
    MinIO 路径生成器
    - business_file: 业务上传的 JSON （RAG 读取）
    - summary: RAG 自动生成摘要文件（primary_memory 写入）
    """

    # -----------------------------
    # 业务上传文件（RAG 读取）
    # -----------------------------
    @staticmethod
    def business_file(identity: Identity, filename: str) -> str:
        """
        业务已上传到 MinIO 的文件路径：
            memory/<wallet>/<app>/<session>/<filename>

        filename 由业务传入，例如：
            history/full_session.json
            outputs/grade.json
        """
        safe = filename.lstrip("/")
        return (
            f"memory/{identity.wallet_id}/"
            f"{identity.app_id}/"
            f"{identity.session_id}/"
            f"{safe}"
        )

    # -----------------------------
    # RAG 自动生成摘要文件
    # -----------------------------
    @staticmethod
    def summary(identity: Identity, version: int) -> str:
        """
        RAG 写入摘要文件：
            memory/<wallet>/<app>/<session>/summary/summary_<version>.json
        """
        return (
            f"memory/{identity.wallet_id}/"
            f"{identity.app_id}/"
            f"{identity.session_id}/summary/"
            f"summary_{version}.json"
        )