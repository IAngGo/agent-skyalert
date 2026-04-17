"""
FastAPI application factory for SkyAlert.

Creates the app, registers exception handlers, and includes all routers.
This is the entry point for uvicorn:
    uvicorn backend.infrastructure.api.main:app --reload
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

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

    # CORS — allow all origins in development; tighten for production
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    app.add_exception_handler(SkyAlertError, skyalert_exception_handler)
    app.add_exception_handler(ValueError, value_error_handler)

    # Routers
    app.include_router(users.router)
    app.include_router(searches.router)
    app.include_router(alerts.router)

    # Serve the frontend as static files under /app
    frontend_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "frontend")
    frontend_dir = os.path.abspath(frontend_dir)
    if os.path.isdir(frontend_dir):
        app.mount("/app", StaticFiles(directory=frontend_dir, html=True), name="frontend")

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        """Redirect root to the landing page."""
        return RedirectResponse(url="/app/landing.html")

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
