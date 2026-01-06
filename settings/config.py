# settings/config.py
from pydantic import BaseModel
import os
from dotenv import load_dotenv
# ===== 只加载一次 .env =====
load_dotenv(override=True)

class Settings(BaseModel):
    # ---------- MinIO ----------
    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "")
    minio_secure: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"

    # ⭐ 唯一 bucket（与你的 .env 对齐）
    minio_bucket: str = os.getenv("MINIO_BUCKET_KB", "yeying-rag")

    # ---------- SQLite ----------
    sqlite_path: str = os.getenv("SQLITE_PATH", "./data/yeying_rag.sqlite3")

    # ---------- Weaviate ----------
    weaviate_api_key: str = os.getenv("WEAVIATE_API_KEY", "")
    # Weaviate
    weaviate_enabled: bool = os.getenv("WEAVIATE_ENABLED","False")
    weaviate_scheme: str =os.getenv("WEAVIATE_SCHEME","http")
    weaviate_host: str = os.getenv("WEAVIATE_HOST","47.101.3.196")
    weaviate_port: int = os.getenv("WEAVIATE_PORT","8080")
    weaviate_grpc_port: int = os.getenv("WEAVIATE_GRPC_PORT","50051")


    # ---------- OpenAI ----------
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_api_base: str = os.getenv("OPENAI_API_BASE", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "")

    embed_model: str = os.getenv("EMBED_MODEL", "")
    embed_api_key: str = os.getenv("EMBED_API_KEY", "")
    embed_api_base: str = os.getenv("EMBED_API_BASE", "")
    embed_dim: int = os.getenv("EMBEDDING_DIM", "")
    # ---------- Plugins ----------
    plugins_auto_register: str = os.getenv("PLUGINS_AUTO_REGISTER", "interviewer")
