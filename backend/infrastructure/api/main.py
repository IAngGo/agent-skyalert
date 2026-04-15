"""
FastAPI application factory for SkyAlert.

Creates the app, registers exception handlers, and includes all routers.
This is the entry point for uvicorn:
    uvicorn backend.infrastructure.api.main:app --reload
"""

from fastapi import FastAPI

from backend.application.exceptions import SkyAlertError
from backend.infrastructure.api.exception_handlers import (
    skyalert_exception_handler,
    value_error_handler,
)
from backend.infrastructure.api.routers import alerts, searches, users


def create_app() -> FastAPI:
    """
    Construct and configure the FastAPI application.

    Returns:
        A fully configured FastAPI instance.
    """
    app = FastAPI(
        title="SkyAlert API",
        description="Flight price monitoring — get notified when prices drop.",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Exception handlers
    app.add_exception_handler(SkyAlertError, skyalert_exception_handler)
    app.add_exception_handler(ValueError, value_error_handler)

    # Routers
    app.include_router(users.router)
    app.include_router(searches.router)
    app.include_router(alerts.router)

    @app.get("/health", tags=["meta"])
    def health() -> dict:
        """
        Health check endpoint.

        Returns:
            Dict with status "ok".
        """
        return {"status": "ok"}

    return app


app = create_app()
