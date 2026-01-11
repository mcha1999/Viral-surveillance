"""
Japan NIID (National Institute of Infectious Diseases) Wastewater Adapter

Data source: https://www.niid.go.jp/niid/en/
Coverage: Japanese prefectures
Frequency: Updated weekly
Granularity: Tier 1 (Prefecture level)
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


class JPNIIDAdapter(BaseAdapter):
    """
    Adapter for Japan NIID wastewater surveillance data.

    Fetches from NIID open data resources.
    """

    source_id = "NIID"
    source_name = "Japan NIID"
    signal_type = SignalType.WASTEWATER

    # Data URL - NIID wastewater surveillance
    DATA_URL = "https://www.niid.go.jp/niid/images/cepr/covid-19/wastewater_data.csv"

    # Japanese prefectures with coordinates and populations
    JP_PREFECTURES = {
        "Hokkaido": {"lat": 43.0642, "lon": 141.3469, "pop": 5224614},
        "Aomori": {"lat": 40.8244, "lon": 140.7400, "pop": 1237984},
        "Iwate": {"lat": 39.7036, "lon": 141.1527, "pop": 1210534},
        "Miyagi": {"lat": 38.2688, "lon": 140.8721, "pop": 2301996},
        "Akita": {"lat": 39.7186, "lon": 140.1024, "pop": 959502},
        "Yamagata": {"lat": 38.2405, "lon": 140.3634, "pop": 1068027},
        "Fukushima": {"lat": 37.7500, "lon": 140.4678, "pop": 1833152},
        "Ibaraki": {"lat": 36.3418, "lon": 140.4468, "pop": 2867009},
        "Tochigi": {"lat": 36.5657, "lon": 139.8836, "pop": 1933146},
        "Gunma": {"lat": 36.3912, "lon": 139.0608, "pop": 1939110},
        "Saitama": {"lat": 35.8569, "lon": 139.6489, "pop": 7344765},
        "Chiba": {"lat": 35.6047, "lon": 140.1233, "pop": 6284480},
        "Tokyo": {"lat": 35.6762, "lon": 139.6503, "pop": 14047594},
        "Kanagawa": {"lat": 35.4478, "lon": 139.6425, "pop": 9237337},
        "Niigata": {"lat": 37.9026, "lon": 139.0236, "pop": 2201272},
        "Toyama": {"lat": 36.6953, "lon": 137.2113, "pop": 1034814},
        "Ishikawa": {"lat": 36.5947, "lon": 136.6256, "pop": 1132526},
        "Fukui": {"lat": 36.0652, "lon": 136.2216, "pop": 766863},
        "Yamanashi": {"lat": 35.6642, "lon": 138.5684, "pop": 809974},
        "Nagano": {"lat": 36.6513, "lon": 138.1810, "pop": 2048011},
        "Gifu": {"lat": 35.3912, "lon": 136.7223, "pop": 1978742},
        "Shizuoka": {"lat": 34.9769, "lon": 138.3831, "pop": 3633202},
        "Aichi": {"lat": 35.1802, "lon": 136.9066, "pop": 7542415},
        "Mie": {"lat": 34.7303, "lon": 136.5086, "pop": 1770254},
        "Shiga": {"lat": 35.0045, "lon": 135.8685, "pop": 1413610},
        "Kyoto": {"lat": 35.0116, "lon": 135.7681, "pop": 2578087},
        "Osaka": {"lat": 34.6937, "lon": 135.5023, "pop": 8837685},
        "Hyogo": {"lat": 34.6913, "lon": 135.1830, "pop": 5465002},
        "Nara": {"lat": 34.6851, "lon": 135.8048, "pop": 1324473},
        "Wakayama": {"lat": 34.2260, "lon": 135.1675, "pop": 922584},
        "Tottori": {"lat": 35.5036, "lon": 134.2383, "pop": 553407},
        "Shimane": {"lat": 35.4723, "lon": 133.0505, "pop": 671126},
        "Okayama": {"lat": 34.6618, "lon": 133.9344, "pop": 1888432},
        "Hiroshima": {"lat": 34.3853, "lon": 132.4553, "pop": 2799702},
        "Yamaguchi": {"lat": 34.1859, "lon": 131.4714, "pop": 1342059},
        "Tokushima": {"lat": 34.0658, "lon": 134.5593, "pop": 719559},
        "Kagawa": {"lat": 34.3401, "lon": 134.0434, "pop": 950244},
        "Ehime": {"lat": 33.8416, "lon": 132.7657, "pop": 1334841},
        "Kochi": {"lat": 33.5597, "lon": 133.5311, "pop": 691527},
        "Fukuoka": {"lat": 33.6064, "lon": 130.4181, "pop": 5135214},
        "Saga": {"lat": 33.2494, "lon": 130.2988, "pop": 811442},
        "Nagasaki": {"lat": 32.7448, "lon": 129.8737, "pop": 1312317},
        "Kumamoto": {"lat": 32.7898, "lon": 130.7417, "pop": 1738301},
        "Oita": {"lat": 33.2382, "lon": 131.6126, "pop": 1123852},
        "Miyazaki": {"lat": 31.9111, "lon": 131.4239, "pop": 1069576},
        "Kagoshima": {"lat": 31.5602, "lon": 130.5581, "pop": 1588256},
        "Okinawa": {"lat": 26.2124, "lon": 127.6809, "pop": 1467480},
    }

    def __init__(self):
        super().__init__()
        self.client = httpx.AsyncClient(timeout=60.0, follow_redirects=True)

    async def fetch(self) -> List[Dict[str, Any]]:
        """Fetch wastewater data from NIID."""
        self.logger.info("Fetching from Japan NIID")

        try:
            response = await self.client.get(self.DATA_URL)
            response.raise_for_status()

            # Parse CSV (may be Shift-JIS encoded)
            try:
                content = response.content.decode("utf-8")
            except UnicodeDecodeError:
                content = response.content.decode("shift-jis")

            reader = csv.DictReader(io.StringIO(content))
            records = list(reader)

            self.logger.info(f"Received {len(records)} records from NIID")
            return records

        except httpx.HTTPError as e:
            self.logger.error(
                f"Failed to fetch NIID data: {e}. "
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

        for prefecture in self.JP_PREFECTURES:
            for days_ago in range(30):
                date = today - timedelta(days=days_ago)
                records.append({
                    "prefecture": prefecture,
                    "date": date.strftime("%Y-%m-%d"),
                    "viral_load": random.uniform(1e5, 1e8),
                    "trend": random.uniform(-15, 15),
                })

        return records

    def normalize(
        self,
        raw_data: List[Dict[str, Any]]
    ) -> tuple[List[LocationData], List[SurveillanceEvent]]:
        """Normalize NIID data to standard schema."""
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
        """Extract location from NIID record."""
        # Try various field names
        prefecture = (
            record.get("prefecture") or
            record.get("都道府県") or
            record.get("pref") or
            record.get("location")
        )

        if not prefecture:
            return None

        # Match prefecture name
        matched_pref = None
        for p in self.JP_PREFECTURES:
            if p.lower() == prefecture.lower() or prefecture in p:
                matched_pref = p
                break

        # Try romanization matching
        if not matched_pref:
            # Common romanization variants
            pref_aliases = {
                "東京": "Tokyo",
                "大阪": "Osaka",
                "北海道": "Hokkaido",
                "愛知": "Aichi",
                "福岡": "Fukuoka",
                "神奈川": "Kanagawa",
                "埼玉": "Saitama",
                "千葉": "Chiba",
                "兵庫": "Hyogo",
                "京都": "Kyoto",
            }
            if prefecture in pref_aliases:
                matched_pref = pref_aliases[prefecture]

        if not matched_pref:
            return None

        pref_info = self.JP_PREFECTURES[matched_pref]
        latitude = pref_info["lat"]
        longitude = pref_info["lon"]
        population = pref_info["pop"]

        # Generate H3 index
        try:
            h3_index = h3.latlng_to_cell(latitude, longitude, 5)
        except Exception:
            h3_index = None

        location_id = f"loc_jp_{matched_pref.lower().replace(' ', '_')}"

        return LocationData(
            location_id=location_id,
            name=matched_pref,
            admin1=matched_pref,
            country="Japan",
            iso_code="JP",
            granularity=GranularityTier.TIER_1,  # Prefecture level
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
        """Extract surveillance event from NIID record."""
        date_str = (
            record.get("date") or
            record.get("日付") or
            record.get("collection_date")
        )
        if not date_str:
            return None

        try:
            timestamp = datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            try:
                timestamp = datetime.strptime(date_str, "%Y/%m/%d")
            except ValueError:
                return None

        # Get metrics
        raw_load = None
        normalized_score = None
        velocity = None

        load_str = (
            record.get("viral_load") or
            record.get("concentration") or
            record.get("ウイルス濃度")
        )
        if load_str:
            try:
                raw_load = float(str(load_str).replace(",", ""))
                normalized_score = min(1.0, raw_load / 1e8)
            except ValueError:
                pass

        trend_str = record.get("trend") or record.get("変化率")
        if trend_str:
            try:
                velocity = float(str(trend_str).replace(",", "")) / 100
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
