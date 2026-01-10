"""
CDC National Wastewater Surveillance System (NWSS) Adapter

Data source: https://data.cdc.gov/resource/g653-rqe2.json
Coverage: ~1,300 sites across US
Frequency: Updated 2x weekly (Tuesday/Thursday)
"""

import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import hashlib

import h3
from sodapy import Socrata

from .base import (
    BaseAdapter,
    LocationData,
    SurveillanceEvent,
    SignalType,
    GranularityTier,
)


class CDCNWSSAdapter(BaseAdapter):
    """
    Adapter for CDC National Wastewater Surveillance System.

    Fetches wastewater viral load data from CDC's Socrata API.
    """

    source_id = "CDC_NWSS"
    source_name = "CDC National Wastewater Surveillance System"
    signal_type = SignalType.WASTEWATER

    # Socrata API details
    DOMAIN = "data.cdc.gov"
    DATASET_ID = "g653-rqe2"

    # Historical max for normalization (copies/L)
    # This should be calibrated based on actual data
    HISTORICAL_MAX_LOAD = 1_000_000

    def __init__(self, app_token: Optional[str] = None):
        super().__init__()
        self.app_token = app_token or os.getenv("SOCRATA_APP_TOKEN")
        self.client = Socrata(self.DOMAIN, self.app_token)

    async def fetch(self) -> List[Dict[str, Any]]:
        """
        Fetch wastewater data from CDC Socrata API.

        Returns latest data for all monitoring sites.
        """
        self.logger.info("Fetching from CDC NWSS")

        # Query parameters
        # Get data from last 30 days to capture updates
        results = self.client.get(
            self.DATASET_ID,
            limit=10000,  # Adjust based on expected volume
            order="date_start DESC",
            where="date_start >= date_sub_d(date_extract_y(now()), 30)",
        )

        self.logger.info("Received records from CDC", count=len(results))
        return results

    def normalize(
        self,
        raw_data: List[Dict[str, Any]]
    ) -> tuple[List[LocationData], List[SurveillanceEvent]]:
        """
        Normalize CDC NWSS data to standard schema.

        Handles:
        - Location extraction from WWTP info
        - Viral load normalization
        - Percent change (velocity) extraction
        """
        locations_map: Dict[str, LocationData] = {}
        events: List[SurveillanceEvent] = []

        for record in raw_data:
            try:
                # Extract location
                location = self._extract_location(record)
                if location:
                    locations_map[location.location_id] = location

                    # Extract event
                    event = self._extract_event(record, location.location_id)
                    if event:
                        events.append(event)

            except Exception as e:
                self.logger.warning(
                    "Failed to process record",
                    error=str(e),
                    record_id=record.get("wwtp_id"),
                )
                continue

        locations = list(locations_map.values())
        return locations, events

    def _extract_location(self, record: Dict[str, Any]) -> Optional[LocationData]:
        """Extract location data from a CDC record."""
        wwtp_id = record.get("wwtp_id")
        if not wwtp_id:
            return None

        # Get coordinates - CDC provides centroid lat/lon
        try:
            latitude = float(record.get("wwtp_latitude", 0))
            longitude = float(record.get("wwtp_longitude", 0))
        except (TypeError, ValueError):
            latitude = 0
            longitude = 0

        if latitude == 0 and longitude == 0:
            # Try to get from county centroid
            # For now, skip records without coordinates
            return None

        # Generate H3 index at resolution 7 (~5km hexagons)
        try:
            h3_index = h3.geo_to_h3(latitude, longitude, 7)
        except Exception:
            h3_index = None

        # Build location name
        county = record.get("county_names", "Unknown County")
        state = record.get("state", "")

        # Get population served
        try:
            population = int(float(record.get("population_served", 0)))
        except (TypeError, ValueError):
            population = None

        return LocationData(
            location_id=self._generate_site_id(wwtp_id),
            name=f"{county}",
            admin1=state,
            country="United States",
            iso_code="US",
            granularity=GranularityTier.TIER_1,  # Site-level data
            latitude=latitude,
            longitude=longitude,
            catchment_population=population,
            h3_index=h3_index,
        )

    def _extract_event(
        self,
        record: Dict[str, Any],
        location_id: str
    ) -> Optional[SurveillanceEvent]:
        """Extract surveillance event from a CDC record."""
        # Parse date
        date_str = record.get("date_start")
        if not date_str:
            return None

        try:
            timestamp = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            try:
                timestamp = datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                return None

        # Get viral load metrics
        # CDC provides percent change rather than raw copies/L
        raw_load = None
        normalized_score = None
        velocity = None

        # Percent change 15-day
        ptc_15d = record.get("ptc_15d")
        if ptc_15d and ptc_15d not in ["", "null"]:
            try:
                velocity = float(ptc_15d) / 100  # Convert percentage to decimal
            except (TypeError, ValueError):
                pass

        # Detection proportion (0-1)
        detect_prop = record.get("detect_prop_15d")
        if detect_prop and detect_prop not in ["", "null"]:
            try:
                normalized_score = float(detect_prop)
                # Clamp to 0-1
                normalized_score = max(0, min(1, normalized_score))
            except (TypeError, ValueError):
                pass

        # Calculate quality score based on data completeness
        quality_score = 0.0
        if normalized_score is not None:
            quality_score += 0.5
        if velocity is not None:
            quality_score += 0.3
        if record.get("population_served"):
            quality_score += 0.2

        return SurveillanceEvent(
            event_id=self.generate_event_id(location_id, timestamp, self.source_id),
            location_id=location_id,
            timestamp=timestamp,
            data_source=self.source_id,
            signal_type=self.signal_type,
            raw_load=raw_load,
            normalized_score=normalized_score,
            velocity=velocity,
            quality_score=quality_score,
            raw_data=record,  # Keep original for debugging
        )

    def _generate_site_id(self, wwtp_id: str) -> str:
        """Generate a consistent location ID from WWTP ID."""
        # Hash to keep ID length manageable
        hash_part = hashlib.md5(wwtp_id.encode()).hexdigest()[:8]
        return f"loc_us_wwtp_{hash_part}"


# Cloud Function entry point
def ingest_cdc_nwss(request):
    """
    Cloud Function entry point for CDC NWSS ingestion.

    Triggered by Cloud Scheduler.
    """
    import asyncio
    import json
    from google.cloud import secretmanager

    # Get secrets
    client = secretmanager.SecretManagerServiceClient()
    project_id = os.getenv("GCP_PROJECT")

    # Get Socrata token
    token_name = f"projects/{project_id}/secrets/viral-weather-socrata-token/versions/latest"
    try:
        response = client.access_secret_version(request={"name": token_name})
        socrata_token = response.payload.data.decode("UTF-8")
    except Exception:
        socrata_token = None

    # Run adapter
    adapter = CDCNWSSAdapter(app_token=socrata_token)
    result = asyncio.run(adapter.run())

    # Log result
    print(json.dumps({
        "source_id": result.source_id,
        "success": result.success,
        "records_fetched": result.records_fetched,
        "records_processed": result.records_processed,
        "locations_count": len(result.locations),
        "events_count": len(result.events),
        "duration_seconds": result.duration_seconds,
        "error": result.error,
    }))

    if not result.success:
        return json.dumps({"error": result.error}), 500

    # TODO: Store results in database
    # For now, just return summary
    return json.dumps({
        "status": "success",
        "locations": len(result.locations),
        "events": len(result.events),
    }), 200
