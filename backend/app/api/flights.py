"""
Flight data API endpoints.

Provides flight route data for visualization and import pressure calculation.
"""

from datetime import datetime, date, timedelta
from typing import Optional, List
import hashlib
import random
import logging

from fastapi import APIRouter, Query, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

router = APIRouter(prefix="/api/flights", tags=["flights"])


class FlightArc(BaseModel):
    arc_id: str
    origin_lat: float
    origin_lon: float
    origin_name: str
    origin_country: str
    dest_lat: float
    dest_lon: float
    dest_name: str
    dest_country: str
    pax_estimate: int
    flight_count: int
    origin_risk: Optional[float] = None


class FlightArcsResponse(BaseModel):
    arcs: List[FlightArc]
    total: int
    date: str


class ImportPressureSource(BaseModel):
    origin_name: str
    origin_country: str
    passengers: int
    risk_contribution: float


class ImportPressureResponse(BaseModel):
    location_id: str
    import_pressure: float
    top_sources: List[ImportPressureSource]
    timestamp: str


# Major airport hubs for generating synthetic flight data
AIRPORT_HUBS = {
    # North America
    "JFK": {"city": "New York", "country": "US", "lat": 40.6413, "lon": -73.7781, "risk": 45},
    "LAX": {"city": "Los Angeles", "country": "US", "lat": 33.9416, "lon": -118.4085, "risk": 38},
    "ORD": {"city": "Chicago", "country": "US", "lat": 41.9742, "lon": -87.9073, "risk": 42},
    "ATL": {"city": "Atlanta", "country": "US", "lat": 33.6407, "lon": -84.4277, "risk": 40},
    "DFW": {"city": "Dallas", "country": "US", "lat": 32.8998, "lon": -97.0403, "risk": 35},
    "MIA": {"city": "Miami", "country": "US", "lat": 25.7959, "lon": -80.2870, "risk": 48},
    "SFO": {"city": "San Francisco", "country": "US", "lat": 37.6213, "lon": -122.3790, "risk": 32},
    "YYZ": {"city": "Toronto", "country": "CA", "lat": 43.6777, "lon": -79.6248, "risk": 30},
    "MEX": {"city": "Mexico City", "country": "MX", "lat": 19.4361, "lon": -99.0719, "risk": 52},

    # Europe
    "LHR": {"city": "London", "country": "GB", "lat": 51.4700, "lon": -0.4543, "risk": 55},
    "CDG": {"city": "Paris", "country": "FR", "lat": 49.0097, "lon": 2.5479, "risk": 50},
    "FRA": {"city": "Frankfurt", "country": "DE", "lat": 50.0379, "lon": 8.5622, "risk": 45},
    "AMS": {"city": "Amsterdam", "country": "NL", "lat": 52.3105, "lon": 4.7683, "risk": 42},
    "MAD": {"city": "Madrid", "country": "ES", "lat": 40.4983, "lon": -3.5676, "risk": 48},
    "FCO": {"city": "Rome", "country": "IT", "lat": 41.8003, "lon": 12.2389, "risk": 52},
    "IST": {"city": "Istanbul", "country": "TR", "lat": 41.2753, "lon": 28.7519, "risk": 58},

    # Asia-Pacific
    "HND": {"city": "Tokyo", "country": "JP", "lat": 35.5494, "lon": 139.7798, "risk": 35},
    "NRT": {"city": "Tokyo Narita", "country": "JP", "lat": 35.7720, "lon": 140.3929, "risk": 35},
    "PEK": {"city": "Beijing", "country": "CN", "lat": 40.0799, "lon": 116.6031, "risk": 65},
    "PVG": {"city": "Shanghai", "country": "CN", "lat": 31.1443, "lon": 121.8083, "risk": 62},
    "HKG": {"city": "Hong Kong", "country": "HK", "lat": 22.3080, "lon": 113.9185, "risk": 55},
    "SIN": {"city": "Singapore", "country": "SG", "lat": 1.3644, "lon": 103.9915, "risk": 40},
    "ICN": {"city": "Seoul", "country": "KR", "lat": 37.4602, "lon": 126.4407, "risk": 38},
    "BKK": {"city": "Bangkok", "country": "TH", "lat": 13.6900, "lon": 100.7501, "risk": 50},
    "SYD": {"city": "Sydney", "country": "AU", "lat": -33.9399, "lon": 151.1753, "risk": 28},
    "DEL": {"city": "Delhi", "country": "IN", "lat": 28.5562, "lon": 77.1000, "risk": 60},
    "DXB": {"city": "Dubai", "country": "AE", "lat": 25.2532, "lon": 55.3657, "risk": 45},

    # South America
    "GRU": {"city": "São Paulo", "country": "BR", "lat": -23.4356, "lon": -46.4731, "risk": 55},
    "EZE": {"city": "Buenos Aires", "country": "AR", "lat": -34.8222, "lon": -58.5358, "risk": 42},
    "SCL": {"city": "Santiago", "country": "CL", "lat": -33.3930, "lon": -70.7858, "risk": 38},
    "BOG": {"city": "Bogotá", "country": "CO", "lat": 4.7016, "lon": -74.1469, "risk": 48},

    # Africa/Middle East
    "JNB": {"city": "Johannesburg", "country": "ZA", "lat": -26.1392, "lon": 28.2460, "risk": 52},
    "CAI": {"city": "Cairo", "country": "EG", "lat": 30.1219, "lon": 31.4056, "risk": 55},
    "DOH": {"city": "Doha", "country": "QA", "lat": 25.2731, "lon": 51.6081, "risk": 40},
}


def generate_synthetic_arcs(
    target_date: date,
    min_passengers: int = 0,
    origin_country: Optional[str] = None,
    dest_country: Optional[str] = None,
) -> List[FlightArc]:
    """Generate synthetic flight arc data for visualization."""
    arcs = []
    hubs = list(AIRPORT_HUBS.items())

    # Use date as seed for consistent results
    seed = int(target_date.strftime("%Y%m%d"))
    random.seed(seed)

    # Generate routes between major hubs
    for i, (dep_code, dep_info) in enumerate(hubs):
        # Filter by origin country if specified
        if origin_country and dep_info["country"] != origin_country:
            continue

        # Each hub connects to 5-10 other hubs
        num_destinations = random.randint(5, 10)
        destinations = random.sample(hubs, min(num_destinations, len(hubs)))

        for arr_code, arr_info in destinations:
            if arr_code == dep_code:
                continue

            # Filter by destination country if specified
            if dest_country and arr_info["country"] != dest_country:
                continue

            # Generate passenger estimate (varies by route importance)
            base_pax = random.randint(200, 2000)
            # Major hub connections get more traffic
            if dep_code in ["JFK", "LHR", "DXB", "SIN"] or arr_code in ["JFK", "LHR", "DXB", "SIN"]:
                base_pax *= 2

            if base_pax < min_passengers:
                continue

            # Generate flight count
            flights = max(1, base_pax // 180)  # Avg 180 pax per flight

            # Create arc ID
            arc_id = hashlib.md5(
                f"{dep_code}-{arr_code}-{target_date}".encode()
            ).hexdigest()[:12]

            # Add some risk variation
            origin_risk = dep_info["risk"] + random.uniform(-10, 10)
            origin_risk = max(0, min(100, origin_risk))

            arcs.append(FlightArc(
                arc_id=f"arc_{arc_id}",
                origin_lat=dep_info["lat"],
                origin_lon=dep_info["lon"],
                origin_name=dep_info["city"],
                origin_country=dep_info["country"],
                dest_lat=arr_info["lat"],
                dest_lon=arr_info["lon"],
                dest_name=arr_info["city"],
                dest_country=arr_info["country"],
                pax_estimate=base_pax,
                flight_count=flights,
                origin_risk=origin_risk,
            ))

    random.seed()  # Reset seed
    return arcs


@router.get("/arcs", response_model=FlightArcsResponse)
async def get_flight_arcs(
    date_str: Optional[str] = Query(None, alias="date", description="Date in YYYY-MM-DD format"),
    min_pax: int = Query(0, description="Minimum passengers to include"),
    origin_country: Optional[str] = Query(None, description="Filter by origin country code"),
    dest_country: Optional[str] = Query(None, description="Filter by destination country code"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get flight arcs for visualization.

    Returns flight routes between major hubs with passenger estimates
    and origin risk scores.
    """
    if date_str:
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        target_date = date.today()

    # Query real flight data from database
    query = """
        SELECT
            va.arc_id,
            ol.latitude as origin_lat,
            ol.longitude as origin_lon,
            ol.name as origin_name,
            ol.country as origin_country,
            dl.latitude as dest_lat,
            dl.longitude as dest_lon,
            dl.name as dest_name,
            dl.country as dest_country,
            va.passenger_volume as pax_estimate,
            va.flight_count,
            COALESCE(rs.risk_score, 50) as origin_risk
        FROM vector_arcs va
        JOIN location_nodes ol ON va.origin_location_id = ol.location_id
        JOIN location_nodes dl ON va.dest_location_id = dl.location_id
        LEFT JOIN risk_scores rs ON va.origin_location_id = rs.location_id
        WHERE va.date >= :start_date AND va.date <= :end_date
          AND va.passenger_volume >= :min_pax
    """

    params = {
        "start_date": target_date - timedelta(days=1),
        "end_date": target_date,
        "min_pax": min_pax,
    }

    if origin_country:
        query += " AND ol.iso_code = :origin_country"
        params["origin_country"] = origin_country

    if dest_country:
        query += " AND dl.iso_code = :dest_country"
        params["dest_country"] = dest_country

    query += " ORDER BY va.passenger_volume DESC LIMIT 500"

    result = await db.execute(text(query), params)
    rows = result.fetchall()

    # If no real data, fall back to synthetic with warning
    if not rows:
        # Log warning that we're using synthetic data
        import logging
        logging.warning(f"No flight data in database for {target_date}, using synthetic fallback")
        arcs = generate_synthetic_arcs(
            target_date=target_date,
            min_passengers=min_pax,
            origin_country=origin_country,
            dest_country=dest_country,
        )
        return FlightArcsResponse(
            arcs=arcs,
            total=len(arcs),
            date=target_date.isoformat(),
        )

    arcs = [
        FlightArc(
            arc_id=row.arc_id,
            origin_lat=float(row.origin_lat),
            origin_lon=float(row.origin_lon),
            origin_name=row.origin_name,
            origin_country=row.origin_country,
            dest_lat=float(row.dest_lat),
            dest_lon=float(row.dest_lon),
            dest_name=row.dest_name,
            dest_country=row.dest_country,
            pax_estimate=row.pax_estimate,
            flight_count=row.flight_count,
            origin_risk=float(row.origin_risk) if row.origin_risk else None,
        )
        for row in rows
    ]

    return FlightArcsResponse(
        arcs=arcs,
        total=len(arcs),
        date=target_date.isoformat(),
    )


@router.get("/import-pressure/{location_id}", response_model=ImportPressureResponse)
async def get_import_pressure(
    location_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Calculate import pressure for a location.

    Import pressure is based on incoming flight volume weighted by
    origin location risk scores.
    """
    # Query incoming flights to this location from database
    query = """
        SELECT
            ol.name as origin_name,
            ol.country as origin_country,
            ol.iso_code as origin_iso,
            SUM(va.passenger_volume) as passengers,
            COALESCE(AVG(rs.risk_score), 50) as origin_risk
        FROM vector_arcs va
        JOIN location_nodes ol ON va.origin_location_id = ol.location_id
        LEFT JOIN risk_scores rs ON va.origin_location_id = rs.location_id
        WHERE va.dest_location_id = :location_id
          AND va.date >= CURRENT_DATE - INTERVAL '7 days'
        GROUP BY ol.name, ol.country, ol.iso_code
        ORDER BY SUM(va.passenger_volume) DESC
        LIMIT 20
    """

    result = await db.execute(text(query), {"location_id": location_id})
    rows = result.fetchall()

    # If no real data, fall back to synthetic with warning
    if not rows:
        logging.warning(f"No flight data for {location_id}, using synthetic fallback")

        # Extract country from location_id for synthetic fallback
        parts = location_id.split("_")
        country_code = parts[1].upper() if len(parts) >= 2 else "US"

        target_hub = None
        for code, info in AIRPORT_HUBS.items():
            if info["country"] == country_code:
                target_hub = (code, info)
                break

        if not target_hub:
            target_hub = ("JFK", AIRPORT_HUBS["JFK"])

        arcs = generate_synthetic_arcs(
            target_date=date.today(),
            dest_country=target_hub[1]["country"],
        )

        sources = []
        total_pressure = 0.0
        for arc in arcs:
            if arc.dest_country == target_hub[1]["country"]:
                risk_contribution = (arc.pax_estimate * (arc.origin_risk or 50)) / 10000
                total_pressure += risk_contribution
                sources.append(ImportPressureSource(
                    origin_name=arc.origin_name,
                    origin_country=arc.origin_country,
                    passengers=arc.pax_estimate,
                    risk_contribution=risk_contribution,
                ))

        import_pressure = min(100, total_pressure / max(1, len(sources)) * 2)
        sources.sort(key=lambda x: x.risk_contribution, reverse=True)

        return ImportPressureResponse(
            location_id=location_id,
            import_pressure=import_pressure,
            top_sources=sources[:10],
            timestamp=datetime.utcnow().isoformat() + "Z",
        )

    # Calculate from real data
    total_pressure = 0.0
    total_passengers = 0
    sources: List[ImportPressureSource] = []

    for row in rows:
        passengers = int(row.passengers)
        origin_risk = float(row.origin_risk)
        risk_contribution = (passengers * origin_risk) / 10000

        total_pressure += risk_contribution
        total_passengers += passengers

        sources.append(ImportPressureSource(
            origin_name=row.origin_name,
            origin_country=row.origin_country,
            passengers=passengers,
            risk_contribution=round(risk_contribution, 2),
        ))

    # Normalize to 0-100 scale
    import_pressure = min(100, total_pressure / max(1, len(sources)) * 2)

    return ImportPressureResponse(
        location_id=location_id,
        import_pressure=round(import_pressure, 1),
        top_sources=sources[:10],
        timestamp=datetime.utcnow().isoformat() + "Z",
    )
