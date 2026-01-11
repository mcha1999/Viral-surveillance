"""
Nextstrain Genomic Data Adapter

Data source: https://nextstrain.org/
Endpoints:
- Clade frequencies: https://data.nextstrain.org/files/workflows/forecasts-ncov/
- Metadata: https://data.nextstrain.org/files/ncov/open/

Coverage: Global genomic sequences
Frequency: Daily builds
Cost: FREE

This adapter fetches variant/clade prevalence data for tracking
emerging variants and their geographic spread.
"""

import os
import json
import gzip
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from io import BytesIO

import httpx

from .base import (
    BaseAdapter,
    LocationData,
    SurveillanceEvent,
    SignalType,
    GranularityTier,
)


class NextstrainAdapter(BaseAdapter):
    """
    Adapter for Nextstrain genomic surveillance data.

    Fetches variant/clade frequencies and geographic distribution
    to track emerging variants globally.
    """

    source_id = "NEXTSTRAIN"
    source_name = "Nextstrain"
    signal_type = SignalType.GENOMIC

    # Nextstrain data endpoints
    CLADES_FORECAST_URL = "https://data.nextstrain.org/files/workflows/forecasts-ncov/gisaid/nextstrain_clades/global/latest_results.json"
    PANGO_FORECAST_URL = "https://data.nextstrain.org/files/workflows/forecasts-ncov/gisaid/pango_lineages/global/latest_results.json"

    # Country-level clade data
    COUNTRY_CLADES_BASE = "https://data.nextstrain.org/files/workflows/forecasts-ncov/gisaid/nextstrain_clades"

    # Key countries to track (matching our wastewater coverage)
    TRACKED_COUNTRIES = {
        "USA": {"iso": "US", "lat": 39.8283, "lon": -98.5795, "pop": 331000000},
        "United Kingdom": {"iso": "GB", "lat": 55.3781, "lon": -3.4360, "pop": 67000000},
        "Germany": {"iso": "DE", "lat": 51.1657, "lon": 10.4515, "pop": 83000000},
        "France": {"iso": "FR", "lat": 46.2276, "lon": 2.2137, "pop": 67000000},
        "Netherlands": {"iso": "NL", "lat": 52.1326, "lon": 5.2913, "pop": 17000000},
        "Japan": {"iso": "JP", "lat": 36.2048, "lon": 138.2529, "pop": 126000000},
        "Australia": {"iso": "AU", "lat": -25.2744, "lon": 133.7751, "pop": 26000000},
        "Canada": {"iso": "CA", "lat": 56.1304, "lon": -106.3468, "pop": 38000000},
        "Spain": {"iso": "ES", "lat": 40.4637, "lon": -3.7492, "pop": 47000000},
        "Italy": {"iso": "IT", "lat": 41.8719, "lon": 12.5674, "pop": 60000000},
        "Brazil": {"iso": "BR", "lat": -14.2350, "lon": -51.9253, "pop": 214000000},
        "India": {"iso": "IN", "lat": 20.5937, "lon": 78.9629, "pop": 1400000000},
        "South Africa": {"iso": "ZA", "lat": -30.5595, "lon": 22.9375, "pop": 60000000},
        "Singapore": {"iso": "SG", "lat": 1.3521, "lon": 103.8198, "pop": 5900000},
        "South Korea": {"iso": "KR", "lat": 35.9078, "lon": 127.7669, "pop": 52000000},
        "Denmark": {"iso": "DK", "lat": 56.2639, "lon": 9.5018, "pop": 5900000},
        "Belgium": {"iso": "BE", "lat": 50.5039, "lon": 4.4699, "pop": 11600000},
        "Switzerland": {"iso": "CH", "lat": 46.8182, "lon": 8.2275, "pop": 8700000},
        "Austria": {"iso": "AT", "lat": 47.5162, "lon": 14.5501, "pop": 9000000},
    }

    # Variant classifications of concern
    VARIANTS_OF_INTEREST = [
        "JN.1", "JN.1.1", "KP.2", "KP.3", "LB.1",
        "BA.2.86", "BA.2.87", "XBB.1.5", "EG.5", "HV.1",
        "FL.1.5.1", "HK.3", "JD.1.1", "XBB.1.16",
    ]

    def __init__(self):
        super().__init__()
        self.client = httpx.AsyncClient(timeout=120.0, follow_redirects=True)

    async def fetch(self) -> List[Dict[str, Any]]:
        """Fetch genomic data from Nextstrain."""
        self.logger.info("Fetching from Nextstrain")
        all_records = []

        # Fetch global clade forecasts
        try:
            global_data = await self._fetch_global_clades()
            all_records.extend(global_data)
            self.logger.info(f"Fetched {len(global_data)} global clade records")
        except Exception as e:
            self.logger.error(f"Failed to fetch global clades: {e}")

        # Fetch country-specific data
        for country, info in self.TRACKED_COUNTRIES.items():
            try:
                country_data = await self._fetch_country_clades(country, info)
                all_records.extend(country_data)
            except Exception as e:
                self.logger.warning(f"Failed to fetch clades for {country}: {e}")
                continue

        self.logger.info(f"Total Nextstrain records: {len(all_records)}")
        return all_records

    async def _fetch_global_clades(self) -> List[Dict[str, Any]]:
        """Fetch global clade frequency data."""
        try:
            response = await self.client.get(self.CLADES_FORECAST_URL)
            response.raise_for_status()
            data = response.json()

            records = []

            # Parse the forecast data
            if "estimates" in data:
                for location, estimates in data["estimates"].items():
                    for clade, values in estimates.items():
                        if isinstance(values, dict) and "median" in values:
                            records.append({
                                "source": "nextstrain_global",
                                "location": location,
                                "clade": clade,
                                "frequency": values.get("median", 0),
                                "frequency_low": values.get("lower", 0),
                                "frequency_high": values.get("upper", 0),
                                "date": data.get("generated_at", datetime.utcnow().isoformat()),
                                "data_type": "clade_frequency",
                            })

            # Parse variant list
            if "variants" in data:
                for variant_info in data["variants"]:
                    if isinstance(variant_info, dict):
                        records.append({
                            "source": "nextstrain_global",
                            "clade": variant_info.get("clade", ""),
                            "pango": variant_info.get("pango", ""),
                            "who_name": variant_info.get("who_name", ""),
                            "date": data.get("generated_at", datetime.utcnow().isoformat()),
                            "data_type": "variant_definition",
                        })

            return records

        except httpx.HTTPError as e:
            self.logger.error(f"HTTP error fetching global clades: {e}")
            return []

    async def _fetch_country_clades(
        self,
        country: str,
        info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Fetch clade frequencies for a specific country."""
        # Construct country-specific URL
        country_slug = country.lower().replace(" ", "-")
        url = f"{self.COUNTRY_CLADES_BASE}/{country_slug}/latest_results.json"

        try:
            response = await self.client.get(url)

            if response.status_code == 404:
                # Country data not available, use global data
                return []

            response.raise_for_status()
            data = response.json()

            records = []

            # Parse estimates
            if "estimates" in data:
                for clade, values in data["estimates"].items():
                    if isinstance(values, dict) and "median" in values:
                        records.append({
                            "source": "nextstrain_country",
                            "country": country,
                            "iso_code": info["iso"],
                            "clade": clade,
                            "frequency": values.get("median", 0),
                            "frequency_low": values.get("lower", 0),
                            "frequency_high": values.get("upper", 0),
                            "date": data.get("generated_at", datetime.utcnow().isoformat()),
                            "latitude": info["lat"],
                            "longitude": info["lon"],
                            "data_type": "clade_frequency",
                        })

            return records

        except httpx.HTTPError as e:
            self.logger.debug(f"Country {country} clade data not available: {e}")
            return []

    def normalize(
        self,
        raw_data: List[Dict[str, Any]]
    ) -> Tuple[List[LocationData], List[SurveillanceEvent]]:
        """Normalize Nextstrain data to standard schema."""
        locations_map: Dict[str, LocationData] = {}
        events: List[SurveillanceEvent] = []

        for record in raw_data:
            try:
                if record.get("data_type") == "clade_frequency":
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
        """Extract location from Nextstrain record."""
        country = record.get("country") or record.get("location")
        if not country:
            return None

        # Look up country info
        country_info = self.TRACKED_COUNTRIES.get(country)
        if not country_info:
            # Try to match by ISO code
            iso = record.get("iso_code", "")
            for c, info in self.TRACKED_COUNTRIES.items():
                if info["iso"] == iso:
                    country = c
                    country_info = info
                    break

        if not country_info:
            return None

        location_id = f"loc_{country_info['iso'].lower()}_national"

        return LocationData(
            location_id=location_id,
            name=country,
            admin1=country,
            country=country,
            iso_code=country_info["iso"],
            granularity=GranularityTier.TIER_3,  # National level
            latitude=country_info["lat"],
            longitude=country_info["lon"],
            catchment_population=country_info["pop"],
        )

    def _extract_event(
        self,
        record: Dict[str, Any],
        location_id: str
    ) -> Optional[SurveillanceEvent]:
        """Extract surveillance event from Nextstrain record."""
        date_str = record.get("date")
        if not date_str:
            return None

        try:
            if "T" in date_str:
                timestamp = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            else:
                timestamp = datetime.strptime(date_str, "%Y-%m-%d")
        except (ValueError, TypeError):
            timestamp = datetime.utcnow()

        clade = record.get("clade", "")
        frequency = record.get("frequency", 0)

        # Create event for this clade observation
        event_id = self.generate_event_id(
            location_id,
            timestamp,
            f"{self.source_id}_{clade}"
        )

        # Determine if this is a variant of interest
        is_voi = any(voi in clade for voi in self.VARIANTS_OF_INTEREST)

        return SurveillanceEvent(
            event_id=event_id,
            location_id=location_id,
            timestamp=timestamp,
            data_source=self.source_id,
            signal_type=self.signal_type,
            normalized_score=frequency,  # Frequency as 0-1 score
            velocity=None,  # Would need time series to calculate
            quality_score=0.9,  # Nextstrain is high quality
            raw_data={
                "clade": clade,
                "frequency": frequency,
                "frequency_low": record.get("frequency_low"),
                "frequency_high": record.get("frequency_high"),
                "is_variant_of_interest": is_voi,
            },
        )

    async def get_dominant_variants(
        self,
        country: Optional[str] = None,
        top_n: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get the currently dominant variants.

        Returns top N variants by frequency, optionally filtered by country.
        """
        records = await self.fetch()

        # Filter to clade frequencies
        clade_records = [
            r for r in records
            if r.get("data_type") == "clade_frequency"
        ]

        if country:
            clade_records = [
                r for r in clade_records
                if r.get("country") == country or r.get("location") == country
            ]

        # Aggregate by clade
        clade_freq: Dict[str, float] = {}
        for r in clade_records:
            clade = r.get("clade", "")
            freq = r.get("frequency", 0)
            if clade in clade_freq:
                clade_freq[clade] = max(clade_freq[clade], freq)
            else:
                clade_freq[clade] = freq

        # Sort by frequency
        sorted_clades = sorted(
            clade_freq.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n]

        return [
            {
                "clade": clade,
                "frequency": freq,
                "is_variant_of_interest": any(voi in clade for voi in self.VARIANTS_OF_INTEREST),
            }
            for clade, freq in sorted_clades
        ]

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# Convenience function for testing
async def test_nextstrain():
    """Test the Nextstrain adapter."""
    adapter = NextstrainAdapter()
    try:
        result = await adapter.run()
        print(f"Success: {result.success}")
        print(f"Locations: {len(result.locations)}")
        print(f"Events: {len(result.events)}")
        print(f"Duration: {result.duration_seconds:.2f}s")

        if result.locations:
            print("\nCountries with data:")
            for loc in result.locations[:10]:
                print(f"  - {loc.name} ({loc.iso_code})")

        # Get dominant variants
        print("\nDominant variants globally:")
        variants = await adapter.get_dominant_variants(top_n=10)
        for v in variants:
            voi = "⚠️" if v["is_variant_of_interest"] else ""
            print(f"  - {v['clade']}: {v['frequency']*100:.1f}% {voi}")

    finally:
        await adapter.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_nextstrain())
