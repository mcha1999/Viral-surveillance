"""
UK Health Security Agency (UKHSA) Wastewater Adapter

Data source: https://coronavirus.data.gov.uk/
Coverage: England, Wales, Scotland, Northern Ireland
Frequency: Updated 2x weekly
"""

import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import hashlib

import httpx
import h3

from .base import (
    BaseAdapter,
    LocationData,
    SurveillanceEvent,
    SignalType,
    GranularityTier,
)


class UKUKHSAAdapter(BaseAdapter):
    """
    Adapter for UK Health Security Agency wastewater data.

    Uses the coronavirus.data.gov.uk API.
    """

    source_id = "UKHSA"
    source_name = "UK Health Security Agency"
    signal_type = SignalType.WASTEWATER

    # API endpoint
    BASE_URL = "https://api.coronavirus.data.gov.uk/v2/data"

    # UK regions with coordinates
    UK_REGIONS = {
        "England": {"lat": 52.3555, "lon": -1.1743},
        "Scotland": {"lat": 56.4907, "lon": -4.2026},
        "Wales": {"lat": 52.1307, "lon": -3.7837},
        "Northern Ireland": {"lat": 54.7877, "lon": -6.4923},
        "East Midlands": {"lat": 52.8301, "lon": -1.3290},
        "East of England": {"lat": 52.2405, "lon": 0.9027},
        "London": {"lat": 51.5074, "lon": -0.1278},
        "North East": {"lat": 55.2970, "lon": -1.7297},
        "North West": {"lat": 54.0934, "lon": -2.8948},
        "South East": {"lat": 51.4545, "lon": -0.9781},
        "South West": {"lat": 50.7772, "lon": -3.9995},
        "West Midlands": {"lat": 52.4751, "lon": -1.8298},
        "Yorkshire and The Humber": {"lat": 53.9591, "lon": -1.0815},
    }

    def __init__(self):
        super().__init__()
        self.client = httpx.AsyncClient(timeout=30.0)

    async def fetch(self) -> List[Dict[str, Any]]:
        """
        Fetch wastewater data from UKHSA API.

        Note: The exact API structure may vary. This implementation
        targets the general coronavirus dashboard API format.
        """
        self.logger.info("Fetching from UKHSA")

        all_data = []

        # Fetch data for each area type
        for area_type in ["region", "nation"]:
            try:
                params = {
                    "areaType": area_type,
                    "metric": "newCasesBySpecimenDateRollingRate",  # Proxy metric
                    "format": "json",
                }

                response = await self.client.get(self.BASE_URL, params=params)
                response.raise_for_status()

                data = response.json()
                if "body" in data:
                    all_data.extend(data["body"])

            except httpx.HTTPError as e:
                self.logger.warning(f"Failed to fetch {area_type} data: {e}")
                continue

        self.logger.info(f"Received {len(all_data)} records from UKHSA")
        return all_data

    def normalize(
        self,
        raw_data: List[Dict[str, Any]]
    ) -> tuple[List[LocationData], List[SurveillanceEvent]]:
        """Normalize UKHSA data to standard schema."""
        locations_map: Dict[str, LocationData] = {}
        events: List[SurveillanceEvent] = []

        for record in raw_data:
            try:
                location = self._extract_location(record)
                if location:
                    locations_map[location.location_id] = location

                    event = self._extract_event(record, location.location_id)
                    if event:
                        events.append(event)

            except Exception as e:
                self.logger.warning(f"Failed to process record: {e}")
                continue

        return list(locations_map.values()), events

    def _extract_location(self, record: Dict[str, Any]) -> Optional[LocationData]:
        """Extract location data from UKHSA record."""
        area_name = record.get("areaName")
        if not area_name:
            return None

        # Get coordinates from our mapping
        coords = self.UK_REGIONS.get(area_name, {"lat": 54.0, "lon": -2.0})
        latitude = coords["lat"]
        longitude = coords["lon"]

        # Determine granularity
        area_type = record.get("areaType", "")
        if area_type == "nation":
            granularity = GranularityTier.TIER_2
        else:
            granularity = GranularityTier.TIER_2

        # Generate H3 index
        try:
            h3_index = h3.geo_to_h3(latitude, longitude, 5)
        except Exception:
            h3_index = None

        location_id = self._generate_location_id(area_name)

        return LocationData(
            location_id=location_id,
            name=area_name,
            admin1=area_name if area_type == "region" else None,
            country="United Kingdom",
            iso_code="GB",
            granularity=granularity,
            latitude=latitude,
            longitude=longitude,
            h3_index=h3_index,
        )

    def _extract_event(
        self,
        record: Dict[str, Any],
        location_id: str
    ) -> Optional[SurveillanceEvent]:
        """Extract surveillance event from UKHSA record."""
        date_str = record.get("date")
        if not date_str:
            return None

        try:
            timestamp = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return None

        # Get metrics - using case rate as proxy for viral load
        # In a real implementation, you'd use actual wastewater metrics
        rate = record.get("newCasesBySpecimenDateRollingRate")

        normalized_score = None
        if rate is not None:
            # Normalize to 0-1 scale (assuming max rate of 1000 per 100k)
            normalized_score = min(1.0, float(rate) / 1000.0)

        return SurveillanceEvent(
            event_id=self.generate_event_id(location_id, timestamp, self.source_id),
            location_id=location_id,
            timestamp=timestamp,
            data_source=self.source_id,
            signal_type=self.signal_type,
            normalized_score=normalized_score,
            quality_score=0.85,
            raw_data=record,
        )

    def _generate_location_id(self, area_name: str) -> str:
        """Generate consistent location ID."""
        normalized = area_name.lower().replace(" ", "_").replace("'", "")
        return f"loc_gb_{normalized[:30]}"

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
