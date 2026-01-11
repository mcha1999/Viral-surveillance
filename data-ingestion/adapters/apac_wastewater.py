"""
Asia-Pacific Wastewater Adapters

Additional wastewater surveillance data sources for Asia-Pacific region:
- Singapore NEA (National Environment Agency)
- South Korea KDCA (Korea Disease Control and Prevention Agency)
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


class SingaporeNEAAdapter(BaseAdapter):
    """
    Adapter for Singapore National Environment Agency wastewater data.

    Data source: https://data.gov.sg/
    Coverage: Singapore national and regional wastewater treatment plants
    Frequency: Weekly updates
    """

    source_id = "SG_NEA"
    source_name = "Singapore National Environment Agency"
    signal_type = SignalType.WASTEWATER

    # Singapore Data.gov.sg API
    BASE_URL = "https://data.gov.sg/api/action/datastore_search"

    # Singapore regions and wastewater treatment plants
    SG_LOCATIONS = {
        "Singapore": {
            "lat": 1.3521,
            "lon": 103.8198,
            "pop": 5900000,
            "plants": ["Changi", "Jurong", "Kranji", "Ulu Pandan"]
        },
        "Central": {"lat": 1.2903, "lon": 103.8519, "pop": 1200000},
        "East": {"lat": 1.3367, "lon": 103.9499, "pop": 800000},
        "North": {"lat": 1.4382, "lon": 103.8000, "pop": 600000},
        "North-East": {"lat": 1.3722, "lon": 103.8936, "pop": 900000},
        "West": {"lat": 1.3462, "lon": 103.6911, "pop": 1000000},
    }

    def __init__(self):
        super().__init__()
        self.client = httpx.AsyncClient(timeout=60.0, follow_redirects=True)

    async def fetch(self) -> List[Dict[str, Any]]:
        """Fetch wastewater data from Singapore data.gov.sg."""
        self.logger.info("Fetching from Singapore NEA")

        all_records = []

        # Try multiple potential dataset IDs for wastewater/COVID surveillance
        dataset_ids = [
            "covid-19-case-numbers",  # Known COVID dataset
            "environmental-monitoring",
            "wastewater-surveillance",
        ]

        for dataset_id in dataset_ids:
            try:
                params = {
                    "resource_id": dataset_id,
                    "limit": 1000,
                }

                response = await self.client.get(self.BASE_URL, params=params)

                if response.status_code == 200:
                    data = response.json()
                    if data.get("success") and "result" in data:
                        records = data["result"].get("records", [])
                        if records:
                            for record in records:
                                record["_source_dataset"] = dataset_id
                            all_records.extend(records)
                            self.logger.info(
                                f"Found {len(records)} records from dataset: {dataset_id}"
                            )
                            break

            except httpx.HTTPError as e:
                self.logger.warning(f"Failed to fetch dataset {dataset_id}: {e}")
                continue

        if not all_records:
            self.logger.error(
                "Failed to fetch Singapore NEA data from any dataset. "
                "Returning empty data - NOT using synthetic fallback."
            )
            return []

        self.logger.info(f"Total Singapore NEA records: {len(all_records)}")
        return all_records

    def normalize(
        self,
        raw_data: List[Dict[str, Any]]
    ) -> Tuple[List[LocationData], List[SurveillanceEvent]]:
        """Normalize Singapore NEA data to standard schema."""
        locations_map: Dict[str, LocationData] = {}
        events: List[SurveillanceEvent] = []

        # Create national location
        sg_info = self.SG_LOCATIONS["Singapore"]
        national_loc = LocationData(
            location_id="loc_sg_national",
            name="Singapore",
            country="Singapore",
            iso_code="SG",
            granularity=GranularityTier.TIER_3,
            latitude=sg_info["lat"],
            longitude=sg_info["lon"],
            catchment_population=sg_info["pop"],
        )
        locations_map["loc_sg_national"] = national_loc

        for record in raw_data:
            try:
                event = self._extract_event(record, "loc_sg_national")
                if event:
                    events.append(event)
            except Exception as e:
                self.logger.warning(f"Failed to process record: {e}")
                continue

        return list(locations_map.values()), events

    def _extract_event(
        self,
        record: Dict[str, Any],
        location_id: str
    ) -> Optional[SurveillanceEvent]:
        """Extract surveillance event from Singapore record."""
        # Try various date field names
        date_str = (
            record.get("date") or
            record.get("week_of") or
            record.get("collection_date") or
            record.get("report_date")
        )

        if not date_str:
            return None

        try:
            # Handle various date formats
            for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"]:
                try:
                    timestamp = datetime.strptime(date_str[:10], fmt[:min(len(fmt), len(date_str))])
                    break
                except ValueError:
                    continue
            else:
                return None
        except Exception:
            return None

        # Try to get viral load or case count
        value = None
        for field in ["viral_load", "cases", "new_cases", "confirmed", "value"]:
            if record.get(field) is not None:
                try:
                    value = float(record[field])
                    break
                except (ValueError, TypeError):
                    continue

        normalized_score = None
        if value is not None:
            # Normalize based on expected range
            normalized_score = min(1.0, value / 10000.0)

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


class SouthKoreaKDCAAdapter(BaseAdapter):
    """
    Adapter for South Korea KDCA wastewater surveillance data.

    Data source: https://ncov.kdca.go.kr/ and data.go.kr
    Coverage: South Korean provinces and major cities
    Frequency: Weekly updates
    """

    source_id = "KR_KDCA"
    source_name = "Korea Disease Control and Prevention Agency"
    signal_type = SignalType.WASTEWATER

    # Korea Open Data API
    BASE_URL = "https://api.odcloud.kr/api"

    # Korean provinces with coordinates
    KR_PROVINCES = {
        "Seoul": {"lat": 37.5665, "lon": 126.9780, "pop": 9700000},
        "Busan": {"lat": 35.1796, "lon": 129.0756, "pop": 3400000},
        "Incheon": {"lat": 37.4563, "lon": 126.7052, "pop": 2900000},
        "Daegu": {"lat": 35.8714, "lon": 128.6014, "pop": 2400000},
        "Daejeon": {"lat": 36.3504, "lon": 127.3845, "pop": 1500000},
        "Gwangju": {"lat": 35.1595, "lon": 126.8526, "pop": 1500000},
        "Ulsan": {"lat": 35.5384, "lon": 129.3114, "pop": 1100000},
        "Sejong": {"lat": 36.4800, "lon": 127.2890, "pop": 360000},
        "Gyeonggi": {"lat": 37.4138, "lon": 127.5183, "pop": 13500000},
        "Gangwon": {"lat": 37.8228, "lon": 128.1555, "pop": 1500000},
        "Chungbuk": {"lat": 36.6357, "lon": 127.4917, "pop": 1600000},
        "Chungnam": {"lat": 36.5184, "lon": 126.8000, "pop": 2100000},
        "Jeonbuk": {"lat": 35.8200, "lon": 127.1089, "pop": 1800000},
        "Jeonnam": {"lat": 34.8679, "lon": 126.9910, "pop": 1900000},
        "Gyeongbuk": {"lat": 36.5760, "lon": 128.5056, "pop": 2600000},
        "Gyeongnam": {"lat": 35.4606, "lon": 128.2132, "pop": 3400000},
        "Jeju": {"lat": 33.4996, "lon": 126.5312, "pop": 670000},
    }

    def __init__(self):
        super().__init__()
        self.client = httpx.AsyncClient(timeout=60.0, follow_redirects=True)
        self.api_key = os.getenv("KOREA_OPENDATA_API_KEY")

    async def fetch(self) -> List[Dict[str, Any]]:
        """Fetch wastewater data from Korea Open Data Portal."""
        self.logger.info("Fetching from South Korea KDCA")

        all_records = []

        # KDCA COVID-19 data endpoint
        # Note: Actual wastewater endpoint may require registration
        endpoints = [
            "/15077756/v1/covid19-domestic-occur-status",  # COVID domestic status
            "/15077757/v1/covid19-si-do-occur-status",  # By province
        ]

        for endpoint in endpoints:
            try:
                params = {
                    "page": 1,
                    "perPage": 500,
                    "serviceKey": self.api_key or "test",
                }

                url = f"{self.BASE_URL}{endpoint}"
                response = await self.client.get(url, params=params)

                if response.status_code == 200:
                    data = response.json()
                    if "data" in data:
                        records = data["data"]
                        for record in records:
                            record["_endpoint"] = endpoint
                        all_records.extend(records)
                        self.logger.info(f"Found {len(records)} records from {endpoint}")

            except httpx.HTTPError as e:
                self.logger.warning(f"Failed to fetch {endpoint}: {e}")
                continue

        if not all_records:
            self.logger.error(
                "Failed to fetch South Korea KDCA data. "
                "Returning empty data - NOT using synthetic fallback. "
                "Note: KOREA_OPENDATA_API_KEY environment variable may be required."
            )
            return []

        self.logger.info(f"Total South Korea KDCA records: {len(all_records)}")
        return all_records

    def normalize(
        self,
        raw_data: List[Dict[str, Any]]
    ) -> Tuple[List[LocationData], List[SurveillanceEvent]]:
        """Normalize South Korea KDCA data to standard schema."""
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
        """Extract location from KDCA record."""
        # Try various field names for location
        province = (
            record.get("gubun") or
            record.get("province") or
            record.get("region") or
            record.get("시도명")
        )

        if not province or province in ["합계", "Total"]:
            return None

        # Match to our province list
        matched_province = None
        for p in self.KR_PROVINCES:
            if p.lower() in province.lower() or province.lower() in p.lower():
                matched_province = p
                break

        if not matched_province:
            return None

        prov_info = self.KR_PROVINCES[matched_province]

        try:
            h3_index = h3.latlng_to_cell(prov_info["lat"], prov_info["lon"], 5)
        except Exception:
            h3_index = None

        location_id = f"loc_kr_{matched_province.lower().replace(' ', '_')}"

        return LocationData(
            location_id=location_id,
            name=matched_province,
            admin1=matched_province,
            country="South Korea",
            iso_code="KR",
            granularity=GranularityTier.TIER_2,
            latitude=prov_info["lat"],
            longitude=prov_info["lon"],
            catchment_population=prov_info["pop"],
            h3_index=h3_index,
        )

    def _extract_event(
        self,
        record: Dict[str, Any],
        location_id: str
    ) -> Optional[SurveillanceEvent]:
        """Extract surveillance event from KDCA record."""
        date_str = (
            record.get("createDt") or
            record.get("stdDay") or
            record.get("date") or
            record.get("기준일")
        )

        if not date_str:
            return None

        try:
            # Handle various date formats
            for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y%m%d"]:
                try:
                    timestamp = datetime.strptime(date_str[:len(fmt.replace("%", ""))], fmt)
                    break
                except ValueError:
                    continue
            else:
                return None
        except Exception:
            return None

        # Get case/viral data
        value = None
        for field in ["incDec", "defCnt", "isolCnt", "confirmed", "신규확진"]:
            if record.get(field) is not None:
                try:
                    value = float(str(record[field]).replace(",", ""))
                    break
                except (ValueError, TypeError):
                    continue

        normalized_score = None
        if value is not None:
            # Normalize based on expected daily case range
            normalized_score = min(1.0, value / 50000.0)

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
        """Close HTTP client."""
        await self.client.aclose()


# Convenience function for testing
async def test_apac_adapters():
    """Test the APAC wastewater adapters."""
    adapters = [
        ("Singapore NEA", SingaporeNEAAdapter),
        ("South Korea KDCA", SouthKoreaKDCAAdapter),
    ]

    for name, adapter_class in adapters:
        print(f"\n{'='*50}")
        print(f"Testing {name}")
        print("=" * 50)

        try:
            adapter = adapter_class()
            raw_data = await adapter.fetch()
            print(f"Raw records fetched: {len(raw_data)}")

            if raw_data:
                locations, events = adapter.normalize(raw_data)
                print(f"Locations normalized: {len(locations)}")
                print(f"Events normalized: {len(events)}")

                if locations:
                    print(f"Sample location: {locations[0].name}")

            await adapter.close()

        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_apac_adapters())
