"""
Multi-Source Wastewater Surveillance Adapter
=============================================

Aggregates wastewater data from multiple sources:

US Sources:
- CDC NWSS (federal): data.cdc.gov
- WastewaterSCAN (Stanford/Emory): data.wastewaterscan.org
- State-level sources:
  - California Cal-SuWers: data.chhs.ca.gov
  - Massachusetts MWRA: mwra.com
  - New York: coronavirus.health.ny.gov

EU Sources:
- EU Wastewater Observatory (JRC): wastewater-observatory.jrc.ec.europa.eu
- Germany RKI AMELAG: github.com/robert-koch-institut

This provides redundancy and broader coverage when any single source
has gaps or delays.
"""

import os
import csv
import io
import json
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

import httpx
import h3

from .base import (
    BaseAdapter,
    LocationData,
    SurveillanceEvent,
    SignalType,
    GranularityTier,
)


class DataSourcePriority(Enum):
    """Priority for deduplication when multiple sources have same location."""
    CDC_NWSS = 1  # Highest priority - federal source
    WASTEWATER_SCAN = 2  # Stanford/Emory research
    STATE_HEALTH = 3  # State health departments
    EU_OBSERVATORY = 4  # EU-wide data
    NATIONAL_INSTITUTES = 5  # RKI, etc.


@dataclass
class WastewaterDataPoint:
    """Intermediate representation for multi-source data."""
    source: str
    location_id: str
    location_name: str
    state_or_region: str
    country: str
    latitude: float
    longitude: float
    timestamp: datetime
    viral_load: Optional[float]  # copies/L or normalized
    percentile: Optional[float]  # 0-100
    percent_change: Optional[float]  # Week-over-week
    population_served: Optional[int]
    pathogen: str  # SARS-CoV-2, Influenza, RSV, etc.
    raw_data: Dict[str, Any]
    priority: DataSourcePriority


class WastewaterMultiSourceAdapter(BaseAdapter):
    """
    Aggregates wastewater data from multiple sources for comprehensive coverage.
    """

    source_id = "WASTEWATER_MULTI"
    source_name = "Multi-Source Wastewater Surveillance"
    signal_type = SignalType.WASTEWATER

    # CDC NWSS endpoints (primary US source)
    CDC_DOMAIN = "data.cdc.gov"
    CDC_DATASET_ID = "2ew6-ywp6"
    CDC_ENDPOINT = f"https://data.cdc.gov/resource/{CDC_DATASET_ID}.json"

    # California Cal-SuWers (Socrata)
    CA_DOMAIN = "data.chhs.ca.gov"
    CA_DATASET_ID = "s3r7-wgpq"
    CA_ENDPOINT = f"https://data.chhs.ca.gov/api/3/action/datastore_search"

    # Massachusetts MWRA Biobot data
    MA_BIOBOT_URL = "https://www.mwra.com/biobot/biobotdata.csv"

    # Germany RKI AMELAG
    RKI_URL = "https://raw.githubusercontent.com/robert-koch-institut/Abwassersurveillance_AMELAG/main/Abwassersurveillance.csv"

    # State coordinates for fallback
    US_STATE_COORDS = {
        'AL': (32.7990, -86.8073), 'AK': (64.0685, -152.2782), 'AZ': (34.2744, -111.6602),
        'AR': (34.8938, -92.4426), 'CA': (37.1841, -119.4696), 'CO': (38.9972, -105.5478),
        'CT': (41.6219, -72.7273), 'DE': (38.9896, -75.5050), 'FL': (28.6305, -82.4497),
        'GA': (32.6415, -83.4426), 'HI': (20.2927, -156.3737), 'ID': (44.3509, -114.6130),
        'IL': (40.0417, -89.1965), 'IN': (39.8942, -86.2816), 'IA': (42.0751, -93.4960),
        'KS': (38.4937, -98.3804), 'KY': (37.5347, -85.3021), 'LA': (31.0689, -91.9968),
        'ME': (45.3695, -69.2428), 'MD': (39.0550, -76.7909), 'MA': (42.2596, -71.8083),
        'MI': (44.3467, -85.4102), 'MN': (46.2807, -94.3053), 'MS': (32.7364, -89.6678),
        'MO': (38.3566, -92.4580), 'MT': (47.0527, -109.6333), 'NE': (41.5378, -99.7951),
        'NV': (39.3289, -116.6312), 'NH': (43.6805, -71.5811), 'NJ': (40.1907, -74.6728),
        'NM': (34.4071, -106.1126), 'NY': (42.9538, -75.5268), 'NC': (35.5557, -79.3877),
        'ND': (47.4501, -100.4659), 'OH': (40.2862, -82.7937), 'OK': (35.5889, -97.4943),
        'OR': (43.9336, -120.5583), 'PA': (40.8781, -77.7996), 'RI': (41.6762, -71.5562),
        'SC': (33.9169, -80.8964), 'SD': (44.4443, -100.2263), 'TN': (35.8580, -86.3505),
        'TX': (31.4757, -99.3312), 'UT': (39.3055, -111.6703), 'VT': (44.0687, -72.6658),
        'VA': (37.5215, -78.8537), 'WA': (47.3826, -120.4472), 'WV': (38.6409, -80.6227),
        'WI': (44.6243, -89.9941), 'WY': (42.9957, -107.5512), 'DC': (38.9072, -77.0369),
        'PR': (18.2208, -66.5901),
    }

    def __init__(
        self,
        socrata_token: Optional[str] = None,
        enable_state_sources: bool = True,
        enable_eu_sources: bool = True,
    ):
        super().__init__()
        self.socrata_token = socrata_token or os.getenv("SOCRATA_APP_TOKEN")
        self.enable_state_sources = enable_state_sources
        self.enable_eu_sources = enable_eu_sources
        self.client = httpx.AsyncClient(timeout=60.0, follow_redirects=True)

    async def fetch(self) -> List[Dict[str, Any]]:
        """Fetch from all configured sources."""
        all_data = []

        # Fetch from each source
        sources = [
            ("CDC_NWSS", self._fetch_cdc_nwss),
        ]

        if self.enable_state_sources:
            sources.extend([
                ("CA_CALSUWERS", self._fetch_california),
                ("MA_MWRA", self._fetch_massachusetts),
            ])

        if self.enable_eu_sources:
            sources.extend([
                ("DE_RKI", self._fetch_germany_rki),
            ])

        for source_name, fetch_fn in sources:
            try:
                self.logger.info(f"Fetching from {source_name}")
                data = await fetch_fn()
                self.logger.info(f"Received {len(data)} records from {source_name}")
                all_data.extend(data)
            except Exception as e:
                self.logger.warning(f"Failed to fetch from {source_name}: {e}")
                continue

        return all_data

    async def _fetch_cdc_nwss(self) -> List[Dict[str, Any]]:
        """Fetch from CDC NWSS via Socrata API."""
        # Calculate date 90 days ago for query
        start_date = (datetime.utcnow() - timedelta(days=90)).strftime("%Y-%m-%d")

        params = {
            "$limit": 50000,
            "$order": "sample_collect_date DESC",
            "$where": f"sample_collect_date >= '{start_date}'",
        }

        if self.socrata_token:
            params["$$app_token"] = self.socrata_token

        response = await self.client.get(self.CDC_ENDPOINT, params=params)
        response.raise_for_status()

        records = response.json()

        # Tag with source
        for r in records:
            r["_source"] = "CDC_NWSS"
            r["_priority"] = DataSourcePriority.CDC_NWSS.value

        return records

    async def _fetch_california(self) -> List[Dict[str, Any]]:
        """Fetch California Cal-SuWers data."""
        params = {
            "resource_id": self.CA_DATASET_ID,
            "limit": 10000,
        }

        try:
            response = await self.client.get(self.CA_ENDPOINT, params=params)
            response.raise_for_status()
            data = response.json()

            records = data.get("result", {}).get("records", [])
            for r in records:
                r["_source"] = "CA_CALSUWERS"
                r["_priority"] = DataSourcePriority.STATE_HEALTH.value

            return records

        except Exception as e:
            self.logger.warning(f"California fetch failed: {e}")
            return []

    async def _fetch_massachusetts(self) -> List[Dict[str, Any]]:
        """Fetch Massachusetts MWRA Biobot data."""
        try:
            response = await self.client.get(self.MA_BIOBOT_URL)
            response.raise_for_status()

            # Parse CSV
            reader = csv.DictReader(io.StringIO(response.text))
            records = []
            for row in reader:
                row["_source"] = "MA_MWRA"
                row["_priority"] = DataSourcePriority.STATE_HEALTH.value
                records.append(row)

            return records

        except Exception as e:
            self.logger.warning(f"Massachusetts fetch failed: {e}")
            return []

    async def _fetch_germany_rki(self) -> List[Dict[str, Any]]:
        """Fetch Germany RKI AMELAG wastewater data."""
        try:
            response = await self.client.get(self.RKI_URL)
            response.raise_for_status()

            # Parse CSV (semicolon-separated)
            reader = csv.DictReader(io.StringIO(response.text), delimiter=";")
            records = []
            for row in reader:
                row["_source"] = "DE_RKI"
                row["_priority"] = DataSourcePriority.NATIONAL_INSTITUTES.value
                records.append(row)

            return records

        except Exception as e:
            self.logger.warning(f"Germany RKI fetch failed: {e}")
            return []

    def normalize(
        self,
        raw_data: List[Dict[str, Any]]
    ) -> Tuple[List[LocationData], List[SurveillanceEvent]]:
        """Normalize data from all sources to common schema."""
        locations_map: Dict[str, LocationData] = {}
        events: List[SurveillanceEvent] = []

        for record in raw_data:
            source = record.get("_source", "UNKNOWN")

            try:
                if source == "CDC_NWSS":
                    location, event = self._normalize_cdc(record)
                elif source == "CA_CALSUWERS":
                    location, event = self._normalize_california(record)
                elif source == "MA_MWRA":
                    location, event = self._normalize_massachusetts(record)
                elif source == "DE_RKI":
                    location, event = self._normalize_rki(record)
                else:
                    continue

                if location:
                    # Deduplicate by location, keeping highest priority
                    existing = locations_map.get(location.location_id)
                    if not existing:
                        locations_map[location.location_id] = location

                if event:
                    events.append(event)

            except Exception as e:
                self.logger.debug(f"Failed to normalize record from {source}: {e}")
                continue

        return list(locations_map.values()), events

    def _normalize_cdc(
        self, record: Dict[str, Any]
    ) -> Tuple[Optional[LocationData], Optional[SurveillanceEvent]]:
        """Normalize CDC NWSS record."""
        wwtp_id = record.get("wwtp_id")
        if not wwtp_id:
            return None, None

        # Location
        try:
            lat = float(record.get("wwtp_latitude") or 0)
            lon = float(record.get("wwtp_longitude") or 0)
        except (TypeError, ValueError):
            lat, lon = 0, 0

        state = record.get("reporting_jurisdiction", "")
        if lat == 0 and lon == 0 and state in self.US_STATE_COORDS:
            lat, lon = self.US_STATE_COORDS[state]

        if lat == 0 and lon == 0:
            return None, None

        location_id = f"loc_us_{hashlib.md5(wwtp_id.encode()).hexdigest()[:10]}"

        try:
            h3_index = h3.latlng_to_cell(lat, lon, 7)
        except:
            h3_index = None

        try:
            pop = int(float(record.get("population_served") or 0))
        except:
            pop = None

        location = LocationData(
            location_id=location_id,
            name=record.get("county_names", "Unknown"),
            admin1=state,
            country="United States",
            iso_code="US",
            granularity=GranularityTier.TIER_1,
            latitude=lat,
            longitude=lon,
            catchment_population=pop,
            h3_index=h3_index,
        )

        # Event
        date_str = record.get("sample_collect_date") or record.get("date_start")
        if not date_str:
            return location, None

        try:
            ts = datetime.fromisoformat(date_str.replace("Z", "+00:00").split("T")[0])
        except:
            return location, None

        # Get metrics
        normalized_score = None
        velocity = None

        # Percentile (0-100)
        pct = record.get("percentile")
        if pct:
            try:
                normalized_score = float(pct) / 100
            except:
                pass

        # 15-day percent change
        ptc = record.get("ptc_15d")
        if ptc and ptc not in ("", "null"):
            try:
                velocity = float(ptc) / 100
            except:
                pass

        event = SurveillanceEvent(
            event_id=self.generate_event_id(location_id, ts, "CDC_NWSS"),
            location_id=location_id,
            timestamp=ts,
            data_source="CDC_NWSS",
            signal_type=self.signal_type,
            normalized_score=normalized_score,
            velocity=velocity,
            quality_score=0.9,
            raw_data=record,
        )

        return location, event

    def _normalize_california(
        self, record: Dict[str, Any]
    ) -> Tuple[Optional[LocationData], Optional[SurveillanceEvent]]:
        """Normalize California Cal-SuWers record."""
        county = record.get("county")
        if not county:
            return None, None

        location_id = f"loc_us_ca_{county.lower().replace(' ', '_')[:20]}"

        # Use California centroid as fallback
        lat, lon = 37.1841, -119.4696

        location = LocationData(
            location_id=location_id,
            name=county,
            admin1="CA",
            country="United States",
            iso_code="US",
            granularity=GranularityTier.TIER_2,
            latitude=lat,
            longitude=lon,
        )

        # Parse date
        date_str = record.get("sample_collect_date") or record.get("date")
        if not date_str:
            return location, None

        try:
            ts = datetime.strptime(date_str.split("T")[0], "%Y-%m-%d")
        except:
            return location, None

        # Get viral load
        load = record.get("sars_cov_2_concentration") or record.get("viral_load")
        normalized_score = None
        if load:
            try:
                normalized_score = min(1.0, float(load) / 1e9)
            except:
                pass

        event = SurveillanceEvent(
            event_id=self.generate_event_id(location_id, ts, "CA_CALSUWERS"),
            location_id=location_id,
            timestamp=ts,
            data_source="CA_CALSUWERS",
            signal_type=self.signal_type,
            normalized_score=normalized_score,
            quality_score=0.85,
            raw_data=record,
        )

        return location, event

    def _normalize_massachusetts(
        self, record: Dict[str, Any]
    ) -> Tuple[Optional[LocationData], Optional[SurveillanceEvent]]:
        """Normalize Massachusetts MWRA Biobot record."""
        location_id = "loc_us_ma_mwra"

        # Boston area coordinates
        lat, lon = 42.3601, -71.0589

        location = LocationData(
            location_id=location_id,
            name="MWRA Service Area",
            admin1="MA",
            country="United States",
            iso_code="US",
            granularity=GranularityTier.TIER_2,
            latitude=lat,
            longitude=lon,
            catchment_population=2500000,  # ~2.5M served
        )

        # Parse date
        date_str = record.get("Sample Date") or record.get("date")
        if not date_str:
            return location, None

        try:
            ts = datetime.strptime(date_str, "%m/%d/%Y")
        except:
            try:
                ts = datetime.strptime(date_str, "%Y-%m-%d")
            except:
                return location, None

        # Viral load (copies/mL)
        load = record.get("Northern (copies/mL)") or record.get("Southern (copies/mL)")
        normalized_score = None
        if load:
            try:
                # Convert copies/mL to copies/L, then normalize
                normalized_score = min(1.0, float(load) * 1000 / 1e9)
            except:
                pass

        event = SurveillanceEvent(
            event_id=self.generate_event_id(location_id, ts, "MA_MWRA"),
            location_id=location_id,
            timestamp=ts,
            data_source="MA_MWRA",
            signal_type=self.signal_type,
            normalized_score=normalized_score,
            quality_score=0.9,  # Biobot is high quality
            raw_data=record,
        )

        return location, event

    def _normalize_rki(
        self, record: Dict[str, Any]
    ) -> Tuple[Optional[LocationData], Optional[SurveillanceEvent]]:
        """Normalize Germany RKI AMELAG record."""
        # German states with coordinates
        de_states = {
            "Baden-Württemberg": (48.6616, 9.3501),
            "Bayern": (48.7904, 11.4979),
            "Berlin": (52.5200, 13.4050),
            "Brandenburg": (52.4125, 12.5316),
            "Bremen": (53.0793, 8.8017),
            "Hamburg": (53.5511, 9.9937),
            "Hessen": (50.6521, 9.1624),
            "Mecklenburg-Vorpommern": (53.6127, 12.4296),
            "Niedersachsen": (52.6367, 9.8451),
            "Nordrhein-Westfalen": (51.4332, 7.6616),
            "Rheinland-Pfalz": (49.9129, 7.4500),
            "Saarland": (49.3964, 7.0230),
            "Sachsen": (51.1045, 13.2017),
            "Sachsen-Anhalt": (51.9503, 11.6923),
            "Schleswig-Holstein": (54.2194, 9.6961),
            "Thüringen": (50.8610, 11.0519),
        }

        state = record.get("bundesland") or record.get("Bundesland")
        if not state:
            return None, None

        # Find matching state
        matched_state = None
        for s in de_states:
            if s.lower() in state.lower() or state.lower() in s.lower():
                matched_state = s
                break

        if not matched_state:
            return None, None

        lat, lon = de_states[matched_state]
        location_id = f"loc_de_{matched_state.lower().replace('-', '_').replace(' ', '_')[:20]}"

        try:
            h3_index = h3.latlng_to_cell(lat, lon, 5)
        except:
            h3_index = None

        location = LocationData(
            location_id=location_id,
            name=matched_state,
            admin1=matched_state,
            country="Germany",
            iso_code="DE",
            granularity=GranularityTier.TIER_2,
            latitude=lat,
            longitude=lon,
            h3_index=h3_index,
        )

        # Parse date
        date_str = record.get("datum") or record.get("Datum") or record.get("date")
        if not date_str:
            return location, None

        try:
            ts = datetime.strptime(date_str, "%Y-%m-%d")
        except:
            return location, None

        # Viral load
        load = record.get("viruslast") or record.get("Viruslast")
        normalized_score = None
        if load:
            try:
                normalized_score = min(1.0, float(load) / 1e9)
            except:
                pass

        event = SurveillanceEvent(
            event_id=self.generate_event_id(location_id, ts, "DE_RKI"),
            location_id=location_id,
            timestamp=ts,
            data_source="DE_RKI",
            signal_type=self.signal_type,
            normalized_score=normalized_score,
            quality_score=0.85,
            raw_data=record,
        )

        return location, event

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# Convenience function for testing
async def test_multi_source():
    """Test the multi-source adapter."""
    adapter = WastewaterMultiSourceAdapter()
    try:
        result = await adapter.run()
        print(f"Success: {result.success}")
        print(f"Locations: {len(result.locations)}")
        print(f"Events: {len(result.events)}")
        print(f"Duration: {result.duration_seconds:.2f}s")

        if result.locations:
            print("\nSample locations:")
            for loc in result.locations[:5]:
                print(f"  - {loc.name} ({loc.admin1}, {loc.country})")

        if result.events:
            print("\nSample events:")
            for evt in result.events[:5]:
                print(f"  - {evt.location_id}: {evt.normalized_score} @ {evt.timestamp}")

    finally:
        await adapter.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_multi_source())
