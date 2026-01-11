"""
OpenSky Network Flight Data Adapter

Data source: https://opensky-network.org/
Coverage: Global real-time and historical flight tracking
Frequency: Real-time updates
Cost: FREE (with optional authentication for higher rate limits)

OpenSky Network is a non-profit research network that provides:
- Real-time flight positions
- Flight departures/arrivals at airports
- Historical flight data

Rate limits:
- Anonymous: 400 API credits/day, 10 requests/min
- Authenticated: 4000 API credits/day, 1 request/5 sec

This adapter fetches airport arrival/departure data for import pressure modeling.
"""

import os
import hashlib
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import logging

import httpx

logger = logging.getLogger(__name__)


@dataclass
class FlightArrival:
    """Represents an arriving flight."""
    icao24: str  # Unique aircraft identifier
    callsign: str
    origin_airport: str  # ICAO code
    destination_airport: str  # ICAO code
    first_seen: datetime
    last_seen: datetime
    estimated_arrival: Optional[datetime]


@dataclass
class AirportFlightData:
    """Aggregated flight data for an airport."""
    airport_icao: str
    airport_name: str
    country: str
    latitude: float
    longitude: float
    arrivals_count: int
    departures_count: int
    estimated_passengers: int
    top_origins: List[Dict[str, Any]]
    timestamp: datetime


class OpenSkyAdapter:
    """
    Adapter for OpenSky Network free flight data API.

    Provides real flight tracking data without requiring a paid subscription.
    Complements AviationStack for more comprehensive flight coverage.
    """

    BASE_URL = "https://opensky-network.org/api"

    # Major airports with ICAO codes (OpenSky uses ICAO, not IATA)
    MAJOR_AIRPORTS = {
        # North America
        "KJFK": {"iata": "JFK", "name": "John F. Kennedy", "city": "New York", "country": "US", "lat": 40.6413, "lon": -73.7781},
        "KLAX": {"iata": "LAX", "name": "Los Angeles International", "city": "Los Angeles", "country": "US", "lat": 33.9416, "lon": -118.4085},
        "KORD": {"iata": "ORD", "name": "O'Hare International", "city": "Chicago", "country": "US", "lat": 41.9742, "lon": -87.9073},
        "KATL": {"iata": "ATL", "name": "Hartsfield-Jackson", "city": "Atlanta", "country": "US", "lat": 33.6407, "lon": -84.4277},
        "KDFW": {"iata": "DFW", "name": "Dallas/Fort Worth", "city": "Dallas", "country": "US", "lat": 32.8998, "lon": -97.0403},
        "KMIA": {"iata": "MIA", "name": "Miami International", "city": "Miami", "country": "US", "lat": 25.7959, "lon": -80.2870},
        "KSFO": {"iata": "SFO", "name": "San Francisco International", "city": "San Francisco", "country": "US", "lat": 37.6213, "lon": -122.3790},
        "CYYZ": {"iata": "YYZ", "name": "Toronto Pearson", "city": "Toronto", "country": "CA", "lat": 43.6777, "lon": -79.6248},
        "CYVR": {"iata": "YVR", "name": "Vancouver International", "city": "Vancouver", "country": "CA", "lat": 49.1947, "lon": -123.1792},
        "MMMX": {"iata": "MEX", "name": "Benito Juárez", "city": "Mexico City", "country": "MX", "lat": 19.4361, "lon": -99.0719},

        # Europe
        "EGLL": {"iata": "LHR", "name": "London Heathrow", "city": "London", "country": "GB", "lat": 51.4700, "lon": -0.4543},
        "LFPG": {"iata": "CDG", "name": "Charles de Gaulle", "city": "Paris", "country": "FR", "lat": 49.0097, "lon": 2.5479},
        "EDDF": {"iata": "FRA", "name": "Frankfurt Airport", "city": "Frankfurt", "country": "DE", "lat": 50.0379, "lon": 8.5622},
        "EHAM": {"iata": "AMS", "name": "Amsterdam Schiphol", "city": "Amsterdam", "country": "NL", "lat": 52.3105, "lon": 4.7683},
        "LEMD": {"iata": "MAD", "name": "Madrid-Barajas", "city": "Madrid", "country": "ES", "lat": 40.4983, "lon": -3.5676},
        "LIRF": {"iata": "FCO", "name": "Leonardo da Vinci", "city": "Rome", "country": "IT", "lat": 41.8003, "lon": 12.2389},
        "LTFM": {"iata": "IST", "name": "Istanbul Airport", "city": "Istanbul", "country": "TR", "lat": 41.2753, "lon": 28.7519},

        # Asia-Pacific
        "RJTT": {"iata": "HND", "name": "Tokyo Haneda", "city": "Tokyo", "country": "JP", "lat": 35.5494, "lon": 139.7798},
        "RJAA": {"iata": "NRT", "name": "Narita International", "city": "Tokyo", "country": "JP", "lat": 35.7720, "lon": 140.3929},
        "ZBAA": {"iata": "PEK", "name": "Beijing Capital", "city": "Beijing", "country": "CN", "lat": 40.0799, "lon": 116.6031},
        "ZSPD": {"iata": "PVG", "name": "Shanghai Pudong", "city": "Shanghai", "country": "CN", "lat": 31.1443, "lon": 121.8083},
        "VHHH": {"iata": "HKG", "name": "Hong Kong International", "city": "Hong Kong", "country": "HK", "lat": 22.3080, "lon": 113.9185},
        "WSSS": {"iata": "SIN", "name": "Singapore Changi", "city": "Singapore", "country": "SG", "lat": 1.3644, "lon": 103.9915},
        "RKSI": {"iata": "ICN", "name": "Incheon International", "city": "Seoul", "country": "KR", "lat": 37.4602, "lon": 126.4407},
        "VTBS": {"iata": "BKK", "name": "Suvarnabhumi", "city": "Bangkok", "country": "TH", "lat": 13.6900, "lon": 100.7501},
        "YSSY": {"iata": "SYD", "name": "Sydney Kingsford Smith", "city": "Sydney", "country": "AU", "lat": -33.9399, "lon": 151.1753},
        "VIDP": {"iata": "DEL", "name": "Indira Gandhi International", "city": "Delhi", "country": "IN", "lat": 28.5562, "lon": 77.1000},
        "OMDB": {"iata": "DXB", "name": "Dubai International", "city": "Dubai", "country": "AE", "lat": 25.2532, "lon": 55.3657},

        # South America
        "SBGR": {"iata": "GRU", "name": "São Paulo–Guarulhos", "city": "São Paulo", "country": "BR", "lat": -23.4356, "lon": -46.4731},
        "SAEZ": {"iata": "EZE", "name": "Ministro Pistarini", "city": "Buenos Aires", "country": "AR", "lat": -34.8222, "lon": -58.5358},
        "SCEL": {"iata": "SCL", "name": "Arturo Merino Benítez", "city": "Santiago", "country": "CL", "lat": -33.3930, "lon": -70.7858},
        "SKBO": {"iata": "BOG", "name": "El Dorado International", "city": "Bogotá", "country": "CO", "lat": 4.7016, "lon": -74.1469},

        # Africa/Middle East
        "FAOR": {"iata": "JNB", "name": "O.R. Tambo International", "city": "Johannesburg", "country": "ZA", "lat": -26.1392, "lon": 28.2460},
        "HECA": {"iata": "CAI", "name": "Cairo International", "city": "Cairo", "country": "EG", "lat": 30.1219, "lon": 31.4056},
        "OTHH": {"iata": "DOH", "name": "Hamad International", "city": "Doha", "country": "QA", "lat": 25.2731, "lon": 51.6081},
        "OMAA": {"iata": "AUH", "name": "Abu Dhabi International", "city": "Abu Dhabi", "country": "AE", "lat": 24.4330, "lon": 54.6511},
    }

    # Average passengers per flight (conservative estimate)
    AVG_PASSENGERS_PER_FLIGHT = 150

    def __init__(
        self,
        username: Optional[str] = None,
        password: Optional[str] = None
    ):
        """
        Initialize OpenSky adapter.

        Args:
            username: OpenSky username (optional, for higher rate limits)
            password: OpenSky password (optional)
        """
        self.username = username or os.getenv("OPENSKY_USERNAME")
        self.password = password or os.getenv("OPENSKY_PASSWORD")

        # Configure client with auth if provided
        auth = None
        if self.username and self.password:
            auth = httpx.BasicAuth(self.username, self.password)
            logger.info("Using authenticated OpenSky access")
        else:
            logger.info("Using anonymous OpenSky access (limited rate)")

        self.client = httpx.AsyncClient(
            timeout=60.0,
            auth=auth,
            follow_redirects=True
        )

        self._cache: Dict[str, Tuple[datetime, Any]] = {}
        self._cache_ttl = timedelta(hours=1)

    async def fetch_arrivals(
        self,
        airport_icao: str,
        begin: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[FlightArrival]:
        """
        Fetch arrivals at an airport.

        Args:
            airport_icao: ICAO code of airport (e.g., "KJFK")
            begin: Start of time range (default: 24 hours ago)
            end: End of time range (default: now)

        Returns:
            List of FlightArrival objects
        """
        if end is None:
            end = datetime.utcnow()
        if begin is None:
            begin = end - timedelta(hours=24)

        # OpenSky uses Unix timestamps
        begin_ts = int(begin.timestamp())
        end_ts = int(end.timestamp())

        cache_key = f"arrivals:{airport_icao}:{begin_ts}:{end_ts}"
        if cache_key in self._cache:
            cached_time, cached_data = self._cache[cache_key]
            if datetime.now() - cached_time < self._cache_ttl:
                return cached_data

        try:
            response = await self.client.get(
                f"{self.BASE_URL}/flights/arrival",
                params={
                    "airport": airport_icao,
                    "begin": begin_ts,
                    "end": end_ts,
                }
            )

            if response.status_code == 404:
                logger.debug(f"No arrivals data for {airport_icao}")
                return []

            response.raise_for_status()
            data = response.json()

            arrivals = []
            for flight in data or []:
                arrivals.append(FlightArrival(
                    icao24=flight.get("icao24", ""),
                    callsign=flight.get("callsign", "").strip(),
                    origin_airport=flight.get("estDepartureAirport", ""),
                    destination_airport=flight.get("estArrivalAirport", airport_icao),
                    first_seen=datetime.fromtimestamp(flight.get("firstSeen", 0)),
                    last_seen=datetime.fromtimestamp(flight.get("lastSeen", 0)),
                    estimated_arrival=datetime.fromtimestamp(flight.get("lastSeen", 0)),
                ))

            self._cache[cache_key] = (datetime.now(), arrivals)
            return arrivals

        except httpx.HTTPError as e:
            logger.error(f"OpenSky API error for {airport_icao}: {e}")
            return []

    async def fetch_departures(
        self,
        airport_icao: str,
        begin: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch departures from an airport.

        Args:
            airport_icao: ICAO code of airport
            begin: Start of time range (default: 24 hours ago)
            end: End of time range (default: now)

        Returns:
            List of departure records
        """
        if end is None:
            end = datetime.utcnow()
        if begin is None:
            begin = end - timedelta(hours=24)

        begin_ts = int(begin.timestamp())
        end_ts = int(end.timestamp())

        try:
            response = await self.client.get(
                f"{self.BASE_URL}/flights/departure",
                params={
                    "airport": airport_icao,
                    "begin": begin_ts,
                    "end": end_ts,
                }
            )

            if response.status_code == 404:
                return []

            response.raise_for_status()
            return response.json() or []

        except httpx.HTTPError as e:
            logger.error(f"OpenSky departures error for {airport_icao}: {e}")
            return []

    async def fetch_all_airports(
        self,
        hours_back: int = 24,
        airports: Optional[List[str]] = None,
    ) -> List[AirportFlightData]:
        """
        Fetch flight data for all major airports.

        Args:
            hours_back: How many hours of data to fetch
            airports: List of ICAO codes (default: all major airports)

        Returns:
            List of AirportFlightData objects
        """
        if airports is None:
            airports = list(self.MAJOR_AIRPORTS.keys())

        end = datetime.utcnow()
        begin = end - timedelta(hours=hours_back)

        results = []

        # Process airports with rate limiting to avoid hitting limits
        for icao in airports:
            try:
                airport_info = self.MAJOR_AIRPORTS.get(icao, {})

                # Fetch arrivals
                arrivals = await self.fetch_arrivals(icao, begin, end)

                # Add delay for rate limiting (OpenSky allows 10 req/min anonymous)
                await asyncio.sleep(0.5)

                # Fetch departures
                departures = await self.fetch_departures(icao, begin, end)

                # Aggregate origin data
                origin_counts: Dict[str, int] = {}
                for arr in arrivals:
                    origin = arr.origin_airport
                    if origin:
                        origin_counts[origin] = origin_counts.get(origin, 0) + 1

                top_origins = [
                    {"airport": orig, "count": count}
                    for orig, count in sorted(
                        origin_counts.items(),
                        key=lambda x: x[1],
                        reverse=True
                    )[:10]
                ]

                results.append(AirportFlightData(
                    airport_icao=icao,
                    airport_name=airport_info.get("name", icao),
                    country=airport_info.get("country", ""),
                    latitude=airport_info.get("lat", 0),
                    longitude=airport_info.get("lon", 0),
                    arrivals_count=len(arrivals),
                    departures_count=len(departures),
                    estimated_passengers=len(arrivals) * self.AVG_PASSENGERS_PER_FLIGHT,
                    top_origins=top_origins,
                    timestamp=end,
                ))

                logger.info(f"[OpenSky] {icao}: {len(arrivals)} arrivals, {len(departures)} departures")

                # Rate limiting delay
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.warning(f"Failed to fetch data for {icao}: {e}")
                continue

        return results

    async def fetch(self) -> List[Dict[str, Any]]:
        """
        Main fetch method - returns flight data for all tracked airports.

        Returns:
            List of flight records for database persistence
        """
        logger.info("Fetching from OpenSky Network")

        # Fetch last 24 hours of data from top airports
        # Limit to 15 airports to stay within rate limits
        top_airports = list(self.MAJOR_AIRPORTS.keys())[:15]

        airport_data = await self.fetch_all_airports(
            hours_back=24,
            airports=top_airports
        )

        # Convert to records for persistence
        records = []
        for data in airport_data:
            records.append({
                "source": "opensky",
                "airport_icao": data.airport_icao,
                "airport_name": data.airport_name,
                "country": data.country,
                "latitude": data.latitude,
                "longitude": data.longitude,
                "arrivals": data.arrivals_count,
                "departures": data.departures_count,
                "estimated_passengers": data.estimated_passengers,
                "top_origins": data.top_origins,
                "timestamp": data.timestamp.isoformat(),
            })

        logger.info(f"OpenSky: fetched data for {len(records)} airports")
        return records

    def get_airport_by_iata(self, iata: str) -> Optional[Dict[str, Any]]:
        """Get airport info by IATA code."""
        for icao, info in self.MAJOR_AIRPORTS.items():
            if info.get("iata") == iata:
                return {"icao": icao, **info}
        return None

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


async def test_opensky():
    """Test the OpenSky adapter."""
    print("\nTesting OpenSky Adapter")
    print("=" * 50)

    adapter = OpenSkyAdapter()

    try:
        # Test with just a few airports
        test_airports = ["KJFK", "EGLL", "WSSS"]

        for icao in test_airports:
            print(f"\nFetching arrivals for {icao}...")
            arrivals = await adapter.fetch_arrivals(icao)
            print(f"  Found {len(arrivals)} arrivals in last 24h")

            if arrivals:
                origins = {}
                for arr in arrivals:
                    if arr.origin_airport:
                        origins[arr.origin_airport] = origins.get(arr.origin_airport, 0) + 1

                print("  Top origins:")
                for orig, count in sorted(origins.items(), key=lambda x: x[1], reverse=True)[:5]:
                    print(f"    - {orig}: {count} flights")

            await asyncio.sleep(1)  # Rate limiting

        # Test full fetch
        print("\nRunning full fetch (limited airports)...")
        records = await adapter.fetch()
        print(f"Total records: {len(records)}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await adapter.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_opensky())
