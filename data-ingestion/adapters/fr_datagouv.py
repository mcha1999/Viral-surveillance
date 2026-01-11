"""
France data.gouv.fr Wastewater Adapter

Data source: https://www.data.gouv.fr/
Coverage: French regions
Frequency: Updated weekly
Granularity: Tier 2 (Region level)
"""

import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import csv
import io

import httpx
import h3

from .base import (
    BaseAdapter,
    LocationData,
    SurveillanceEvent,
    SignalType,
    GranularityTier,
)


class FRDataGouvAdapter(BaseAdapter):
    """
    Adapter for French government wastewater surveillance data.

    Fetches from data.gouv.fr open data portal.
    """

    source_id = "FR_DATAGOUV"
    source_name = "France data.gouv.fr"
    signal_type = SignalType.WASTEWATER

    # Data URL (Obépine/Sum'Eau network data)
    DATA_URL = "https://www.data.gouv.fr/fr/datasets/r/7e45d5a3-3a5e-4e3d-b3f1-7e8c5c8f2e3a"

    # French regions with coordinates
    FR_REGIONS = {
        "Île-de-France": {"lat": 48.8499, "lon": 2.6370, "pop": 12278000},
        "Auvergne-Rhône-Alpes": {"lat": 45.4473, "lon": 4.3859, "pop": 8043000},
        "Hauts-de-France": {"lat": 49.9656, "lon": 2.7699, "pop": 5963000},
        "Nouvelle-Aquitaine": {"lat": 45.7087, "lon": 0.6262, "pop": 5999000},
        "Occitanie": {"lat": 43.8927, "lon": 3.2828, "pop": 5925000},
        "Grand Est": {"lat": 48.6998, "lon": 6.1878, "pop": 5556000},
        "Provence-Alpes-Côte d'Azur": {"lat": 43.9352, "lon": 6.0679, "pop": 5055000},
        "Pays de la Loire": {"lat": 47.7633, "lon": -0.3296, "pop": 3807000},
        "Bretagne": {"lat": 48.2020, "lon": -2.9326, "pop": 3341000},
        "Normandie": {"lat": 49.1829, "lon": -0.3707, "pop": 3303000},
        "Bourgogne-Franche-Comté": {"lat": 47.2805, "lon": 4.9994, "pop": 2783000},
        "Centre-Val de Loire": {"lat": 47.7516, "lon": 1.6751, "pop": 2573000},
        "Corse": {"lat": 42.0396, "lon": 9.0129, "pop": 340000},
    }

    def __init__(self):
        super().__init__()
        self.client = httpx.AsyncClient(timeout=60.0, follow_redirects=True)

    async def fetch(self) -> List[Dict[str, Any]]:
        """Fetch wastewater data from data.gouv.fr."""
        self.logger.info("Fetching from France data.gouv.fr")

        try:
            # Try to fetch the CSV data
            response = await self.client.get(self.DATA_URL)
            response.raise_for_status()

            # Parse CSV
            content = response.text
            reader = csv.DictReader(io.StringIO(content), delimiter=";")
            records = list(reader)

            self.logger.info(f"Received {len(records)} records from data.gouv.fr")
            return records

        except httpx.HTTPError as e:
            self.logger.error(
                f"Failed to fetch data.gouv.fr data: {e}. "
                "Returning empty data - NOT using synthetic fallback."
            )
            # Return empty data instead of silently using synthetic data
            return []

    def _generate_synthetic_data(self) -> List[Dict[str, Any]]:
        """Generate synthetic data when real source unavailable."""
        import random
        from datetime import timedelta

        records = []
        today = datetime.now()

        for region in self.FR_REGIONS:
            for days_ago in range(30):
                date = today - timedelta(days=days_ago)
                records.append({
                    "region": region,
                    "date": date.strftime("%Y-%m-%d"),
                    "viral_load": random.uniform(1e6, 1e9),
                    "trend": random.uniform(-20, 20),
                })

        return records

    def normalize(
        self,
        raw_data: List[Dict[str, Any]]
    ) -> tuple[List[LocationData], List[SurveillanceEvent]]:
        """Normalize France data to standard schema."""
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
        """Extract location from France record."""
        region = record.get("region") or record.get("nom_region")
        if not region:
            return None

        # Find matching region
        matched_region = None
        for r in self.FR_REGIONS:
            if r.lower() == region.lower() or region.lower() in r.lower():
                matched_region = r
                break

        if not matched_region:
            return None

        region_info = self.FR_REGIONS[matched_region]
        latitude = region_info["lat"]
        longitude = region_info["lon"]
        population = region_info["pop"]

        # Generate H3 index
        try:
            h3_index = h3.latlng_to_cell(latitude, longitude, 5)
        except Exception:
            h3_index = None

        clean_name = matched_region.lower().replace(' ', '_').replace('-', '_').replace("'", '')[:25]
        location_id = f"loc_fr_{clean_name}"

        return LocationData(
            location_id=location_id,
            name=matched_region,
            admin1=matched_region,
            country="France",
            iso_code="FR",
            granularity=GranularityTier.TIER_2,
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
        """Extract surveillance event from France record."""
        date_str = record.get("date") or record.get("semaine")
        if not date_str:
            return None

        try:
            timestamp = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            try:
                timestamp = datetime.strptime(date_str, "%d/%m/%Y")
            except ValueError:
                return None

        # Get metrics
        raw_load = None
        normalized_score = None
        velocity = None

        load_str = record.get("viral_load") or record.get("concentration")
        if load_str:
            try:
                raw_load = float(str(load_str).replace(",", "."))
                normalized_score = min(1.0, raw_load / 1e9)
            except ValueError:
                pass

        trend_str = record.get("trend") or record.get("evolution")
        if trend_str:
            try:
                velocity = float(str(trend_str).replace(",", ".")) / 100
            except ValueError:
                pass

        return SurveillanceEvent(
            event_id=self.generate_event_id(location_id, timestamp, self.source_id),
            location_id=location_id,
            timestamp=timestamp,
            data_source=self.source_id,
            signal_type=self.signal_type,
            raw_load=raw_load,
            normalized_score=normalized_score,
            velocity=velocity,
            quality_score=0.80,
            raw_data=record,
        )

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
