"""
Historical data API endpoints.

Provides access to historical surveillance and risk data for trend analysis.
"""

from datetime import datetime, date, timedelta
from typing import Optional, List
import random
import hashlib

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/history", tags=["history"])


class HistoricalDataPoint(BaseModel):
    location_id: str
    date: str
    risk_score: Optional[float] = None
    velocity: Optional[float] = None
    variants: List[str] = []


class HistoricalDataResponse(BaseModel):
    data: List[HistoricalDataPoint]
    locations: int
    date_range: dict


class TimeSeriesPoint(BaseModel):
    date: str
    value: float
    confidence_low: Optional[float] = None
    confidence_high: Optional[float] = None


class TimeSeriesResponse(BaseModel):
    location_id: str
    metric: str
    series: List[TimeSeriesPoint]
    start_date: str
    end_date: str


# Sample variants for synthetic data
VARIANTS = [
    "BA.2.86",
    "JN.1",
    "JN.1.1",
    "XBB.1.5",
    "EG.5",
    "HV.1",
    "JD.1.1",
]


def generate_historical_data(
    location_ids: List[str],
    start_date: date,
    end_date: date,
    granularity: str = "daily",
) -> List[HistoricalDataPoint]:
    """Generate synthetic historical data for locations."""
    data_points = []

    # Determine date step based on granularity
    if granularity == "weekly":
        date_step = timedelta(days=7)
    else:
        date_step = timedelta(days=1)

    for loc_id in location_ids:
        # Use location_id as seed for consistent results
        seed = int(hashlib.md5(loc_id.encode()).hexdigest()[:8], 16)
        random.seed(seed)

        # Generate base risk level for this location
        base_risk = random.uniform(20, 70)

        current_date = start_date
        prev_score = base_risk

        while current_date <= end_date:
            # Add some temporal variation
            day_offset = (current_date - start_date).days
            seasonal = 10 * (0.5 + 0.5 * (1 + (day_offset % 90 - 45) / 45))

            # Random walk with mean reversion
            change = random.gauss(0, 5) + 0.1 * (base_risk - prev_score)
            risk_score = max(0, min(100, prev_score + change + seasonal * 0.1))

            # Calculate velocity (week-over-week change)
            velocity = change / 7 if granularity == "weekly" else change

            # Select variants (more likely to have dominant variant at higher risk)
            num_variants = 1 if risk_score < 30 else (2 if risk_score < 60 else 3)
            variants = random.sample(VARIANTS, min(num_variants, len(VARIANTS)))

            data_points.append(HistoricalDataPoint(
                location_id=loc_id,
                date=current_date.isoformat(),
                risk_score=round(risk_score, 1),
                velocity=round(velocity, 2),
                variants=variants,
            ))

            prev_score = risk_score
            current_date += date_step

    random.seed()  # Reset seed
    return data_points


# Sample location IDs for when none specified
SAMPLE_LOCATIONS = [
    "loc_us_new_york",
    "loc_us_los_angeles",
    "loc_us_chicago",
    "loc_gb_london",
    "loc_de_berlin",
    "loc_fr_paris",
    "loc_jp_tokyo",
    "loc_au_sydney",
    "loc_br_sao_paulo",
    "loc_sg_singapore",
]


@router.get("", response_model=HistoricalDataResponse)
async def get_historical_data(
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    location_id: Optional[List[str]] = Query(None, description="Location IDs to fetch"),
    granularity: str = Query("daily", description="Data granularity: daily or weekly"),
):
    """
    Get historical surveillance data for specified locations and date range.

    Returns risk scores, velocity, and variant information over time.
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    if end < start:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")

    if (end - start).days > 365:
        raise HTTPException(status_code=400, detail="Date range cannot exceed 365 days")

    if granularity not in ["daily", "weekly"]:
        raise HTTPException(status_code=400, detail="granularity must be 'daily' or 'weekly'")

    # Use sample locations if none specified
    locations = location_id if location_id else SAMPLE_LOCATIONS[:5]

    # For MVP, generate synthetic data
    # In production, this would query the database
    data = generate_historical_data(
        location_ids=locations,
        start_date=start,
        end_date=end,
        granularity=granularity,
    )

    return HistoricalDataResponse(
        data=data,
        locations=len(locations),
        date_range={"start": start_date, "end": end_date},
    )


@router.get("/timeseries/{location_id}", response_model=TimeSeriesResponse)
async def get_timeseries(
    location_id: str,
    metric: str = Query("risk_score", description="Metric to fetch: risk_score, velocity"),
    days: int = Query(30, ge=1, le=365, description="Number of days of history"),
):
    """
    Get time series data for a specific metric and location.

    Useful for charting and trend analysis.
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    # Generate data
    data = generate_historical_data(
        location_ids=[location_id],
        start_date=start_date,
        end_date=end_date,
        granularity="daily",
    )

    # Extract the requested metric
    series = []
    for point in data:
        value = getattr(point, metric, None)
        if value is not None:
            # Add confidence intervals (synthetic)
            confidence_margin = abs(value) * 0.15
            series.append(TimeSeriesPoint(
                date=point.date,
                value=value,
                confidence_low=max(0, value - confidence_margin),
                confidence_high=min(100, value + confidence_margin) if metric == "risk_score" else value + confidence_margin,
            ))

    return TimeSeriesResponse(
        location_id=location_id,
        metric=metric,
        series=series,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
    )


@router.get("/compare")
async def compare_locations(
    location_ids: List[str] = Query(..., description="Location IDs to compare"),
    metric: str = Query("risk_score", description="Metric to compare"),
    days: int = Query(30, ge=1, le=90, description="Number of days"),
):
    """
    Compare a metric across multiple locations over time.

    Returns aligned time series for easy comparison.
    """
    if len(location_ids) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 locations for comparison")

    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    # Generate data for all locations
    data = generate_historical_data(
        location_ids=location_ids,
        start_date=start_date,
        end_date=end_date,
        granularity="daily",
    )

    # Organize by location
    by_location = {}
    for point in data:
        if point.location_id not in by_location:
            by_location[point.location_id] = []
        by_location[point.location_id].append({
            "date": point.date,
            "value": getattr(point, metric, None),
        })

    return {
        "metric": metric,
        "date_range": {"start": start_date.isoformat(), "end": end_date.isoformat()},
        "locations": by_location,
    }


@router.get("/summary")
async def get_historical_summary(
    location_id: str,
    days: int = Query(30, ge=7, le=365, description="Number of days to summarize"),
):
    """
    Get summary statistics for a location's historical data.

    Includes averages, trends, and key metrics.
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    # Generate data
    data = generate_historical_data(
        location_ids=[location_id],
        start_date=start_date,
        end_date=end_date,
        granularity="daily",
    )

    if not data:
        raise HTTPException(status_code=404, detail="No data found for location")

    # Calculate statistics
    risk_scores = [p.risk_score for p in data if p.risk_score is not None]
    velocities = [p.velocity for p in data if p.velocity is not None]

    avg_risk = sum(risk_scores) / len(risk_scores) if risk_scores else 0
    max_risk = max(risk_scores) if risk_scores else 0
    min_risk = min(risk_scores) if risk_scores else 0
    avg_velocity = sum(velocities) / len(velocities) if velocities else 0

    # Determine trend
    if len(risk_scores) >= 7:
        recent_avg = sum(risk_scores[-7:]) / 7
        earlier_avg = sum(risk_scores[:7]) / 7
        if recent_avg > earlier_avg + 5:
            trend = "rising"
        elif recent_avg < earlier_avg - 5:
            trend = "falling"
        else:
            trend = "stable"
    else:
        trend = "insufficient_data"

    # Collect all variants seen
    all_variants = set()
    for p in data:
        all_variants.update(p.variants)

    return {
        "location_id": location_id,
        "period": {"start": start_date.isoformat(), "end": end_date.isoformat(), "days": days},
        "statistics": {
            "avg_risk_score": round(avg_risk, 1),
            "max_risk_score": round(max_risk, 1),
            "min_risk_score": round(min_risk, 1),
            "avg_velocity": round(avg_velocity, 2),
            "data_points": len(data),
        },
        "trend": trend,
        "variants_observed": list(all_variants),
    }
