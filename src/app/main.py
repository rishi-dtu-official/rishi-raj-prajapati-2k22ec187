"""FastAPI application entrypoint for Boostly."""

from fastapi import FastAPI

from .api.v1.router import api_router
from .jobs import register_scheduler


def create_app() -> FastAPI:
    """Instantiate and configure the FastAPI application."""
    app = FastAPI(title="Boostly API", version="0.1.0")
    app.include_router(api_router, prefix="/api/v1")
    register_scheduler(app)
    return app


app = create_app()
