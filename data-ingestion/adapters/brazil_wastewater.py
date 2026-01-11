"""
Brazil Wastewater Surveillance Adapter

Data source: Fiocruz (Oswaldo Cruz Foundation) and IBGE
Coverage: Brazilian states and major cities
Frequency: Weekly updates

Fiocruz maintains COVID-19 surveillance data including wastewater monitoring
through the InfoGripe and related surveillance systems.
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
import json

import httpx
import h3

from .base import (
    BaseAdapter,
    LocationData,
    SurveillanceEvent,
    SignalType,
    GranularityTier,
)


class BrazilFiocruzAdapter(BaseAdapter):
    """
    Adapter for Brazil Fiocruz wastewater and epidemiological surveillance data.

    Data source: https://infogripe.fiocruz.br/ and Brasil.IO
    Coverage: Brazilian states (26 states + Federal District)
    Frequency: Weekly updates
    """

    source_id = "BR_FIOCRUZ"
    source_name = "Fiocruz - Oswaldo Cruz Foundation"
    signal_type = SignalType.WASTEWATER

    # Fiocruz InfoGripe API
    INFOGRIPE_URL = "https://info.gripe.fiocruz.br/api/dados"

    # Brasil.IO COVID data API (community maintained)
    BRASIL_IO_URL = "https://api.brasil.io/v1/dataset/covid19/caso_full/data"

    # Brazilian states with coordinates and populations
    BR_STATES = {
        "AC": {"name": "Acre", "lat": -9.0238, "lon": -70.8120, "pop": 900000},
        "AL": {"name": "Alagoas", "lat": -9.5713, "lon": -36.7820, "pop": 3400000},
        "AP": {"name": "Amapá", "lat": 1.4102, "lon": -51.7700, "pop": 870000},
        "AM": {"name": "Amazonas", "lat": -3.4168, "lon": -65.8561, "pop": 4200000},
        "BA": {"name": "Bahia", "lat": -12.5797, "lon": -41.7007, "pop": 14900000},
        "CE": {"name": "Ceará", "lat": -5.4984, "lon": -39.3206, "pop": 9200000},
        "DF": {"name": "Distrito Federal", "lat": -15.7801, "lon": -47.9292, "pop": 3100000},
        "ES": {"name": "Espírito Santo", "lat": -19.1834, "lon": -40.3089, "pop": 4100000},
        "GO": {"name": "Goiás", "lat": -15.8270, "lon": -49.8362, "pop": 7100000},
        "MA": {"name": "Maranhão", "lat": -5.4200, "lon": -45.4431, "pop": 7100000},
        "MT": {"name": "Mato Grosso", "lat": -12.6819, "lon": -56.9211, "pop": 3500000},
        "MS": {"name": "Mato Grosso do Sul", "lat": -20.7722, "lon": -54.7852, "pop": 2800000},
        "MG": {"name": "Minas Gerais", "lat": -18.5122, "lon": -44.5550, "pop": 21300000},
        "PA": {"name": "Pará", "lat": -3.4168, "lon": -52.2166, "pop": 8700000},
        "PB": {"name": "Paraíba", "lat": -7.2399, "lon": -36.7819, "pop": 4100000},
        "PR": {"name": "Paraná", "lat": -24.8941, "lon": -51.5545, "pop": 11500000},
        "PE": {"name": "Pernambuco", "lat": -8.3187, "lon": -37.8612, "pop": 9600000},
        "PI": {"name": "Piauí", "lat": -7.7183, "lon": -42.7289, "pop": 3300000},
        "RJ": {"name": "Rio de Janeiro", "lat": -22.2533, "lon": -42.8797, "pop": 17400000},
        "RN": {"name": "Rio Grande do Norte", "lat": -5.4026, "lon": -36.9541, "pop": 3500000},
        "RS": {"name": "Rio Grande do Sul", "lat": -30.0346, "lon": -51.2177, "pop": 11400000},
        "RO": {"name": "Rondônia", "lat": -11.5057, "lon": -63.5806, "pop": 1800000},
        "RR": {"name": "Roraima", "lat": 1.9892, "lon": -61.3269, "pop": 630000},
        "SC": {"name": "Santa Catarina", "lat": -27.2423, "lon": -50.2189, "pop": 7200000},
        "SP": {"name": "São Paulo", "lat": -23.5505, "lon": -46.6333, "pop": 46300000},
        "SE": {"name": "Sergipe", "lat": -10.5741, "lon": -37.3857, "pop": 2300000},
        "TO": {"name": "Tocantins", "lat": -10.1753, "lon": -48.2982, "pop": 1600000},
    }

    def __init__(self):
        super().__init__()
        self.client = httpx.AsyncClient(timeout=60.0, follow_redirects=True)
        self.brasil_io_token = os.getenv("BRASIL_IO_TOKEN")

    async def fetch(self) -> List[Dict[str, Any]]:
        """Fetch wastewater/epidemiological data from Brazilian sources."""
        self.logger.info("Fetching from Brazil Fiocruz")

        all_records = []

        # Try Fiocruz InfoGripe API first
        try:
            records = await self._fetch_infogripe()
            if records:
                all_records.extend(records)
        except Exception as e:
            self.logger.warning(f"InfoGripe fetch failed: {e}")

        # Try Brasil.IO as backup
        if not all_records:
            try:
                records = await self._fetch_brasil_io()
                if records:
                    all_records.extend(records)
            except Exception as e:
                self.logger.warning(f"Brasil.IO fetch failed: {e}")

        if not all_records:
            self.logger.error(
                "Failed to fetch Brazil data from any source. "
                "Returning empty data - NOT using synthetic fallback."
            )
            return []

        self.logger.info(f"Total Brazil records: {len(all_records)}")
        return all_records

    async def _fetch_infogripe(self) -> List[Dict[str, Any]]:
        """Fetch from Fiocruz InfoGripe API."""
        records = []

        try:
            # InfoGripe provides SARI (Severe Acute Respiratory Infection) data
            params = {
                "ano": datetime.now().year,
                "tipo": "estadual",
                "territorios": "1",  # All states
            }

            response = await self.client.get(self.INFOGRIPE_URL, params=params)

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    for item in data:
                        item["_source"] = "infogripe"
                    records = data
                    self.logger.info(f"InfoGripe: fetched {len(records)} records")

        except httpx.HTTPError as e:
            self.logger.warning(f"InfoGripe API error: {e}")

        return records

    async def _fetch_brasil_io(self) -> List[Dict[str, Any]]:
        """Fetch from Brasil.IO COVID dataset."""
        records = []

        headers = {}
        if self.brasil_io_token:
            headers["Authorization"] = f"Token {self.brasil_io_token}"

        try:
            # Get state-level data
            params = {
                "place_type": "state",
                "is_last": "True",
            }

            response = await self.client.get(
                self.BRASIL_IO_URL,
                params=params,
                headers=headers
            )

            if response.status_code == 200:
                data = response.json()
                if "results" in data:
                    for item in data["results"]:
                        item["_source"] = "brasil_io"
                    records = data["results"]
                    self.logger.info(f"Brasil.IO: fetched {len(records)} records")

        except httpx.HTTPError as e:
            self.logger.warning(f"Brasil.IO API error: {e}")

        return records

    def normalize(
        self,
        raw_data: List[Dict[str, Any]]
    ) -> Tuple[List[LocationData], List[SurveillanceEvent]]:
        """Normalize Brazil data to standard schema."""
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
        """Extract location from Brazil record."""
        # Get state code
        state_code = (
            record.get("state") or
            record.get("uf") or
            record.get("sigla_uf")
        )

        if not state_code or state_code not in self.BR_STATES:
            return None

        state_info = self.BR_STATES[state_code]

        try:
            h3_index = h3.latlng_to_cell(state_info["lat"], state_info["lon"], 5)
        except Exception:
            h3_index = None

        location_id = f"loc_br_{state_code.lower()}"

        return LocationData(
            location_id=location_id,
            name=state_info["name"],
            admin1=state_info["name"],
            country="Brazil",
            iso_code="BR",
            granularity=GranularityTier.TIER_2,  # State level
            latitude=state_info["lat"],
            longitude=state_info["lon"],
            catchment_population=state_info["pop"],
            h3_index=h3_index,
        )

    def _extract_event(
        self,
        record: Dict[str, Any],
        location_id: str
    ) -> Optional[SurveillanceEvent]:
        """Extract surveillance event from Brazil record."""
        source = record.get("_source", "unknown")

        # Get date based on source
        if source == "infogripe":
            date_str = record.get("data") or record.get("semana_epidemiologica")
        else:  # brasil_io
            date_str = record.get("date") or record.get("last_available_date")

        if not date_str:
            return None

        try:
            if isinstance(date_str, int):
                # Epidemiological week format
                year = datetime.now().year
                timestamp = datetime.strptime(f"{year}-W{date_str:02d}-1", "%Y-W%W-%w")
            else:
                timestamp = datetime.strptime(date_str[:10], "%Y-%m-%d")
        except ValueError:
            return None

        # Get metrics based on source
        normalized_score = None

        if source == "infogripe":
            # SARI (Severe Acute Respiratory Infection) data
            sari_count = record.get("casos") or record.get("srag")
            if sari_count is not None:
                try:
                    # Normalize SARI counts (typical weekly max ~5000/state)
                    normalized_score = min(1.0, float(sari_count) / 5000.0)
                except (ValueError, TypeError):
                    pass
        else:  # brasil_io
            # Case data
            new_cases = record.get("new_confirmed") or record.get("confirmed")
            if new_cases is not None:
                try:
                    # Normalize daily cases (typical max ~10000/state)
                    normalized_score = min(1.0, float(new_cases) / 10000.0)
                except (ValueError, TypeError):
                    pass

        return SurveillanceEvent(
            event_id=self.generate_event_id(location_id, timestamp, self.source_id),
            location_id=location_id,
            timestamp=timestamp,
            data_source=self.source_id,
            signal_type=self.signal_type,
            normalized_score=normalized_score,
            quality_score=0.80,
            raw_data=record,
        )

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# Convenience function for testing
async def test_brazil_adapter():
    """Test the Brazil Fiocruz adapter."""
    print("\nTesting Brazil Fiocruz Adapter")
    print("=" * 50)

    try:
        adapter = BrazilFiocruzAdapter()
        raw_data = await adapter.fetch()
        print(f"Raw records fetched: {len(raw_data)}")

        if raw_data:
            locations, events = adapter.normalize(raw_data)
            print(f"Locations normalized: {len(locations)}")
            print(f"Events normalized: {len(events)}")

            if locations:
                print("\nSample locations:")
                for loc in locations[:5]:
                    print(f"  - {loc.name} ({loc.location_id})")

        await adapter.close()

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_brazil_adapter())
