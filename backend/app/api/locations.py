"""
Location endpoints
"""

from datetime import datetime, timedelta
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.cache import get_cache, set_cache, cache_key
from app.core.config import settings

logger = structlog.get_logger()
router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================

class Coordinates(BaseModel):
    """Geographic coordinates."""
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)


class LocationBase(BaseModel):
    """Base location schema."""
    location_id: str
    name: str
    country: str
    iso_code: str
    granularity: str
    coordinates: Coordinates


class LocationSummary(LocationBase):
    """Location with risk summary."""
    risk_score: Optional[float] = None
    last_updated: Optional[datetime] = None
    variants: Optional[List[str]] = None


class IncomingThreat(BaseModel):
    """Incoming flight threat."""
    origin_name: str
    origin_country: str
    flight_count: int
    pax_estimate: int
    source_risk_score: float
    primary_variant: Optional[str] = None


class LocationDossier(LocationBase):
    """Full location dossier."""
    risk_score: float
    risk_trend: str  # "rising", "falling", "stable"
    last_updated: Optional[datetime] = None
    variants: List[str] = []
    dominant_variant: Optional[str] = None
    weekly_change: Optional[float] = None
    catchment_population: Optional[int] = None
    incoming_threats: List[IncomingThreat] = []
    data_quality: str  # "excellent", "good", "limited"


class LocationListResponse(BaseModel):
    """Paginated location list."""
    items: List[LocationSummary]
    total: int
    page: int
    page_size: int


# =============================================================================
# Endpoints
# =============================================================================

@router.get("", response_model=LocationListResponse)
async def list_locations(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    country: Optional[str] = Query(None, min_length=2, max_length=2),
    min_risk: Optional[float] = Query(None, ge=0, le=100),
    db: AsyncSession = Depends(get_db),
):
    """
    List all locations with current risk scores.

    - **page**: Page number (default 1)
    - **page_size**: Items per page (default 50, max 100)
    - **country**: Filter by ISO country code (e.g., "US")
    - **min_risk**: Filter locations with risk >= this value
    """
    # Try cache first
    cache_k = cache_key("locations", f"{page}_{page_size}_{country}_{min_risk}")
    cached = await get_cache(cache_k)
    if cached:
        return cached

    # Build query
    offset = (page - 1) * page_size

    filters = []
    params = {"limit": page_size, "offset": offset}

    if country:
        filters.append("iso_code = :country")
        params["country"] = country.upper()

    if min_risk is not None:
        filters.append("risk_score >= :min_risk")
        params["min_risk"] = min_risk

    where_clause = " AND ".join(filters) if filters else "1=1"

    # Get total count
    count_query = f"""
        SELECT COUNT(*) FROM risk_scores WHERE {where_clause}
    """
    result = await db.execute(text(count_query), params)
    total = result.scalar()

    # Get locations
    query = f"""
        SELECT
            location_id,
            name,
            country,
            iso_code,
            granularity::text as granularity,
            ST_X(geometry) as lon,
            ST_Y(geometry) as lat,
            risk_score,
            last_updated,
            variants
        FROM risk_scores
        WHERE {where_clause}
        ORDER BY risk_score DESC NULLS LAST
        LIMIT :limit OFFSET :offset
    """

    result = await db.execute(text(query), params)
    rows = result.fetchall()

    items = [
        LocationSummary(
            location_id=row.location_id,
            name=row.name,
            country=row.country,
            iso_code=row.iso_code,
            granularity=row.granularity or "tier_3",
            coordinates=Coordinates(lat=row.lat, lon=row.lon),
            risk_score=float(row.risk_score) if row.risk_score else None,
            last_updated=row.last_updated,
            variants=row.variants or [],
        )
        for row in rows
    ]

    response = LocationListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )

    # Cache for 5 minutes
    await set_cache(cache_k, response.model_dump(), ttl_seconds=300)

    return response


@router.get("/{location_id}", response_model=LocationDossier)
async def get_location(
    location_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get detailed dossier for a specific location.

    Returns risk score, variants, incoming threats, and trend data.
    """
    # Try cache first
    cache_k = cache_key("location", location_id)
    cached = await get_cache(cache_k)
    if cached:
        return cached

    # Get location details
    query = """
        SELECT
            ln.location_id,
            ln.name,
            ln.country,
            ln.iso_code,
            ln.granularity::text as granularity,
            ST_X(ln.geometry) as lon,
            ST_Y(ln.geometry) as lat,
            ln.catchment_population,
            rs.risk_score,
            rs.last_updated,
            rs.variants,
            rs.avg_velocity
        FROM location_nodes ln
        LEFT JOIN risk_scores rs ON ln.location_id = rs.location_id
        WHERE ln.location_id = :location_id
    """

    result = await db.execute(text(query), {"location_id": location_id})
    row = result.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Location not found")

    # Determine trend
    velocity = row.avg_velocity or 0
    if velocity > 0.1:
        trend = "rising"
    elif velocity < -0.1:
        trend = "falling"
    else:
        trend = "stable"

    # Determine data quality based on granularity and freshness
    if row.last_updated:
        days_old = (datetime.utcnow() - row.last_updated).days
    else:
        days_old = 999

    if row.granularity == "tier_1" and days_old < 7:
        data_quality = "excellent"
    elif row.granularity in ("tier_1", "tier_2") and days_old < 14:
        data_quality = "good"
    else:
        data_quality = "limited"

    # Get incoming threats (top 5)
    threats_query = """
        SELECT
            ln.name as origin_name,
            ln.country as origin_country,
            va.flight_count,
            va.pax_estimate,
            rs.risk_score as source_risk_score,
            va.primary_variant
        FROM vector_arcs va
        JOIN location_nodes ln ON va.origin_location_id = ln.location_id
        LEFT JOIN risk_scores rs ON va.origin_location_id = rs.location_id
        WHERE va.dest_location_id = :location_id
          AND va.date >= CURRENT_DATE - INTERVAL '7 days'
        ORDER BY rs.risk_score DESC NULLS LAST
        LIMIT 5
    """

    threats_result = await db.execute(text(threats_query), {"location_id": location_id})
    threats_rows = threats_result.fetchall()

    incoming_threats = [
        IncomingThreat(
            origin_name=t.origin_name,
            origin_country=t.origin_country,
            flight_count=t.flight_count or 0,
            pax_estimate=t.pax_estimate or 0,
            source_risk_score=float(t.source_risk_score) if t.source_risk_score else 0,
            primary_variant=t.primary_variant,
        )
        for t in threats_rows
    ]

    variants = row.variants or []
    dossier = LocationDossier(
        location_id=row.location_id,
        name=row.name,
        country=row.country,
        iso_code=row.iso_code,
        granularity=row.granularity or "tier_3",
        coordinates=Coordinates(lat=row.lat, lon=row.lon),
        risk_score=float(row.risk_score) if row.risk_score else 0,
        risk_trend=trend,
        last_updated=row.last_updated,
        variants=variants,
        dominant_variant=variants[0] if variants else None,
        weekly_change=float(velocity * 100) if velocity else None,  # Convert to percentage
        catchment_population=row.catchment_population,
        incoming_threats=incoming_threats,
        data_quality=data_quality,
    )

    # Cache for 5 minutes
    await set_cache(cache_k, dossier.model_dump(), ttl_seconds=300)

    return dossier


@router.get("/{location_id}/history")
async def get_location_history(
    location_id: str,
    days: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    """
    Get historical surveillance data for a location.

    - **days**: Number of days of history (default 30, max 90)
    """
    # Verify location exists
    check = await db.execute(
        text("SELECT 1 FROM location_nodes WHERE location_id = :id"),
        {"id": location_id}
    )
    if not check.fetchone():
        raise HTTPException(status_code=404, detail="Location not found")

    query = """
        SELECT
            DATE(timestamp) as date,
            AVG(normalized_score) as avg_score,
            AVG(velocity) as avg_velocity,
            array_agg(DISTINCT unnest) as variants
        FROM surveillance_events,
             LATERAL unnest(confirmed_variants) WITH ORDINALITY
        WHERE location_id = :location_id
          AND timestamp >= NOW() - (:days || ' days')::INTERVAL
        GROUP BY DATE(timestamp)
        ORDER BY date
    """

    result = await db.execute(text(query), {"location_id": location_id, "days": days})
    rows = result.fetchall()

    return {
        "location_id": location_id,
        "days": days,
        "history": [
            {
                "date": row.date.isoformat(),
                "risk_score": float(row.avg_score * 100) if row.avg_score else None,
                "velocity": float(row.avg_velocity) if row.avg_velocity else None,
                "variants": row.variants or [],
            }
            for row in rows
        ],
    }
