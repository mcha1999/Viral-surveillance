"""
Variant tracking and spread visualization endpoints.
"""

from datetime import datetime, date, timedelta
from typing import Optional, List
import random
import hashlib

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/variants", tags=["variants"])


class VariantSpreadArc(BaseModel):
    """Arc data for variant spread visualization."""
    arc_id: str
    origin_lat: float
    origin_lon: float
    origin_name: str
    origin_country: str
    dest_lat: float
    dest_lon: float
    dest_name: str
    dest_country: str
    variant_id: str
    days_since_origin_detection: int
    pax_volume: int
    first_detection_date: str
    is_active: bool = True


class VariantSpreadResponse(BaseModel):
    """Response for variant spread arcs."""
    variant_id: str
    arcs: List[VariantSpreadArc]
    date_range: dict
    total_arcs: int


class FirstDetectionMarker(BaseModel):
    """Marker for first detection of variant at a location."""
    location_id: str
    location_name: str
    country: str
    lat: float
    lon: float
    variant_id: str
    detection_date: str
    detection_type: str  # 'traveler' or 'local'
    confidence: float


class DetectionMarkersResponse(BaseModel):
    """Response for first detection markers."""
    variant_id: str
    markers: List[FirstDetectionMarker]
    earliest_detection: str
    total_locations: int


# Sample airport/city data for synthetic generation
MAJOR_HUBS = [
    {"id": "loc_us_new_york", "name": "New York", "country": "United States", "lat": 40.7128, "lon": -74.0060},
    {"id": "loc_us_los_angeles", "name": "Los Angeles", "country": "United States", "lat": 34.0522, "lon": -118.2437},
    {"id": "loc_us_chicago", "name": "Chicago", "country": "United States", "lat": 41.8781, "lon": -87.6298},
    {"id": "loc_gb_london", "name": "London", "country": "United Kingdom", "lat": 51.5074, "lon": -0.1278},
    {"id": "loc_fr_paris", "name": "Paris", "country": "France", "lat": 48.8566, "lon": 2.3522},
    {"id": "loc_de_berlin", "name": "Berlin", "country": "Germany", "lat": 52.5200, "lon": 13.4050},
    {"id": "loc_de_frankfurt", "name": "Frankfurt", "country": "Germany", "lat": 50.1109, "lon": 8.6821},
    {"id": "loc_nl_amsterdam", "name": "Amsterdam", "country": "Netherlands", "lat": 52.3676, "lon": 4.9041},
    {"id": "loc_ae_dubai", "name": "Dubai", "country": "UAE", "lat": 25.2048, "lon": 55.2708},
    {"id": "loc_sg_singapore", "name": "Singapore", "country": "Singapore", "lat": 1.3521, "lon": 103.8198},
    {"id": "loc_hk_hong_kong", "name": "Hong Kong", "country": "China", "lat": 22.3193, "lon": 114.1694},
    {"id": "loc_jp_tokyo", "name": "Tokyo", "country": "Japan", "lat": 35.6762, "lon": 139.6503},
    {"id": "loc_kr_seoul", "name": "Seoul", "country": "South Korea", "lat": 37.5665, "lon": 126.9780},
    {"id": "loc_au_sydney", "name": "Sydney", "country": "Australia", "lat": -33.8688, "lon": 151.2093},
    {"id": "loc_br_sao_paulo", "name": "São Paulo", "country": "Brazil", "lat": -23.5505, "lon": -46.6333},
    {"id": "loc_mx_mexico_city", "name": "Mexico City", "country": "Mexico", "lat": 19.4326, "lon": -99.1332},
    {"id": "loc_in_mumbai", "name": "Mumbai", "country": "India", "lat": 19.0760, "lon": 72.8777},
    {"id": "loc_in_delhi", "name": "Delhi", "country": "India", "lat": 28.6139, "lon": 77.2090},
    {"id": "loc_za_johannesburg", "name": "Johannesburg", "country": "South Africa", "lat": -26.2041, "lon": 28.0473},
    {"id": "loc_eg_cairo", "name": "Cairo", "country": "Egypt", "lat": 30.0444, "lon": 31.2357},
]

VARIANTS = ["BA.2.86", "JN.1", "JN.1.1", "XBB.1.5", "EG.5"]


def generate_spread_arcs(
    variant_id: str,
    start_date: date,
    end_date: date,
) -> List[VariantSpreadArc]:
    """Generate synthetic variant spread arcs."""
    seed = int(hashlib.md5(f"{variant_id}_{start_date}".encode()).hexdigest()[:8], 16)
    random.seed(seed)

    arcs = []
    total_days = (end_date - start_date).days

    # Select origin hub for this variant (deterministic by variant)
    variant_idx = VARIANTS.index(variant_id) if variant_id in VARIANTS else 0
    origin_hub = MAJOR_HUBS[variant_idx % len(MAJOR_HUBS)]

    # Generate spread from origin to other hubs
    for i, dest_hub in enumerate(MAJOR_HUBS):
        if dest_hub["id"] == origin_hub["id"]:
            continue

        # Calculate days since detection based on distance/connectivity
        base_delay = random.randint(3, 21)
        days_since = min(total_days, base_delay + random.randint(0, 14))

        # Calculate first detection date
        first_detection = end_date - timedelta(days=days_since)
        if first_detection < start_date:
            first_detection = start_date
            days_since = (end_date - first_detection).days

        # Generate arc
        arcs.append(VariantSpreadArc(
            arc_id=f"spread_{variant_id}_{origin_hub['id']}_{dest_hub['id']}",
            origin_lat=origin_hub["lat"],
            origin_lon=origin_hub["lon"],
            origin_name=origin_hub["name"],
            origin_country=origin_hub["country"],
            dest_lat=dest_hub["lat"],
            dest_lon=dest_hub["lon"],
            dest_name=dest_hub["name"],
            dest_country=dest_hub["country"],
            variant_id=variant_id,
            days_since_origin_detection=days_since,
            pax_volume=random.randint(500, 5000),
            first_detection_date=first_detection.isoformat(),
            is_active=days_since <= 14,
        ))

    random.seed()  # Reset seed
    return arcs


def generate_detection_markers(
    variant_id: str,
    days: int,
) -> List[FirstDetectionMarker]:
    """Generate first detection markers for a variant."""
    seed = int(hashlib.md5(f"markers_{variant_id}".encode()).hexdigest()[:8], 16)
    random.seed(seed)

    markers = []
    today = date.today()

    # Origin location (first detection)
    variant_idx = VARIANTS.index(variant_id) if variant_id in VARIANTS else 0
    origin_hub = MAJOR_HUBS[variant_idx % len(MAJOR_HUBS)]

    # Origin is the first detection
    earliest_date = today - timedelta(days=days - random.randint(0, 10))
    markers.append(FirstDetectionMarker(
        location_id=origin_hub["id"],
        location_name=origin_hub["name"],
        country=origin_hub["country"],
        lat=origin_hub["lat"],
        lon=origin_hub["lon"],
        variant_id=variant_id,
        detection_date=earliest_date.isoformat(),
        detection_type="local",
        confidence=0.95,
    ))

    # Add traveler detections at other hubs
    for hub in MAJOR_HUBS:
        if hub["id"] == origin_hub["id"]:
            continue

        # Random chance of detection
        if random.random() > 0.7:
            continue

        detection_delay = random.randint(5, 30)
        detection_date = earliest_date + timedelta(days=detection_delay)

        if detection_date > today:
            continue

        # Traveler detection first, then local
        detection_type = "traveler" if random.random() > 0.3 else "local"

        markers.append(FirstDetectionMarker(
            location_id=hub["id"],
            location_name=hub["name"],
            country=hub["country"],
            lat=hub["lat"],
            lon=hub["lon"],
            variant_id=variant_id,
            detection_date=detection_date.isoformat(),
            detection_type=detection_type,
            confidence=random.uniform(0.7, 0.95),
        ))

    random.seed()  # Reset seed
    return sorted(markers, key=lambda m: m.detection_date)


@router.get("/spread-arcs/{variant_id}", response_model=VariantSpreadResponse)
async def get_variant_spread_arcs(
    variant_id: str,
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    days: int = Query(30, ge=7, le=90, description="Days of history if dates not specified"),
):
    """
    Get flight arcs showing variant spread from origin locations.

    Arcs are colored by days-since-variant-detection at origin.
    Used for animated playback of variant geographic spread.
    """
    if variant_id not in VARIANTS:
        raise HTTPException(status_code=404, detail=f"Unknown variant: {variant_id}")

    # Parse dates
    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format")
    else:
        end_dt = date.today()

    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format")
    else:
        start_dt = end_dt - timedelta(days=days)

    arcs = generate_spread_arcs(variant_id, start_dt, end_dt)

    return VariantSpreadResponse(
        variant_id=variant_id,
        arcs=arcs,
        date_range={"start": start_dt.isoformat(), "end": end_dt.isoformat()},
        total_arcs=len(arcs),
    )


@router.get("/first-detections/{variant_id}", response_model=DetectionMarkersResponse)
async def get_first_detections(
    variant_id: str,
    days: int = Query(60, ge=14, le=180, description="Days of history"),
):
    """
    Get first detection markers for a variant across locations.

    Shows where and when a variant was first detected, distinguishing
    between traveler screening detections and local surveillance detections.
    """
    if variant_id not in VARIANTS:
        raise HTTPException(status_code=404, detail=f"Unknown variant: {variant_id}")

    markers = generate_detection_markers(variant_id, days)

    earliest = markers[0].detection_date if markers else date.today().isoformat()

    return DetectionMarkersResponse(
        variant_id=variant_id,
        markers=markers,
        earliest_detection=earliest,
        total_locations=len(markers),
    )


@router.get("/list")
async def list_variants():
    """Get list of available variants for visualization."""
    return {
        "variants": [
            {"id": v, "display_name": v, "is_active": i >= len(VARIANTS) - 2}
            for i, v in enumerate(VARIANTS)
        ]
    }
