# api/main.py

from fastapi import FastAPI

from api.routers.health import router as health_router
from api.routers.query import router as query_router
from api.app_register import router as app_register_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Yeying RAG Service",
        version="2.1.0",
    )

    app.include_router(health_router)
    app.include_router(query_router)
    app.include_router(app_register_router)

    return app


app = create_app()
