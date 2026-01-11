"""
Data source status API endpoint.

Provides visibility into what data sources are connected and whether
real or synthetic data is being served.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

router = APIRouter(prefix="/api/status", tags=["status"])


class DataSourceStatus(BaseModel):
    source_id: str
    source_name: str
    status: str  # "connected", "stale", "no_data", "synthetic"
    last_ingestion: Optional[datetime] = None
    record_count: int = 0
    coverage: Optional[str] = None
    data_type: str  # "wastewater", "flight", "genomic"


class SystemStatus(BaseModel):
    overall_status: str  # "healthy", "degraded", "synthetic_only"
    real_data_sources: int
    synthetic_fallback_active: bool
    last_checked: datetime
    sources: List[DataSourceStatus]
    warnings: List[str]


# Expected data sources from DATA_SOURCES.md
EXPECTED_SOURCES = {
    "CDC_NWSS": {"name": "CDC NWSS (US)", "type": "wastewater", "coverage": "~1,300 sites, 50 states"},
    "UKHSA": {"name": "UK UKHSA", "type": "wastewater", "coverage": "UK nations"},
    "RIVM": {"name": "Netherlands RIVM", "type": "wastewater", "coverage": "Netherlands sites"},
    "RKI": {"name": "Germany RKI", "type": "wastewater", "coverage": "16 German states"},
    "FR_DATAGOUV": {"name": "France data.gouv", "type": "wastewater", "coverage": "French regions"},
    "NIID": {"name": "Japan NIID", "type": "wastewater", "coverage": "47 prefectures"},
    "AU_HEALTH": {"name": "Australia Health", "type": "wastewater", "coverage": "8 states/territories"},
    "AVIATIONSTACK": {"name": "AviationStack", "type": "flight", "coverage": "Global routes"},
    "NEXTSTRAIN": {"name": "Nextstrain", "type": "genomic", "coverage": "Global sequences"},
}


@router.get("", response_model=SystemStatus)
async def get_system_status(db: AsyncSession = Depends(get_db)):
    """
    Get comprehensive data source status.

    Shows which data sources are connected, when they were last updated,
    and whether synthetic fallbacks are active.
    """
    sources: List[DataSourceStatus] = []
    warnings: List[str] = []
    now = datetime.utcnow()
    stale_threshold = timedelta(days=7)

    # Check surveillance events by source
    events_query = """
        SELECT
            data_source,
            COUNT(*) as record_count,
            MAX(timestamp) as last_timestamp
        FROM surveillance_events
        GROUP BY data_source
    """

    try:
        result = await db.execute(text(events_query))
        events_by_source = {
            row.data_source: {
                "count": row.record_count,
                "last": row.last_timestamp
            }
            for row in result.fetchall()
        }
    except Exception as e:
        events_by_source = {}
        warnings.append(f"Could not query surveillance_events: {str(e)}")

    # Check flight data
    flights_query = """
        SELECT
            COUNT(*) as record_count,
            MAX(date) as last_date
        FROM vector_arcs
    """

    try:
        result = await db.execute(text(flights_query))
        row = result.fetchone()
        flight_data = {
            "count": row.record_count if row else 0,
            "last": row.last_date if row else None
        }
    except Exception as e:
        flight_data = {"count": 0, "last": None}
        warnings.append(f"Could not query vector_arcs: {str(e)}")

    # Build source status list
    for source_id, info in EXPECTED_SOURCES.items():
        if info["type"] == "flight":
            count = flight_data["count"]
            last = flight_data["last"]
        else:
            source_data = events_by_source.get(source_id, {"count": 0, "last": None})
            count = source_data["count"]
            last = source_data["last"]

        # Determine status
        if count == 0:
            status = "no_data"
            warnings.append(f"{info['name']}: No data in database - synthetic fallback will be used")
        elif last and (now - last) > stale_threshold:
            status = "stale"
            warnings.append(f"{info['name']}: Data is stale (last update: {last})")
        else:
            status = "connected"

        sources.append(DataSourceStatus(
            source_id=source_id,
            source_name=info["name"],
            status=status,
            last_ingestion=last,
            record_count=count,
            coverage=info["coverage"],
            data_type=info["type"],
        ))

    # Calculate overall status
    connected_count = sum(1 for s in sources if s.status == "connected")
    total_sources = len(sources)

    if connected_count == 0:
        overall_status = "synthetic_only"
        warnings.insert(0, "⚠️ NO REAL DATA: All endpoints are serving synthetic data")
    elif connected_count < total_sources * 0.5:
        overall_status = "degraded"
        warnings.insert(0, f"⚠️ DEGRADED: Only {connected_count}/{total_sources} sources connected")
    else:
        overall_status = "healthy"

    synthetic_active = any(s.status in ("no_data", "stale") for s in sources)

    return SystemStatus(
        overall_status=overall_status,
        real_data_sources=connected_count,
        synthetic_fallback_active=synthetic_active,
        last_checked=now,
        sources=sources,
        warnings=warnings,
    )


@router.get("/database")
async def get_database_status(db: AsyncSession = Depends(get_db)):
    """
    Get database table row counts to verify data population.
    """
    tables = [
        "location_nodes",
        "surveillance_events",
        "vector_arcs",
        "variants",
        "risk_scores",
    ]

    counts = {}
    for table in tables:
        try:
            result = await db.execute(text(f"SELECT COUNT(*) FROM {table}"))
            row = result.fetchone()
            counts[table] = row[0] if row else 0
        except Exception as e:
            counts[table] = f"Error: {str(e)}"

    total_records = sum(c for c in counts.values() if isinstance(c, int))

    return {
        "database_populated": total_records > 0,
        "total_records": total_records,
        "tables": counts,
        "checked_at": datetime.utcnow().isoformat(),
    }


@router.get("/ingestion-log")
async def get_recent_ingestion_log(
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """
    Get recent ingestion activity to verify Cloud Functions are running.
    """
    # Check for recent data by source
    query = """
        SELECT
            data_source,
            DATE(timestamp) as ingestion_date,
            COUNT(*) as records_ingested
        FROM surveillance_events
        WHERE timestamp > NOW() - INTERVAL '30 days'
        GROUP BY data_source, DATE(timestamp)
        ORDER BY ingestion_date DESC, data_source
        LIMIT :limit
    """

    try:
        result = await db.execute(text(query), {"limit": limit})
        rows = result.fetchall()

        log = [
            {
                "source": row.data_source,
                "date": row.ingestion_date.isoformat() if row.ingestion_date else None,
                "records": row.records_ingested,
            }
            for row in rows
        ]

        return {
            "recent_activity": len(log) > 0,
            "entries": log,
            "message": "Ingestion appears active" if log else "No recent ingestion activity detected",
        }

    except Exception as e:
        return {
            "recent_activity": False,
            "entries": [],
            "error": str(e),
            "message": "Could not query ingestion log - database may not be initialized",
        }
