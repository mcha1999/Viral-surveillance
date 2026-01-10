"""
Search endpoints
"""

from typing import List

import structlog
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.cache import get_cache, set_cache, cache_key

logger = structlog.get_logger()
router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================

class SearchResult(BaseModel):
    """Search result item."""
    location_id: str
    name: str
    country: str
    iso_code: str
    granularity: str
    match_score: float


class SearchResponse(BaseModel):
    """Search response."""
    query: str
    results: List[SearchResult]
    total: int


# =============================================================================
# Endpoints
# =============================================================================

@router.get("", response_model=SearchResponse)
async def search_locations(
    q: str = Query(..., min_length=2, max_length=100, description="Search query"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    Search for locations by name.

    Uses PostgreSQL trigram similarity for fuzzy matching.
    """
    # Try cache first
    cache_k = cache_key("search", q.lower(), str(limit))
    cached = await get_cache(cache_k)
    if cached:
        return cached

    # Search using trigram similarity
    query = """
        SELECT
            location_id,
            name,
            country,
            iso_code,
            granularity::text as granularity,
            similarity(name, :query) as match_score
        FROM location_nodes
        WHERE name % :query
           OR name ILIKE :like_query
        ORDER BY
            CASE WHEN name ILIKE :exact_query THEN 0 ELSE 1 END,
            similarity(name, :query) DESC,
            name
        LIMIT :limit
    """

    result = await db.execute(
        text(query),
        {
            "query": q,
            "like_query": f"%{q}%",
            "exact_query": f"{q}%",
            "limit": limit,
        }
    )

    rows = result.fetchall()

    results = [
        SearchResult(
            location_id=row.location_id,
            name=row.name,
            country=row.country,
            iso_code=row.iso_code,
            granularity=row.granularity or "tier_3",
            match_score=float(row.match_score) if row.match_score else 0,
        )
        for row in rows
    ]

    response = SearchResponse(
        query=q,
        results=results,
        total=len(results),
    )

    # Cache for 1 hour (location names don't change often)
    await set_cache(cache_k, response.model_dump(), ttl_seconds=3600)

    return response


@router.get("/autocomplete")
async def autocomplete(
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """
    Fast autocomplete for location search.

    Optimized for speed, returns minimal data.
    """
    # Try cache first
    cache_k = cache_key("autocomplete", q.lower(), str(limit))
    cached = await get_cache(cache_k)
    if cached:
        return cached

    query = """
        SELECT
            location_id,
            name,
            country
        FROM location_nodes
        WHERE name ILIKE :prefix
        ORDER BY
            length(name),
            name
        LIMIT :limit
    """

    result = await db.execute(
        text(query),
        {"prefix": f"{q}%", "limit": limit}
    )

    suggestions = [
        {
            "id": row.location_id,
            "label": f"{row.name}, {row.country}",
        }
        for row in result.fetchall()
    ]

    # Cache for 1 hour
    await set_cache(cache_k, suggestions, ttl_seconds=3600)

    return suggestions
