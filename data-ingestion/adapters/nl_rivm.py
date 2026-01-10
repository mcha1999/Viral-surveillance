"""
Netherlands RIVM Wastewater Adapter

Data source: https://data.rivm.nl/covid-19/
Coverage: Netherlands wastewater treatment plants
Frequency: Updated weekly
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


class NLRIVMAdapter(BaseAdapter):
    """
    Adapter for Netherlands RIVM wastewater surveillance data.

    Fetches CSV data from RIVM open data portal.
    """

    source_id = "RIVM"
    source_name = "Netherlands RIVM"
    signal_type = SignalType.WASTEWATER

    # Data URL - COVID-19 sewage surveillance
    DATA_URL = "https://data.rivm.nl/covid-19/COVID-19_rioolwaterdata.csv"

    # Netherlands provinces with coordinates
    NL_PROVINCES = {
        "Groningen": {"lat": 53.2194, "lon": 6.5665},
        "Friesland": {"lat": 53.1642, "lon": 5.7819},
        "Drenthe": {"lat": 52.9476, "lon": 6.6231},
        "Overijssel": {"lat": 52.4388, "lon": 6.5016},
        "Flevoland": {"lat": 52.5279, "lon": 5.5953},
        "Gelderland": {"lat": 52.0452, "lon": 5.8718},
        "Utrecht": {"lat": 52.0907, "lon": 5.1214},
        "Noord-Holland": {"lat": 52.5206, "lon": 4.7885},
        "Zuid-Holland": {"lat": 51.9851, "lon": 4.4919},
        "Zeeland": {"lat": 51.4940, "lon": 3.8497},
        "Noord-Brabant": {"lat": 51.4827, "lon": 5.2324},
        "Limburg": {"lat": 51.4427, "lon": 6.0608},
    }

    def __init__(self):
        super().__init__()
        self.client = httpx.AsyncClient(timeout=60.0)

    async def fetch(self) -> List[Dict[str, Any]]:
        """Fetch wastewater data from RIVM."""
        self.logger.info("Fetching from RIVM")

        try:
            response = await self.client.get(self.DATA_URL)
            response.raise_for_status()

            # Parse CSV
            content = response.text
            reader = csv.DictReader(io.StringIO(content), delimiter=";")
            records = list(reader)

            self.logger.info(f"Received {len(records)} records from RIVM")
            return records

        except httpx.HTTPError as e:
            self.logger.error(f"Failed to fetch RIVM data: {e}")
            return []

    def normalize(
        self,
        raw_data: List[Dict[str, Any]]
    ) -> tuple[List[LocationData], List[SurveillanceEvent]]:
        """Normalize RIVM data to standard schema."""
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
        """Extract location from RIVM record."""
        # RIVM data includes RWZI (treatment plant) info
        rwzi_name = record.get("RWZI_AWZI_name", "")
        region = record.get("Security_region_name", "")

        if not rwzi_name:
            return None

        # Try to get province from region or use default
        province = None
        for prov in self.NL_PROVINCES:
            if prov.lower() in region.lower():
                province = prov
                break

        # Get coordinates - prefer specific if available
        lat = record.get("RWZI_AWZI_lat")
        lon = record.get("RWZI_AWZI_lon")

        if lat and lon:
            try:
                latitude = float(lat.replace(",", "."))
                longitude = float(lon.replace(",", "."))
            except (ValueError, AttributeError):
                # Use province center as fallback
                coords = self.NL_PROVINCES.get(province, {"lat": 52.1326, "lon": 5.2913})
                latitude = coords["lat"]
                longitude = coords["lon"]
        else:
            coords = self.NL_PROVINCES.get(province, {"lat": 52.1326, "lon": 5.2913})
            latitude = coords["lat"]
            longitude = coords["lon"]

        # Generate H3 index
        try:
            h3_index = h3.geo_to_h3(latitude, longitude, 7)
        except Exception:
            h3_index = None

        # Get population served
        population = None
        pop_str = record.get("RWZI_AWZI_population_equivalents")
        if pop_str:
            try:
                population = int(float(pop_str.replace(",", ".")))
            except (ValueError, AttributeError):
                pass

        location_id = self._generate_location_id(rwzi_name)

        return LocationData(
            location_id=location_id,
            name=rwzi_name,
            admin1=province or region,
            country="Netherlands",
            iso_code="NL",
            granularity=GranularityTier.TIER_1,  # Site-level
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
        """Extract surveillance event from RIVM record."""
        # Date field
        date_str = record.get("Date_measurement")
        if not date_str:
            return None

        try:
            timestamp = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            try:
                timestamp = datetime.strptime(date_str, "%d-%m-%Y")
            except ValueError:
                return None

        # Get viral load
        raw_load = None
        normalized_score = None

        # RNA flow per 100k inhabitants
        rna_flow = record.get("RNA_flow_per_100000")
        if rna_flow:
            try:
                raw_load = float(rna_flow.replace(",", "."))
                # Normalize (assuming max of 1e15 copies)
                normalized_score = min(1.0, raw_load / 1e15)
            except (ValueError, AttributeError):
                pass

        return SurveillanceEvent(
            event_id=self.generate_event_id(location_id, timestamp, self.source_id),
            location_id=location_id,
            timestamp=timestamp,
            data_source=self.source_id,
            signal_type=self.signal_type,
            raw_load=raw_load,
            normalized_score=normalized_score,
            quality_score=0.90,
            raw_data=record,
        )

    def _generate_location_id(self, name: str) -> str:
        """Generate consistent location ID."""
        import hashlib
        hash_part = hashlib.md5(name.encode()).hexdigest()[:8]
        return f"loc_nl_rwzi_{hash_part}"

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
