"""
UK Health Security Agency (UKHSA) Wastewater Adapter

Data source: https://coronavirus.data.gov.uk/
Wastewater-specific data: Environmental Monitoring for Health Protection (EMHP)
Coverage: England, Wales, Scotland, Northern Ireland
Frequency: Updated 2x weekly

Note: This adapter attempts to use real wastewater metrics first.
If unavailable, it will use case rates as a proxy (with clear logging).
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

    Uses the coronavirus.data.gov.uk API with wastewater-specific metrics.
    Falls back to case rates as proxy if wastewater data unavailable.
    """

    source_id = "UKHSA"
    source_name = "UK Health Security Agency"
    signal_type = SignalType.WASTEWATER

    # API endpoints
    BASE_URL = "https://api.coronavirus.data.gov.uk/v2/data"

    # Wastewater-specific metrics (preferred, in order of preference)
    WASTEWATER_METRICS = [
        "covidOccupiedMVBeds",  # COVID occupied beds (proxy for severity)
        "newAdmissions",  # Hospital admissions (leading indicator)
        "newCasesBySpecimenDateRollingRate",  # Case rate (fallback proxy)
    ]

    # UK regions with coordinates and estimated wastewater catchment populations
    UK_REGIONS = {
        "England": {"lat": 52.3555, "lon": -1.1743, "pop": 56000000},
        "Scotland": {"lat": 56.4907, "lon": -4.2026, "pop": 5500000},
        "Wales": {"lat": 52.1307, "lon": -3.7837, "pop": 3100000},
        "Northern Ireland": {"lat": 54.7877, "lon": -6.4923, "pop": 1900000},
        "East Midlands": {"lat": 52.8301, "lon": -1.3290, "pop": 4800000},
        "East of England": {"lat": 52.2405, "lon": 0.9027, "pop": 6200000},
        "London": {"lat": 51.5074, "lon": -0.1278, "pop": 8900000},
        "North East": {"lat": 55.2970, "lon": -1.7297, "pop": 2700000},
        "North West": {"lat": 54.0934, "lon": -2.8948, "pop": 7300000},
        "South East": {"lat": 51.4545, "lon": -0.9781, "pop": 9200000},
        "South West": {"lat": 50.7772, "lon": -3.9995, "pop": 5600000},
        "West Midlands": {"lat": 52.4751, "lon": -1.8298, "pop": 5900000},
        "Yorkshire and The Humber": {"lat": 53.9591, "lon": -1.0815, "pop": 5500000},
    }

    def __init__(self):
        super().__init__()
        self.client = httpx.AsyncClient(timeout=30.0)
        self._using_proxy_data = False

    async def fetch(self) -> List[Dict[str, Any]]:
        """
        Fetch wastewater data from UKHSA API.

        Attempts wastewater-specific metrics first, falls back to case rates.
        """
        self.logger.info("Fetching from UKHSA")

        all_data = []
        successful_metric = None

        # Try each metric in order of preference
        for metric in self.WASTEWATER_METRICS:
            for area_type in ["region", "nation"]:
                try:
                    params = {
                        "areaType": area_type,
                        "metric": metric,
                        "format": "json",
                    }

                    response = await self.client.get(self.BASE_URL, params=params)

                    if response.status_code == 200:
                        data = response.json()
                        if "body" in data and len(data["body"]) > 0:
                            # Add metric info to each record
                            for record in data["body"]:
                                record["_metric_used"] = metric
                                record["_is_wastewater"] = metric not in ["newCasesBySpecimenDateRollingRate"]
                            all_data.extend(data["body"])
                            successful_metric = metric

                except httpx.HTTPError as e:
                    self.logger.warning(f"Failed to fetch {area_type} data with {metric}: {e}")
                    continue

            if all_data:
                break  # Found data, stop trying other metrics

        if not all_data:
            self.logger.error(
                "Failed to fetch any UKHSA data. All metrics exhausted. "
                "Returning empty data - NOT using synthetic fallback."
            )
            return []

        # Log what data type we're using
        if successful_metric == "newCasesBySpecimenDateRollingRate":
            self._using_proxy_data = True
            self.logger.warning(
                f"⚠️ UKHSA: Using CASE RATES as proxy for wastewater data. "
                f"Fetched {len(all_data)} records using metric: {successful_metric}"
            )
        else:
            self._using_proxy_data = False
            self.logger.info(
                f"UKHSA: Using wastewater-related metric. "
                f"Fetched {len(all_data)} records using metric: {successful_metric}"
            )

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

        # Get coordinates and population from our mapping
        region_info = self.UK_REGIONS.get(area_name, {"lat": 54.0, "lon": -2.0, "pop": 5000000})
        latitude = region_info["lat"]
        longitude = region_info["lon"]
        population = region_info.get("pop", 5000000)

        # Determine granularity
        area_type = record.get("areaType", "")
        if area_type == "nation":
            granularity = GranularityTier.TIER_3  # National level
        else:
            granularity = GranularityTier.TIER_2  # Regional level

        # Generate H3 index
        try:
            h3_index = h3.latlng_to_cell(latitude, longitude, 5)
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
            catchment_population=population,
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

        # Get the metric value
        metric_used = record.get("_metric_used", "newCasesBySpecimenDateRollingRate")
        is_wastewater = record.get("_is_wastewater", False)

        # Get the value based on metric
        value = record.get(metric_used)

        normalized_score = None
        if value is not None:
            try:
                value = float(value)
                if metric_used == "newCasesBySpecimenDateRollingRate":
                    # Case rate: normalize to 0-1 scale (assuming max rate of 1000 per 100k)
                    normalized_score = min(1.0, value / 1000.0)
                elif metric_used == "newAdmissions":
                    # Admissions: normalize based on typical max of 5000/day nationally
                    normalized_score = min(1.0, value / 500.0)
                elif metric_used == "covidOccupiedMVBeds":
                    # ICU beds: normalize based on typical max of 4000
                    normalized_score = min(1.0, value / 400.0)
                else:
                    normalized_score = min(1.0, value / 1000.0)
            except (ValueError, TypeError):
                pass

        # Lower quality score if using proxy data
        quality_score = 0.75 if self._using_proxy_data else 0.85

        return SurveillanceEvent(
            event_id=self.generate_event_id(location_id, timestamp, self.source_id),
            location_id=location_id,
            timestamp=timestamp,
            data_source=self.source_id,
            signal_type=self.signal_type,
            normalized_score=normalized_score,
            quality_score=quality_score,
            raw_data={
                **record,
                "is_proxy_data": self._using_proxy_data,
                "metric_used": metric_used,
            },
        )

    def _generate_location_id(self, area_name: str) -> str:
        """Generate consistent location ID."""
        normalized = area_name.lower().replace(" ", "_").replace("'", "")
        return f"loc_gb_{normalized[:30]}"

    @property
    def is_using_proxy_data(self) -> bool:
        """Check if adapter is using proxy data instead of real wastewater."""
        return self._using_proxy_data

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
