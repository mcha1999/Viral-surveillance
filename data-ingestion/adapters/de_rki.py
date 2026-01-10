"""
Germany RKI (Robert Koch Institute) Wastewater Adapter

Data source: https://github.com/robert-koch-institut/
Coverage: German states (Bundesländer)
Frequency: Updated weekly
Granularity: Tier 2 (State level)
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


class DERKIAdapter(BaseAdapter):
    """
    Adapter for German RKI wastewater surveillance data.

    Fetches from RKI's GitHub data repository.
    """

    source_id = "RKI"
    source_name = "Robert Koch Institute"
    signal_type = SignalType.WASTEWATER

    # RKI GitHub raw data URL
    DATA_URL = "https://raw.githubusercontent.com/robert-koch-institut/Abwassersurveillance_AMELAG/main/Abwassersurveillance_AMELAG.csv"

    # German states (Bundesländer) with coordinates
    DE_STATES = {
        "Baden-Württemberg": {"lat": 48.6616, "lon": 9.3501, "pop": 11100000},
        "Bayern": {"lat": 48.7904, "lon": 11.4979, "pop": 13125000},
        "Berlin": {"lat": 52.5200, "lon": 13.4050, "pop": 3645000},
        "Brandenburg": {"lat": 52.4125, "lon": 12.5316, "pop": 2522000},
        "Bremen": {"lat": 53.0793, "lon": 8.8017, "pop": 681000},
        "Hamburg": {"lat": 53.5511, "lon": 9.9937, "pop": 1853000},
        "Hessen": {"lat": 50.6521, "lon": 9.1624, "pop": 6288000},
        "Mecklenburg-Vorpommern": {"lat": 53.6127, "lon": 12.4296, "pop": 1611000},
        "Niedersachsen": {"lat": 52.6367, "lon": 9.8451, "pop": 8003000},
        "Nordrhein-Westfalen": {"lat": 51.4332, "lon": 7.6616, "pop": 17926000},
        "Rheinland-Pfalz": {"lat": 49.9129, "lon": 7.4500, "pop": 4094000},
        "Saarland": {"lat": 49.3964, "lon": 7.0230, "pop": 984000},
        "Sachsen": {"lat": 51.1045, "lon": 13.2017, "pop": 4057000},
        "Sachsen-Anhalt": {"lat": 51.9503, "lon": 11.6923, "pop": 2181000},
        "Schleswig-Holstein": {"lat": 54.2194, "lon": 9.6961, "pop": 2904000},
        "Thüringen": {"lat": 50.8610, "lon": 11.0519, "pop": 2120000},
    }

    def __init__(self):
        super().__init__()
        self.client = httpx.AsyncClient(timeout=60.0)

    async def fetch(self) -> List[Dict[str, Any]]:
        """Fetch wastewater data from RKI GitHub."""
        self.logger.info("Fetching from RKI")

        try:
            response = await self.client.get(self.DATA_URL)
            response.raise_for_status()

            # Parse CSV
            content = response.text
            reader = csv.DictReader(io.StringIO(content))
            records = list(reader)

            self.logger.info(f"Received {len(records)} records from RKI")
            return records

        except httpx.HTTPError as e:
            self.logger.error(f"Failed to fetch RKI data: {e}")
            return []

    def normalize(
        self,
        raw_data: List[Dict[str, Any]]
    ) -> tuple[List[LocationData], List[SurveillanceEvent]]:
        """Normalize RKI data to standard schema."""
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
        """Extract location from RKI record."""
        # RKI provides state-level data
        state = record.get("bundesland", "")

        if not state or state not in self.DE_STATES:
            # Try to find partial match
            for s in self.DE_STATES:
                if s.lower() in state.lower() or state.lower() in s.lower():
                    state = s
                    break
            else:
                return None

        state_info = self.DE_STATES[state]
        latitude = state_info["lat"]
        longitude = state_info["lon"]
        population = state_info["pop"]

        # Generate H3 index
        try:
            h3_index = h3.geo_to_h3(latitude, longitude, 5)
        except Exception:
            h3_index = None

        location_id = f"loc_de_{state.lower().replace('-', '_').replace(' ', '_')}"

        return LocationData(
            location_id=location_id,
            name=state,
            admin1=state,
            country="Germany",
            iso_code="DE",
            granularity=GranularityTier.TIER_2,  # State level
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
        """Extract surveillance event from RKI record."""
        date_str = record.get("datum") or record.get("date")
        if not date_str:
            return None

        try:
            timestamp = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            return None

        # Get viral load metrics
        raw_load = None
        normalized_score = None
        velocity = None

        # Viral load (gene copies per liter)
        load_str = record.get("viruslast") or record.get("viral_load")
        if load_str:
            try:
                raw_load = float(load_str)
                # Normalize (assuming max of 1e9)
                normalized_score = min(1.0, raw_load / 1e9)
            except ValueError:
                pass

        # Trend/change
        trend_str = record.get("trend") or record.get("change_percent")
        if trend_str:
            try:
                velocity = float(trend_str) / 100
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
            quality_score=0.85,
            raw_data=record,
        )

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
