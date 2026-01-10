"""
Viral Weather API
FastAPI application entry point
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import locations, risk, search, health, flights, history
from app.core.config import settings
from app.core.database import init_db, close_db
from app.core.cache import init_cache, close_cache

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Application lifespan handler for startup/shutdown."""
    # Startup
    logger.info("Starting Viral Weather API", version=settings.VERSION)
    await init_db()
    await init_cache()

    yield

    # Shutdown
    logger.info("Shutting down Viral Weather API")
    await close_db()
    await close_cache()


# Create FastAPI app
app = FastAPI(
    title="Viral Weather API",
    description="Predictive viral risk intelligence platform",
    version=settings.VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors."""
    logger.error(
        "Unhandled exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=exc,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(locations.router, prefix="/api/locations", tags=["Locations"])
app.include_router(risk.router, prefix="/api/risk", tags=["Risk"])
app.include_router(search.router, prefix="/api/search", tags=["Search"])
app.include_router(flights.router, tags=["Flights"])
app.include_router(history.router, tags=["History"])


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Viral Weather API",
        "version": settings.VERSION,
        "status": "operational",
        "docs": "/docs" if settings.DEBUG else None,
    }
