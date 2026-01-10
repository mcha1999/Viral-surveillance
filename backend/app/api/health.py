"""
Health check endpoints
"""

from datetime import datetime

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.cache import redis_client
from app.core.config import settings

logger = structlog.get_logger()
router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.VERSION,
    }


@router.get("/health/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """Readiness check - verifies all dependencies are available."""
    checks = {
        "database": False,
        "cache": False,
    }

    # Check database
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as e:
        logger.error("Database health check failed", error=str(e))

    # Check Redis
    try:
        if redis_client:
            await redis_client.ping()
            checks["cache"] = True
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))

    all_healthy = all(checks.values())

    return {
        "status": "ready" if all_healthy else "degraded",
        "checks": checks,
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health/live")
async def liveness_check():
    """Liveness check - verifies the application is running."""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat(),
    }
