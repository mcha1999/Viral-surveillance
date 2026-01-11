"""
European Union Wastewater Surveillance Adapters

Consolidated adapter for EU countries not yet implemented:
- Spain (ISCIII)
- Italy (ISS)
- Austria (AGES)
- Switzerland (BAG)
- Belgium (Sciensano)
- Denmark (SSI)

Plus integration with the new EU Wastewater Observatory (JRC)
launched January 2025.
"""

import os
import csv
import io
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

import httpx
import h3

from .base import (
    BaseAdapter,
    LocationData,
    SurveillanceEvent,
    SignalType,
    GranularityTier,
)


class EUWastewaterObservatoryAdapter(BaseAdapter):
    """
    Adapter for EU Wastewater Observatory (JRC).

    The EU-wide dashboard launched January 2025 aggregates data from
    multiple member states.
    """

    source_id = "EU_OBSERVATORY"
    source_name = "EU Wastewater Observatory"
    signal_type = SignalType.WASTEWATER

    # EU Observatory endpoints (as of Jan 2025)
    OBSERVATORY_BASE = "https://wastewater-observatory.jrc.ec.europa.eu"
    API_ENDPOINT = f"{OBSERVATORY_BASE}/api/v1/data"

    # EU member states with wastewater programs
    EU_COUNTRIES = {
        "AT": {"name": "Austria", "lat": 47.5162, "lon": 14.5501, "pop": 9000000},
        "BE": {"name": "Belgium", "lat": 50.5039, "lon": 4.4699, "pop": 11600000},
        "DK": {"name": "Denmark", "lat": 56.2639, "lon": 9.5018, "pop": 5900000},
        "FI": {"name": "Finland", "lat": 61.9241, "lon": 25.7482, "pop": 5500000},
        "FR": {"name": "France", "lat": 46.2276, "lon": 2.2137, "pop": 67400000},
        "DE": {"name": "Germany", "lat": 51.1657, "lon": 10.4515, "pop": 83200000},
        "IE": {"name": "Ireland", "lat": 53.1424, "lon": -7.6921, "pop": 5100000},
        "IT": {"name": "Italy", "lat": 41.8719, "lon": 12.5674, "pop": 59100000},
        "LU": {"name": "Luxembourg", "lat": 49.8153, "lon": 6.1296, "pop": 650000},
        "NL": {"name": "Netherlands", "lat": 52.1326, "lon": 5.2913, "pop": 17500000},
        "PT": {"name": "Portugal", "lat": 39.3999, "lon": -8.2245, "pop": 10300000},
        "ES": {"name": "Spain", "lat": 40.4637, "lon": -3.7492, "pop": 47400000},
        "SE": {"name": "Sweden", "lat": 60.1282, "lon": 18.6435, "pop": 10400000},
        "CH": {"name": "Switzerland", "lat": 46.8182, "lon": 8.2275, "pop": 8700000},
    }

    def __init__(self):
        super().__init__()
        self.client = httpx.AsyncClient(timeout=60.0, follow_redirects=True)

    async def fetch(self) -> List[Dict[str, Any]]:
        """Fetch from EU Observatory API."""
        self.logger.info("Fetching from EU Wastewater Observatory")
        records = []

        # Try the API first
        try:
            response = await self.client.get(
                self.API_ENDPOINT,
                params={
                    "pathogen": "SARS-CoV-2",
                    "limit": 10000,
                }
            )

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    records = data
                elif isinstance(data, dict) and "data" in data:
                    records = data["data"]

                self.logger.info(f"Fetched {len(records)} records from EU Observatory")
                return records

        except Exception as e:
            self.logger.warning(f"EU Observatory API not accessible: {e}")

        # Fall back to individual country sources
        self.logger.info("Falling back to individual country sources")
        for iso, info in self.EU_COUNTRIES.items():
            try:
                country_records = await self._fetch_country_fallback(iso, info)
                records.extend(country_records)
            except Exception as e:
                self.logger.warning(f"Failed to fetch {info['name']}: {e}")

        return records

    async def _fetch_country_fallback(
        self,
        iso: str,
        info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Fetch from country-specific sources as fallback.

        These are best-effort based on known public data sources.
        """
        records = []

        # Country-specific fallback URLs
        fallback_sources = {
            "ES": "https://cnecovid.isciii.es/covid19/resources/datos_aguas_residuales.csv",
            "IT": "https://github.com/italia/covid19-opendata-vaccini/raw/master/dati/wastewater.csv",
            "AT": "https://data.gv.at/katalog/api/3/action/datastore_search?resource_id=covid-abwasser",
            "CH": "https://www.covid19.admin.ch/api/data/context",
            "BE": "https://epistat.sciensano.be/Data/COVID19BE_WASTEWATER.csv",
            "DK": "https://covid19.ssi.dk/overvagningsdata/download-fil-med-overvaagningsdata",
        }

        if iso not in fallback_sources:
            return records

        url = fallback_sources[iso]

        try:
            response = await self.client.get(url)

            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")

                if "csv" in content_type or url.endswith(".csv"):
                    # Parse CSV
                    reader = csv.DictReader(io.StringIO(response.text))
                    for row in reader:
                        row["_country"] = info["name"]
                        row["_iso"] = iso
                        row["_source"] = f"fallback_{iso}"
                        records.append(row)

                elif "json" in content_type:
                    # Parse JSON
                    data = response.json()
                    if isinstance(data, list):
                        for item in data:
                            item["_country"] = info["name"]
                            item["_iso"] = iso
                            item["_source"] = f"fallback_{iso}"
                            records.append(item)

                self.logger.info(f"Fetched {len(records)} records for {info['name']}")

        except Exception as e:
            self.logger.debug(f"Fallback for {info['name']} failed: {e}")

        return records

    def normalize(
        self,
        raw_data: List[Dict[str, Any]]
    ) -> Tuple[List[LocationData], List[SurveillanceEvent]]:
        """Normalize EU data to standard schema."""
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
                self.logger.warning(f"Failed to normalize record: {e}")
                continue

        return list(locations_map.values()), events

    def _extract_location(self, record: Dict[str, Any]) -> Optional[LocationData]:
        """Extract location from EU record."""
        # Try various field names for country
        iso = (
            record.get("_iso") or
            record.get("country_code") or
            record.get("iso") or
            record.get("countryCode")
        )

        if not iso or iso not in self.EU_COUNTRIES:
            # Try to match by country name
            country_name = (
                record.get("_country") or
                record.get("country") or
                record.get("Country")
            )
            if country_name:
                for code, info in self.EU_COUNTRIES.items():
                    if info["name"].lower() == country_name.lower():
                        iso = code
                        break

        if not iso or iso not in self.EU_COUNTRIES:
            return None

        info = self.EU_COUNTRIES[iso]

        # Check for region/site level data
        region = (
            record.get("region") or
            record.get("site") or
            record.get("location")
        )

        if region:
            location_id = f"loc_{iso.lower()}_{hashlib.md5(region.encode()).hexdigest()[:8]}"
            name = region
            granularity = GranularityTier.TIER_1
        else:
            location_id = f"loc_{iso.lower()}_national"
            name = info["name"]
            granularity = GranularityTier.TIER_3

        try:
            h3_index = h3.latlng_to_cell(info["lat"], info["lon"], 5)
        except:
            h3_index = None

        return LocationData(
            location_id=location_id,
            name=name,
            admin1=region or info["name"],
            country=info["name"],
            iso_code=iso,
            granularity=granularity,
            latitude=info["lat"],
            longitude=info["lon"],
            catchment_population=info["pop"],
            h3_index=h3_index,
        )

    def _extract_event(
        self,
        record: Dict[str, Any],
        location_id: str
    ) -> Optional[SurveillanceEvent]:
        """Extract surveillance event from EU record."""
        # Try various date field names
        date_str = (
            record.get("date") or
            record.get("sample_date") or
            record.get("Date") or
            record.get("collection_date") or
            record.get("week")
        )

        if not date_str:
            return None

        try:
            # Handle various date formats
            if isinstance(date_str, str):
                for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y"]:
                    try:
                        timestamp = datetime.strptime(date_str.split("T")[0], fmt)
                        break
                    except ValueError:
                        continue
                else:
                    return None
            else:
                timestamp = datetime.utcnow()
        except:
            return None

        # Get viral load metrics
        raw_load = None
        normalized_score = None
        velocity = None

        # Try various metric field names
        for field in ["viral_load", "concentration", "value", "copies_per_liter", "load"]:
            if field in record and record[field]:
                try:
                    raw_load = float(str(record[field]).replace(",", "."))
                    normalized_score = min(1.0, raw_load / 1e9)
                    break
                except:
                    pass

        # Try velocity/trend fields
        for field in ["trend", "change", "percent_change", "velocity"]:
            if field in record and record[field]:
                try:
                    velocity = float(str(record[field]).replace(",", ".")) / 100
                    break
                except:
                    pass

        source = record.get("_source", "EU_OBSERVATORY")

        return SurveillanceEvent(
            event_id=self.generate_event_id(location_id, timestamp, source),
            location_id=location_id,
            timestamp=timestamp,
            data_source=source,
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


class SpainISCIIIAdapter(BaseAdapter):
    """
    Adapter for Spain ISCIII wastewater surveillance.

    Instituto de Salud Carlos III provides national wastewater data.
    """

    source_id = "ES_ISCIII"
    source_name = "Spain ISCIII"
    signal_type = SignalType.WASTEWATER

    DATA_URL = "https://cnecovid.isciii.es/covid19/resources/datos_aguas_residuales.csv"

    # Spanish autonomous communities
    ES_REGIONS = {
        "Andalucía": {"lat": 37.5443, "lon": -4.7278, "pop": 8472407},
        "Aragón": {"lat": 41.5976, "lon": -0.9057, "pop": 1329391},
        "Asturias": {"lat": 43.3614, "lon": -5.8593, "pop": 1011792},
        "Baleares": {"lat": 39.5713, "lon": 2.6502, "pop": 1219439},
        "Canarias": {"lat": 28.2916, "lon": -16.6291, "pop": 2237309},
        "Cantabria": {"lat": 43.1828, "lon": -3.9878, "pop": 584507},
        "Castilla y León": {"lat": 41.8357, "lon": -4.3976, "pop": 2383139},
        "Castilla-La Mancha": {"lat": 39.2796, "lon": -3.0977, "pop": 2049562},
        "Cataluña": {"lat": 41.5912, "lon": 1.5209, "pop": 7780479},
        "Comunidad Valenciana": {"lat": 39.4699, "lon": -0.3763, "pop": 5057353},
        "Extremadura": {"lat": 39.4937, "lon": -6.0679, "pop": 1059501},
        "Galicia": {"lat": 42.5751, "lon": -8.1339, "pop": 2701819},
        "Madrid": {"lat": 40.4168, "lon": -3.7038, "pop": 6779888},
        "Murcia": {"lat": 37.9922, "lon": -1.1307, "pop": 1518486},
        "Navarra": {"lat": 42.6954, "lon": -1.6761, "pop": 661197},
        "País Vasco": {"lat": 42.9896, "lon": -2.6189, "pop": 2220504},
        "La Rioja": {"lat": 42.2871, "lon": -2.5396, "pop": 319914},
        "Ceuta": {"lat": 35.8894, "lon": -5.3198, "pop": 84202},
        "Melilla": {"lat": 35.2923, "lon": -2.9381, "pop": 87076},
    }

    def __init__(self):
        super().__init__()
        self.client = httpx.AsyncClient(timeout=60.0)

    async def fetch(self) -> List[Dict[str, Any]]:
        """Fetch from ISCIII."""
        self.logger.info("Fetching from Spain ISCIII")

        try:
            response = await self.client.get(self.DATA_URL)
            response.raise_for_status()

            # Parse CSV (semicolon-separated)
            reader = csv.DictReader(io.StringIO(response.text), delimiter=";")
            records = list(reader)

            self.logger.info(f"Fetched {len(records)} records from ISCIII")
            return records

        except httpx.HTTPError as e:
            self.logger.error(f"Failed to fetch ISCIII data: {e}")
            return []

    def normalize(
        self,
        raw_data: List[Dict[str, Any]]
    ) -> Tuple[List[LocationData], List[SurveillanceEvent]]:
        """Normalize Spain ISCIII data."""
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
                self.logger.warning(f"Failed to process ISCIII record: {e}")
                continue

        return list(locations_map.values()), events

    def _extract_location(self, record: Dict[str, Any]) -> Optional[LocationData]:
        """Extract location from ISCIII record."""
        region = (
            record.get("ccaa") or
            record.get("comunidad") or
            record.get("region")
        )

        if not region:
            return None

        # Match region
        matched = None
        for r in self.ES_REGIONS:
            if r.lower() in region.lower() or region.lower() in r.lower():
                matched = r
                break

        if not matched:
            return None

        info = self.ES_REGIONS[matched]
        location_id = f"loc_es_{matched.lower().replace(' ', '_')[:15]}"

        try:
            h3_index = h3.latlng_to_cell(info["lat"], info["lon"], 5)
        except:
            h3_index = None

        return LocationData(
            location_id=location_id,
            name=matched,
            admin1=matched,
            country="Spain",
            iso_code="ES",
            granularity=GranularityTier.TIER_2,
            latitude=info["lat"],
            longitude=info["lon"],
            catchment_population=info["pop"],
            h3_index=h3_index,
        )

    def _extract_event(
        self,
        record: Dict[str, Any],
        location_id: str
    ) -> Optional[SurveillanceEvent]:
        """Extract event from ISCIII record."""
        date_str = record.get("fecha") or record.get("date")
        if not date_str:
            return None

        try:
            timestamp = datetime.strptime(date_str, "%Y-%m-%d")
        except:
            try:
                timestamp = datetime.strptime(date_str, "%d/%m/%Y")
            except:
                return None

        # Get viral load
        load_str = record.get("carga_viral") or record.get("viral_load")
        raw_load = None
        normalized_score = None

        if load_str:
            try:
                raw_load = float(str(load_str).replace(",", "."))
                normalized_score = min(1.0, raw_load / 1e9)
            except:
                pass

        return SurveillanceEvent(
            event_id=self.generate_event_id(location_id, timestamp, self.source_id),
            location_id=location_id,
            timestamp=timestamp,
            data_source=self.source_id,
            signal_type=self.signal_type,
            raw_load=raw_load,
            normalized_score=normalized_score,
            quality_score=0.85,
            raw_data=record,
        )

    async def close(self):
        await self.client.aclose()


class CanadaWastewaterAdapter(BaseAdapter):
    """
    Adapter for Canadian wastewater surveillance data.
    """

    source_id = "CA_PHAC"
    source_name = "Canada PHAC"
    signal_type = SignalType.WASTEWATER

    # Public Health Agency of Canada wastewater data
    DATA_URL = "https://health-infobase.canada.ca/src/data/covidLive/wastewater.csv"

    CA_PROVINCES = {
        "Ontario": {"lat": 51.2538, "lon": -85.3232, "pop": 14915000, "code": "ON"},
        "Quebec": {"lat": 52.9399, "lon": -73.5491, "pop": 8604000, "code": "QC"},
        "British Columbia": {"lat": 53.7267, "lon": -127.6476, "pop": 5214000, "code": "BC"},
        "Alberta": {"lat": 53.9333, "lon": -116.5765, "pop": 4464000, "code": "AB"},
        "Manitoba": {"lat": 53.7609, "lon": -98.8139, "pop": 1393000, "code": "MB"},
        "Saskatchewan": {"lat": 52.9399, "lon": -106.4509, "pop": 1194000, "code": "SK"},
        "Nova Scotia": {"lat": 44.6820, "lon": -63.7443, "pop": 1000000, "code": "NS"},
        "New Brunswick": {"lat": 46.5653, "lon": -66.4619, "pop": 789000, "code": "NB"},
        "Newfoundland and Labrador": {"lat": 53.1355, "lon": -57.6604, "pop": 521000, "code": "NL"},
        "Prince Edward Island": {"lat": 46.5107, "lon": -63.4168, "pop": 164000, "code": "PE"},
    }

    def __init__(self):
        super().__init__()
        self.client = httpx.AsyncClient(timeout=60.0)

    async def fetch(self) -> List[Dict[str, Any]]:
        """Fetch Canadian wastewater data."""
        self.logger.info("Fetching from Canada PHAC")

        try:
            response = await self.client.get(self.DATA_URL)
            response.raise_for_status()

            reader = csv.DictReader(io.StringIO(response.text))
            records = list(reader)

            self.logger.info(f"Fetched {len(records)} records from Canada PHAC")
            return records

        except httpx.HTTPError as e:
            self.logger.error(f"Failed to fetch Canada data: {e}")
            return []

    def normalize(
        self,
        raw_data: List[Dict[str, Any]]
    ) -> Tuple[List[LocationData], List[SurveillanceEvent]]:
        """Normalize Canadian data."""
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
                self.logger.warning(f"Failed to process Canada record: {e}")

        return list(locations_map.values()), events

    def _extract_location(self, record: Dict[str, Any]) -> Optional[LocationData]:
        """Extract location from Canada record."""
        province = record.get("province") or record.get("region")
        if not province:
            return None

        # Match province
        matched = None
        for p, info in self.CA_PROVINCES.items():
            if (p.lower() in province.lower() or
                province.lower() in p.lower() or
                info["code"].lower() == province.lower()):
                matched = p
                break

        if not matched:
            return None

        info = self.CA_PROVINCES[matched]
        location_id = f"loc_ca_{info['code'].lower()}"

        return LocationData(
            location_id=location_id,
            name=matched,
            admin1=matched,
            country="Canada",
            iso_code="CA",
            granularity=GranularityTier.TIER_2,
            latitude=info["lat"],
            longitude=info["lon"],
            catchment_population=info["pop"],
        )

    def _extract_event(
        self,
        record: Dict[str, Any],
        location_id: str
    ) -> Optional[SurveillanceEvent]:
        """Extract event from Canada record."""
        date_str = record.get("date") or record.get("week_end")
        if not date_str:
            return None

        try:
            timestamp = datetime.strptime(date_str, "%Y-%m-%d")
        except:
            return None

        # Get viral signal
        value = record.get("viral_load") or record.get("value")
        normalized_score = None

        if value:
            try:
                raw = float(str(value).replace(",", ""))
                normalized_score = min(1.0, raw / 1e9)
            except:
                pass

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

    async def close(self):
        await self.client.aclose()


class NewZealandESRAdapter(BaseAdapter):
    """
    Adapter for New Zealand ESR wastewater surveillance.
    """

    source_id = "NZ_ESR"
    source_name = "New Zealand ESR"
    signal_type = SignalType.WASTEWATER

    # ESR GitHub data
    DATA_URL = "https://raw.githubusercontent.com/ESR-NZ/covid_in_wastewater/main/data/national_wastewater_data.csv"

    NZ_REGIONS = {
        "Auckland": {"lat": -36.8509, "lon": 174.7645, "pop": 1700000},
        "Wellington": {"lat": -41.2865, "lon": 174.7762, "pop": 420000},
        "Christchurch": {"lat": -43.5320, "lon": 172.6306, "pop": 390000},
        "Hamilton": {"lat": -37.7870, "lon": 175.2793, "pop": 180000},
        "Tauranga": {"lat": -37.6878, "lon": 176.1651, "pop": 155000},
        "Dunedin": {"lat": -45.8788, "lon": 170.5028, "pop": 135000},
    }

    def __init__(self):
        super().__init__()
        self.client = httpx.AsyncClient(timeout=60.0)

    async def fetch(self) -> List[Dict[str, Any]]:
        """Fetch NZ ESR data."""
        self.logger.info("Fetching from New Zealand ESR")

        try:
            response = await self.client.get(self.DATA_URL)
            response.raise_for_status()

            reader = csv.DictReader(io.StringIO(response.text))
            records = list(reader)

            self.logger.info(f"Fetched {len(records)} records from NZ ESR")
            return records

        except httpx.HTTPError as e:
            self.logger.error(f"Failed to fetch NZ ESR data: {e}")
            return []

    def normalize(
        self,
        raw_data: List[Dict[str, Any]]
    ) -> Tuple[List[LocationData], List[SurveillanceEvent]]:
        """Normalize NZ data."""
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
                self.logger.warning(f"Failed to process NZ record: {e}")

        return list(locations_map.values()), events

    def _extract_location(self, record: Dict[str, Any]) -> Optional[LocationData]:
        """Extract location from NZ record."""
        site = record.get("site") or record.get("location") or record.get("city")
        if not site:
            # National level
            return LocationData(
                location_id="loc_nz_national",
                name="New Zealand",
                admin1="New Zealand",
                country="New Zealand",
                iso_code="NZ",
                granularity=GranularityTier.TIER_3,
                latitude=-40.9006,
                longitude=174.8860,
                catchment_population=5100000,
            )

        # Match to known region
        for region, info in self.NZ_REGIONS.items():
            if region.lower() in site.lower():
                return LocationData(
                    location_id=f"loc_nz_{region.lower()}",
                    name=region,
                    admin1=region,
                    country="New Zealand",
                    iso_code="NZ",
                    granularity=GranularityTier.TIER_1,
                    latitude=info["lat"],
                    longitude=info["lon"],
                    catchment_population=info["pop"],
                )

        return None

    def _extract_event(
        self,
        record: Dict[str, Any],
        location_id: str
    ) -> Optional[SurveillanceEvent]:
        """Extract event from NZ record."""
        date_str = record.get("date") or record.get("week_ending")
        if not date_str:
            return None

        try:
            timestamp = datetime.strptime(date_str, "%Y-%m-%d")
        except:
            return None

        value = record.get("copies_per_person_per_day") or record.get("value")
        normalized_score = None

        if value:
            try:
                raw = float(str(value).replace(",", ""))
                # NZ uses copies per person per day, normalize differently
                normalized_score = min(1.0, raw / 1e6)
            except:
                pass

        return SurveillanceEvent(
            event_id=self.generate_event_id(location_id, timestamp, self.source_id),
            location_id=location_id,
            timestamp=timestamp,
            data_source=self.source_id,
            signal_type=self.signal_type,
            normalized_score=normalized_score,
            quality_score=0.90,  # ESR is high quality
            raw_data=record,
        )

    async def close(self):
        await self.client.aclose()
