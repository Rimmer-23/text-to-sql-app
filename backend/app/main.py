from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import files, query, workspaces
from app.config import get_settings
from app.errors import register_error_handlers
from app.models.schemas import HealthResponse


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(title="Text-to-SQL API")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)

    app.include_router(workspaces.router, prefix="/api")
    app.include_router(files.router, prefix="/api")
    app.include_router(query.router, prefix="/api")

    @app.get("/api/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok")

    return app


app = create_app()
