"""
FastAPI application entry point.
Configures middleware, routers, startup/shutdown events, and global exception handling.
"""
from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.core.config import settings
from app.core.logging import configure_logging, get_logger, set_request_id
from app.database.connection import check_db_connection, close_db, init_db
from app.database.schemas import HealthResponse
from app.services.gemini_service import get_gemini_service

# Configure logging before anything else
configure_logging(debug=settings.DEBUG)
logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Application lifespan (startup / shutdown)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifecycle: DB init, service warmup, cleanup."""
    logger.info("Starting %s v%s [%s]", settings.APP_NAME, settings.APP_VERSION, settings.ENVIRONMENT)

    # Initialize database tables
    try:
        await init_db()
        logger.info("Database initialized successfully.")
    except Exception as exc:
        logger.error("Failed to initialize database: %s. Continuing without DB.", exc)

    yield  # Application runs

    # Cleanup
    logger.info("Shutting down application...")
    await close_db()
    logger.info("Application shutdown complete.")


# ---------------------------------------------------------------------------
# FastAPI app instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Enterprise GTM Intelligence Agent — AI-powered sales research, "
        "account scoring, and strategy generation platform."
    ),
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Request ID middleware
# ---------------------------------------------------------------------------

@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Attach a unique request ID to each request for tracing."""
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:8]
    set_request_id(request_id)
    start_time = time.time()

    response = await call_next(request)

    duration_ms = round((time.time() - start_time) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time-Ms"] = str(duration_ms)

    logger.info(
        "%s %s %d (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


# ---------------------------------------------------------------------------
# Global exception handlers — never expose stack traces to clients
# ---------------------------------------------------------------------------

@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    logger.warning("Validation error: %s", exc)
    return JSONResponse(
        status_code=422,
        content={"success": False, "message": str(exc), "errors": [str(exc)]},
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "An internal server error occurred. Please try again.",
            "errors": [],
        },
    )


# ---------------------------------------------------------------------------
# Health endpoint (root-level, before versioned routes)
# ---------------------------------------------------------------------------

@app.get("/api/v1/health", response_model=HealthResponse, tags=["System"])
async def health_check() -> HealthResponse:
    """
    Application health check.
    Returns connectivity status for database and Gemini API.
    Does NOT expose internal errors or secrets.
    """
    db_ok = await check_db_connection()
    gemini_status = await get_gemini_service().health_check()

    return HealthResponse(
        status="ok" if db_ok else "degraded",
        version=settings.APP_VERSION,
        database="connected" if db_ok else "disconnected",
        gemini=gemini_status["status"],
        environment=settings.ENVIRONMENT,
        timestamp=datetime.utcnow(),
    )


# ---------------------------------------------------------------------------
# API Routers
# ---------------------------------------------------------------------------

from app.api.routes import accounts, ingestion, research, reports, chat, opportunities  # noqa: E402

app.include_router(accounts.router, prefix=settings.API_V1_PREFIX, tags=["Accounts"])
app.include_router(ingestion.router, prefix=settings.API_V1_PREFIX, tags=["Ingestion"])
app.include_router(research.router, prefix=settings.API_V1_PREFIX, tags=["Research"])
app.include_router(reports.router, prefix=settings.API_V1_PREFIX, tags=["Reports"])
app.include_router(chat.router, prefix=settings.API_V1_PREFIX, tags=["Chat"])
app.include_router(opportunities.router, prefix=settings.API_V1_PREFIX, tags=["Opportunities"])


# ---------------------------------------------------------------------------
# UI Static Files & Root
# ---------------------------------------------------------------------------

_static_dir = Path(__file__).parent / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")

@app.get("/", include_in_schema=False)
async def root():
    index_file = _static_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": f"{settings.API_V1_PREFIX}/docs",
    }
