# api/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import os

from api.routers.health import router as health_router
from api.routers.query import router as query_router
from api.app_register import router as app_register_router
from api.routers.memory import router as memory_router
from api.routers.kb import router as kb_router
from api.routers.stores import router as stores_router
from api.routers.ingestion import router as ingestion_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="RAG Service",
        version="2.1.0",
    )

    origins = [o.strip() for o in os.getenv("CORS_ALLOW_ORIGINS", "").split(",") if o.strip()]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(health_router)
    app.include_router(query_router)
    app.include_router(app_register_router)
    app.include_router(memory_router)
    app.include_router(kb_router)
    app.include_router(stores_router)
    app.include_router(ingestion_router)

    frontend_dir = Path(__file__).resolve().parents[2] / "frontend"
    if frontend_dir.exists():
        app.mount("/console", StaticFiles(directory=str(frontend_dir), html=True), name="console")

    return app


app = create_app()
