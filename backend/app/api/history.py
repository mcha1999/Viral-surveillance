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


class VariantWave(BaseModel):
    """Represents a period where a variant was dominant or highly prevalent."""
    variant_id: str
    display_name: str
    color: str
    start_date: str
    peak_date: str
    end_date: Optional[str] = None
    peak_percentage: float
    is_active: bool = True


class VariantWavesResponse(BaseModel):
    waves: List[VariantWave]
    date_range: dict
    location_id: Optional[str] = None


class VariantCompositionPoint(BaseModel):
    """Variant composition at a specific date."""
    date: str
    variants: dict  # variant_id -> percentage


class VariantCompositionResponse(BaseModel):
    location_id: str
    series: List[VariantCompositionPoint]
    variants: List[str]  # All variants present in the series
    date_range: dict


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


# Variant colors for visualization
VARIANT_COLORS = {
    "BA.2.86": "#8b5cf6",  # purple
    "JN.1": "#ef4444",     # red
    "JN.1.1": "#f97316",   # orange
    "XBB.1.5": "#22c55e",  # green
    "EG.5": "#3b82f6",     # blue
    "HV.1": "#06b6d4",     # cyan
    "JD.1.1": "#eab308",   # yellow
}


def generate_variant_waves(
    start_date: date,
    end_date: date,
    location_id: Optional[str] = None,
) -> List[VariantWave]:
    """Generate synthetic variant wave data showing dominance periods."""
    waves = []
    total_days = (end_date - start_date).days

    # Seed for consistency
    seed_str = location_id or "global"
    seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
    random.seed(seed)

    # Generate overlapping waves for major variants
    wave_variants = ["XBB.1.5", "EG.5", "BA.2.86", "JN.1", "JN.1.1"]

    for i, variant in enumerate(wave_variants):
        # Each wave spans a portion of the date range with some overlap
        wave_start_offset = int(total_days * (i / len(wave_variants)) * 0.8)
        wave_duration = int(total_days * 0.4) + random.randint(-10, 20)
        peak_offset = wave_start_offset + wave_duration // 2 + random.randint(-5, 5)

        wave_start = start_date + timedelta(days=wave_start_offset)
        wave_peak = start_date + timedelta(days=min(peak_offset, total_days - 1))

        # Determine if wave has ended
        wave_end_offset = wave_start_offset + wave_duration
        if wave_end_offset < total_days:
            wave_end = start_date + timedelta(days=wave_end_offset)
            is_active = False
        else:
            wave_end = None
            is_active = True

        waves.append(VariantWave(
            variant_id=variant,
            display_name=variant,
            color=VARIANT_COLORS.get(variant, "#888888"),
            start_date=wave_start.isoformat(),
            peak_date=wave_peak.isoformat(),
            end_date=wave_end.isoformat() if wave_end else None,
            peak_percentage=random.uniform(30, 70),
            is_active=is_active,
        ))

    random.seed()  # Reset seed
    return waves


def generate_variant_composition(
    location_id: str,
    start_date: date,
    end_date: date,
    granularity: str = "daily",
) -> List[VariantCompositionPoint]:
    """Generate synthetic variant composition data over time."""
    seed = int(hashlib.md5(location_id.encode()).hexdigest()[:8], 16)
    random.seed(seed)

    date_step = timedelta(days=7) if granularity == "weekly" else timedelta(days=1)
    total_days = (end_date - start_date).days

    # Initialize variant prevalence with smooth transitions
    variant_list = ["XBB.1.5", "EG.5", "BA.2.86", "JN.1", "JN.1.1"]

    composition_series = []
    current_date = start_date

    while current_date <= end_date:
        day_offset = (current_date - start_date).days
        progress = day_offset / max(total_days, 1)

        # Create smooth wave-like transitions between variants
        composition = {}
        total = 0

        for i, variant in enumerate(variant_list):
            # Each variant has a wave centered at different points in time
            wave_center = i / len(variant_list)
            wave_width = 0.3

            # Gaussian-like wave
            distance = abs(progress - wave_center)
            if distance < wave_width * 2:
                base_value = max(0, 50 * (1 - (distance / wave_width) ** 2))
            else:
                base_value = 0

            # Add some noise
            value = max(0, base_value + random.gauss(0, 5))
            composition[variant] = value
            total += value

        # Normalize to 100%
        if total > 0:
            for variant in composition:
                composition[variant] = round(composition[variant] / total * 100, 1)

        composition_series.append(VariantCompositionPoint(
            date=current_date.isoformat(),
            variants=composition,
        ))

        current_date += date_step

    random.seed()  # Reset seed
    return composition_series


@router.get("/variant-waves", response_model=VariantWavesResponse)
async def get_variant_waves(
    location_id: Optional[str] = Query(None, description="Location ID (optional, defaults to global)"),
    days: int = Query(90, ge=30, le=365, description="Number of days of history"),
):
    """
    Get variant wave periods showing when each variant was dominant.

    Returns chronological list of variant waves with start, peak, and end dates.
    Useful for timeline visualization of variant succession.
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    waves = generate_variant_waves(start_date, end_date, location_id)

    return VariantWavesResponse(
        waves=waves,
        date_range={"start": start_date.isoformat(), "end": end_date.isoformat()},
        location_id=location_id,
    )


@router.get("/variant-composition/{location_id}", response_model=VariantCompositionResponse)
async def get_variant_composition(
    location_id: str,
    days: int = Query(90, ge=30, le=365, description="Number of days of history"),
    granularity: str = Query("weekly", description="Data granularity: daily or weekly"),
):
    """
    Get time series of variant composition percentages for a location.

    Returns variant percentages over time, suitable for stacked area charts.
    Each point shows what percentage of detected variants each strain represents.
    """
    if granularity not in ["daily", "weekly"]:
        raise HTTPException(status_code=400, detail="granularity must be 'daily' or 'weekly'")

    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    series = generate_variant_composition(location_id, start_date, end_date, granularity)

    # Collect all variants present
    all_variants = set()
    for point in series:
        all_variants.update(point.variants.keys())

    return VariantCompositionResponse(
        location_id=location_id,
        series=series,
        variants=sorted(list(all_variants)),
        date_range={"start": start_date.isoformat(), "end": end_date.isoformat()},
    )
