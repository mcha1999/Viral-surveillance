"""
Risk calculation endpoints
"""

from datetime import datetime
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.cache import get_cache, set_cache, cache_key

logger = structlog.get_logger()
router = APIRouter()


# =============================================================================
# Schemas
# =============================================================================

class RiskScore(BaseModel):
    """Risk score for a location."""
    location_id: str
    risk_score: float = Field(..., ge=0, le=100)
    components: dict
    confidence: float = Field(..., ge=0, le=1)
    last_updated: Optional[datetime] = None


class RiskForecastPoint(BaseModel):
    """Single forecast data point."""
    date: str
    risk_score: float
    confidence_low: float
    confidence_high: float


class RiskForecast(BaseModel):
    """Risk forecast for a location."""
    location_id: str
    current_score: float
    forecast: List[RiskForecastPoint]
    trend: str  # "rising", "falling", "stable"


class GlobalRiskSummary(BaseModel):
    """Global risk summary."""
    total_locations: int
    high_risk_count: int  # >= 70
    medium_risk_count: int  # 30-69
    low_risk_count: int  # < 30
    hotspots: List[dict]
    last_updated: datetime


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/{location_id}", response_model=RiskScore)
async def get_risk_score(
    location_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get current risk score for a location with component breakdown.

    Risk score is calculated from:
    - Wastewater viral load (40%)
    - Growth velocity (30%)
    - Import pressure from flights (30%)
    """
    # Try cache first
    cache_k = cache_key("risk", location_id)
    cached = await get_cache(cache_k)
    if cached:
        return cached

    # Get wastewater component
    ww_query = """
        SELECT
            AVG(normalized_score) as ww_score,
            AVG(velocity) as velocity,
            MAX(timestamp) as last_updated,
            COUNT(*) as event_count
        FROM surveillance_events
        WHERE location_id = :location_id
          AND signal = 'wastewater'
          AND timestamp > NOW() - INTERVAL '14 days'
    """
    ww_result = await db.execute(text(ww_query), {"location_id": location_id})
    ww_row = ww_result.fetchone()

    # Get import pressure component
    import_query = """
        SELECT AVG(export_risk_score) as import_pressure
        FROM vector_arcs
        WHERE dest_location_id = :location_id
          AND date >= CURRENT_DATE - INTERVAL '7 days'
    """
    import_result = await db.execute(text(import_query), {"location_id": location_id})
    import_row = import_result.fetchone()

    # Calculate components
    ww_score = float(ww_row.ww_score) if ww_row and ww_row.ww_score else 0
    velocity = float(ww_row.velocity) if ww_row and ww_row.velocity else 0
    import_pressure = float(import_row.import_pressure) if import_row and import_row.import_pressure else 0

    # Normalize velocity to 0-1 (assuming -1 to +1 range)
    velocity_normalized = max(0, min(1, (velocity + 1) / 2))

    # Calculate final score
    final_score = (
        ww_score * 0.4 +
        velocity_normalized * 0.3 +
        import_pressure * 0.3
    ) * 100

    final_score = max(0, min(100, final_score))

    # Calculate confidence based on data availability
    data_points = ww_row.event_count if ww_row else 0
    confidence = min(1.0, data_points / 10)  # Full confidence at 10+ data points

    response = RiskScore(
        location_id=location_id,
        risk_score=round(final_score, 1),
        components={
            "wastewater_load": round(ww_score * 100, 1),
            "growth_velocity": round(velocity_normalized * 100, 1),
            "import_pressure": round(import_pressure * 100, 1),
        },
        confidence=round(confidence, 2),
        last_updated=ww_row.last_updated if ww_row else None,
    )

    # Cache for 1 hour
    await set_cache(cache_k, response.model_dump(), ttl_seconds=3600)

    return response


@router.get("/{location_id}/forecast", response_model=RiskForecast)
async def get_risk_forecast(
    location_id: str,
    days: int = Query(7, ge=1, le=14),
    db: AsyncSession = Depends(get_db),
):
    """
    Get risk forecast for a location.

    Uses simple linear extrapolation for MVP.
    Future: implement proper time series forecasting.

    - **days**: Number of days to forecast (default 7, max 14)
    """
    # Get recent trend data
    query = """
        SELECT
            DATE(timestamp) as date,
            AVG(normalized_score) as avg_score
        FROM surveillance_events
        WHERE location_id = :location_id
          AND signal = 'wastewater'
          AND timestamp > NOW() - INTERVAL '14 days'
        GROUP BY DATE(timestamp)
        ORDER BY date
    """

    result = await db.execute(text(query), {"location_id": location_id})
    rows = result.fetchall()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="Insufficient data for forecast"
        )

    # Calculate simple linear trend
    scores = [float(r.avg_score) * 100 if r.avg_score else 0 for r in rows]
    current_score = scores[-1] if scores else 0

    if len(scores) >= 2:
        # Calculate average daily change
        daily_change = (scores[-1] - scores[0]) / len(scores)
    else:
        daily_change = 0

    # Determine trend
    if daily_change > 1:
        trend = "rising"
    elif daily_change < -1:
        trend = "falling"
    else:
        trend = "stable"

    # Generate forecast
    forecast = []
    base_date = datetime.utcnow().date()

    for i in range(1, days + 1):
        forecast_date = base_date + timedelta(days=i)
        projected_score = current_score + (daily_change * i)

        # Clamp to valid range
        projected_score = max(0, min(100, projected_score))

        # Confidence interval widens with time
        uncertainty = 5 * i  # +/- 5 points per day
        conf_low = max(0, projected_score - uncertainty)
        conf_high = min(100, projected_score + uncertainty)

        forecast.append(RiskForecastPoint(
            date=forecast_date.isoformat(),
            risk_score=round(projected_score, 1),
            confidence_low=round(conf_low, 1),
            confidence_high=round(conf_high, 1),
        ))

    return RiskForecast(
        location_id=location_id,
        current_score=round(current_score, 1),
        forecast=forecast,
        trend=trend,
    )


@router.get("/summary/global", response_model=GlobalRiskSummary)
async def get_global_summary(
    db: AsyncSession = Depends(get_db),
):
    """
    Get global risk summary with hotspots.
    """
    # Try cache first
    cache_k = cache_key("risk", "global_summary")
    cached = await get_cache(cache_k)
    if cached:
        return cached

    # Get counts by risk level
    query = """
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE risk_score >= 70) as high_risk,
            COUNT(*) FILTER (WHERE risk_score >= 30 AND risk_score < 70) as medium_risk,
            COUNT(*) FILTER (WHERE risk_score < 30) as low_risk,
            MAX(last_updated) as last_updated
        FROM risk_scores
    """

    result = await db.execute(text(query))
    row = result.fetchone()

    # Get top 10 hotspots
    hotspots_query = """
        SELECT
            location_id,
            name,
            country,
            risk_score,
            variants
        FROM risk_scores
        WHERE risk_score IS NOT NULL
        ORDER BY risk_score DESC
        LIMIT 10
    """

    hotspots_result = await db.execute(text(hotspots_query))
    hotspots = [
        {
            "location_id": h.location_id,
            "name": h.name,
            "country": h.country,
            "risk_score": float(h.risk_score),
            "variants": h.variants or [],
        }
        for h in hotspots_result.fetchall()
    ]

    response = GlobalRiskSummary(
        total_locations=row.total or 0,
        high_risk_count=row.high_risk or 0,
        medium_risk_count=row.medium_risk or 0,
        low_risk_count=row.low_risk or 0,
        hotspots=hotspots,
        last_updated=row.last_updated or datetime.utcnow(),
    )

    # Cache for 15 minutes
    await set_cache(cache_k, response.model_dump(), ttl_seconds=900)

    return response


# Import timedelta at the top
from datetime import timedelta
