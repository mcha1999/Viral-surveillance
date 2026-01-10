"""
AviationStack Flight Data Adapter

Data source: https://aviationstack.com/
Coverage: Global flight routes
Frequency: Real-time and historical
Cost: $49/month for 10,000 API calls

This adapter fetches flight route data to calculate import pressure
for viral risk assessment.
"""

import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import hashlib
import asyncio

import httpx


@dataclass
class FlightRoute:
    """Represents a flight route between two airports."""
    route_id: str
    departure_iata: str
    departure_city: str
    departure_country: str
    departure_lat: float
    departure_lon: float
    arrival_iata: str
    arrival_city: str
    arrival_country: str
    arrival_lat: float
    arrival_lon: float
    airline_iata: str
    airline_name: str
    flight_count: int
    estimated_passengers: int
    timestamp: datetime


@dataclass
class VectorArc:
    """Represents a travel vector between locations for visualization."""
    arc_id: str
    origin_location_id: str
    destination_location_id: str
    origin_lat: float
    origin_lon: float
    destination_lat: float
    destination_lon: float
    passenger_volume: int
    flight_count: int
    timestamp: datetime


# Aircraft capacity estimates (average seats)
AIRCRAFT_CAPACITY = {
    # Narrow-body
    "A320": 150, "A321": 185, "A319": 124, "A318": 107,
    "B737": 160, "B738": 175, "B739": 189, "B73H": 160,
    "B752": 186, "B753": 218,
    "E190": 100, "E195": 120, "E170": 72, "E175": 78,
    "CRJ9": 76, "CRJ7": 70, "CRJ2": 50,
    "AT76": 70, "AT72": 68, "DH8D": 78,
    # Wide-body
    "B777": 350, "B772": 305, "B773": 368, "B77W": 365,
    "B787": 290, "B788": 248, "B789": 296, "B78X": 318,
    "A330": 277, "A332": 247, "A333": 277, "A339": 287,
    "A350": 300, "A359": 300, "A35K": 350,
    "A380": 500,
    "B744": 416, "B748": 410,
    "B767": 218, "B763": 218, "B764": 245,
}

# Default capacity for unknown aircraft
DEFAULT_CAPACITY = 150

# Average load factor
AVG_LOAD_FACTOR = 0.82


class AviationStackAdapter:
    """
    Adapter for AviationStack flight data API.

    Fetches flight routes and calculates passenger volumes
    for import pressure modeling.
    """

    BASE_URL = "https://api.aviationstack.com/v1"

    # Major airport hubs by region (for route prioritization)
    MAJOR_HUBS = {
        # North America
        "JFK": {"city": "New York", "country": "US", "lat": 40.6413, "lon": -73.7781},
        "LAX": {"city": "Los Angeles", "country": "US", "lat": 33.9416, "lon": -118.4085},
        "ORD": {"city": "Chicago", "country": "US", "lat": 41.9742, "lon": -87.9073},
        "ATL": {"city": "Atlanta", "country": "US", "lat": 33.6407, "lon": -84.4277},
        "DFW": {"city": "Dallas", "country": "US", "lat": 32.8998, "lon": -97.0403},
        "MIA": {"city": "Miami", "country": "US", "lat": 25.7959, "lon": -80.2870},
        "SFO": {"city": "San Francisco", "country": "US", "lat": 37.6213, "lon": -122.3790},
        "YYZ": {"city": "Toronto", "country": "CA", "lat": 43.6777, "lon": -79.6248},
        "YVR": {"city": "Vancouver", "country": "CA", "lat": 49.1947, "lon": -123.1792},
        "MEX": {"city": "Mexico City", "country": "MX", "lat": 19.4361, "lon": -99.0719},

        # Europe
        "LHR": {"city": "London", "country": "GB", "lat": 51.4700, "lon": -0.4543},
        "CDG": {"city": "Paris", "country": "FR", "lat": 49.0097, "lon": 2.5479},
        "FRA": {"city": "Frankfurt", "country": "DE", "lat": 50.0379, "lon": 8.5622},
        "AMS": {"city": "Amsterdam", "country": "NL", "lat": 52.3105, "lon": 4.7683},
        "MAD": {"city": "Madrid", "country": "ES", "lat": 40.4983, "lon": -3.5676},
        "FCO": {"city": "Rome", "country": "IT", "lat": 41.8003, "lon": 12.2389},
        "IST": {"city": "Istanbul", "country": "TR", "lat": 41.2753, "lon": 28.7519},

        # Asia-Pacific
        "HND": {"city": "Tokyo", "country": "JP", "lat": 35.5494, "lon": 139.7798},
        "NRT": {"city": "Tokyo Narita", "country": "JP", "lat": 35.7720, "lon": 140.3929},
        "PEK": {"city": "Beijing", "country": "CN", "lat": 40.0799, "lon": 116.6031},
        "PVG": {"city": "Shanghai", "country": "CN", "lat": 31.1443, "lon": 121.8083},
        "HKG": {"city": "Hong Kong", "country": "HK", "lat": 22.3080, "lon": 113.9185},
        "SIN": {"city": "Singapore", "country": "SG", "lat": 1.3644, "lon": 103.9915},
        "ICN": {"city": "Seoul", "country": "KR", "lat": 37.4602, "lon": 126.4407},
        "BKK": {"city": "Bangkok", "country": "TH", "lat": 13.6900, "lon": 100.7501},
        "SYD": {"city": "Sydney", "country": "AU", "lat": -33.9399, "lon": 151.1753},
        "DEL": {"city": "Delhi", "country": "IN", "lat": 28.5562, "lon": 77.1000},
        "DXB": {"city": "Dubai", "country": "AE", "lat": 25.2532, "lon": 55.3657},

        # South America
        "GRU": {"city": "São Paulo", "country": "BR", "lat": -23.4356, "lon": -46.4731},
        "EZE": {"city": "Buenos Aires", "country": "AR", "lat": -34.8222, "lon": -58.5358},
        "SCL": {"city": "Santiago", "country": "CL", "lat": -33.3930, "lon": -70.7858},
        "BOG": {"city": "Bogotá", "country": "CO", "lat": 4.7016, "lon": -74.1469},

        # Africa/Middle East
        "JNB": {"city": "Johannesburg", "country": "ZA", "lat": -26.1392, "lon": 28.2460},
        "CAI": {"city": "Cairo", "country": "EG", "lat": 30.1219, "lon": 31.4056},
        "DOH": {"city": "Doha", "country": "QA", "lat": 25.2731, "lon": 51.6081},
        "AUH": {"city": "Abu Dhabi", "country": "AE", "lat": 24.4330, "lon": 54.6511},
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("AVIATIONSTACK_API_KEY")
        self.client = httpx.AsyncClient(timeout=30.0)
        self._cache: Dict[str, Tuple[datetime, Any]] = {}
        self._cache_ttl = timedelta(hours=6)  # Cache routes for 6 hours

    async def fetch_flights(
        self,
        departure_iata: Optional[str] = None,
        arrival_iata: Optional[str] = None,
        flight_date: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Fetch flights from AviationStack API.

        Args:
            departure_iata: Filter by departure airport
            arrival_iata: Filter by arrival airport
            flight_date: Date in YYYY-MM-DD format
            limit: Maximum results to return

        Returns:
            List of flight records
        """
        if not self.api_key:
            # Return synthetic data if no API key
            return self._generate_synthetic_flights(departure_iata, arrival_iata)

        cache_key = f"{departure_iata}:{arrival_iata}:{flight_date}"
        if cache_key in self._cache:
            cached_time, cached_data = self._cache[cache_key]
            if datetime.now() - cached_time < self._cache_ttl:
                return cached_data

        params = {
            "access_key": self.api_key,
            "limit": limit,
        }

        if departure_iata:
            params["dep_iata"] = departure_iata
        if arrival_iata:
            params["arr_iata"] = arrival_iata
        if flight_date:
            params["flight_date"] = flight_date

        try:
            response = await self.client.get(
                f"{self.BASE_URL}/flights",
                params=params
            )
            response.raise_for_status()

            data = response.json()
            flights = data.get("data", [])

            # Cache the result
            self._cache[cache_key] = (datetime.now(), flights)

            return flights

        except httpx.HTTPError as e:
            print(f"AviationStack API error: {e}")
            return []

    async def fetch_top_routes(
        self,
        date: Optional[datetime] = None,
        hub_airports: Optional[List[str]] = None,
    ) -> List[FlightRoute]:
        """
        Fetch top flight routes between major hubs.

        Optimized for API budget - queries ~50 hub pairs daily.

        Args:
            date: Date to query (defaults to today)
            hub_airports: List of airport codes to query

        Returns:
            List of FlightRoute objects
        """
        if date is None:
            date = datetime.now()

        if hub_airports is None:
            hub_airports = list(self.MAJOR_HUBS.keys())[:20]  # Top 20 hubs

        routes: List[FlightRoute] = []
        flight_date = date.strftime("%Y-%m-%d")

        # Query routes from each hub (budget-conscious approach)
        for dep_iata in hub_airports[:10]:  # Limit to 10 departure hubs
            try:
                flights = await self.fetch_flights(
                    departure_iata=dep_iata,
                    flight_date=flight_date,
                    limit=100,
                )

                # Aggregate flights by route
                route_flights: Dict[str, List[Dict]] = {}
                for flight in flights:
                    arr_iata = flight.get("arrival", {}).get("iata")
                    if arr_iata:
                        key = f"{dep_iata}-{arr_iata}"
                        if key not in route_flights:
                            route_flights[key] = []
                        route_flights[key].append(flight)

                # Create FlightRoute objects
                for route_key, flight_list in route_flights.items():
                    route = self._create_route(dep_iata, flight_list, date)
                    if route:
                        routes.append(route)

                # Rate limiting - avoid hitting API too fast
                await asyncio.sleep(0.5)

            except Exception as e:
                print(f"Error fetching routes from {dep_iata}: {e}")
                continue

        return routes

    def _create_route(
        self,
        dep_iata: str,
        flights: List[Dict],
        date: datetime
    ) -> Optional[FlightRoute]:
        """Create a FlightRoute from a list of flights on the same route."""
        if not flights:
            return None

        first_flight = flights[0]
        departure = first_flight.get("departure", {})
        arrival = first_flight.get("arrival", {})

        arr_iata = arrival.get("iata")
        if not arr_iata:
            return None

        # Get coordinates
        dep_info = self.MAJOR_HUBS.get(dep_iata, {})
        arr_info = self.MAJOR_HUBS.get(arr_iata, {})

        dep_lat = dep_info.get("lat", departure.get("lat", 0))
        dep_lon = dep_info.get("lon", departure.get("lon", 0))
        arr_lat = arr_info.get("lat", arrival.get("lat", 0))
        arr_lon = arr_info.get("lon", arrival.get("lon", 0))

        # Estimate passengers
        total_passengers = 0
        for flight in flights:
            aircraft = flight.get("aircraft", {}).get("iata", "")
            capacity = AIRCRAFT_CAPACITY.get(aircraft, DEFAULT_CAPACITY)
            total_passengers += int(capacity * AVG_LOAD_FACTOR)

        route_id = hashlib.md5(
            f"{dep_iata}-{arr_iata}-{date.strftime('%Y%m%d')}".encode()
        ).hexdigest()[:12]

        return FlightRoute(
            route_id=f"route_{route_id}",
            departure_iata=dep_iata,
            departure_city=dep_info.get("city", departure.get("airport", "")),
            departure_country=dep_info.get("country", ""),
            departure_lat=dep_lat,
            departure_lon=dep_lon,
            arrival_iata=arr_iata,
            arrival_city=arr_info.get("city", arrival.get("airport", "")),
            arrival_country=arr_info.get("country", ""),
            arrival_lat=arr_lat,
            arrival_lon=arr_lon,
            airline_iata=first_flight.get("airline", {}).get("iata", ""),
            airline_name=first_flight.get("airline", {}).get("name", ""),
            flight_count=len(flights),
            estimated_passengers=total_passengers,
            timestamp=date,
        )

    def routes_to_vector_arcs(
        self,
        routes: List[FlightRoute],
        location_mapping: Dict[str, str],
    ) -> List[VectorArc]:
        """
        Convert flight routes to vector arcs for visualization.

        Args:
            routes: List of FlightRoute objects
            location_mapping: Mapping of airport codes to location_ids

        Returns:
            List of VectorArc objects
        """
        arcs = []

        for route in routes:
            # Map airport to location
            origin_loc = location_mapping.get(
                route.departure_iata,
                f"loc_{route.departure_country.lower()}_{route.departure_city.lower().replace(' ', '_')}"
            )
            dest_loc = location_mapping.get(
                route.arrival_iata,
                f"loc_{route.arrival_country.lower()}_{route.arrival_city.lower().replace(' ', '_')}"
            )

            arc_id = hashlib.md5(
                f"{origin_loc}-{dest_loc}-{route.timestamp.strftime('%Y%m%d')}".encode()
            ).hexdigest()[:12]

            arcs.append(VectorArc(
                arc_id=f"arc_{arc_id}",
                origin_location_id=origin_loc,
                destination_location_id=dest_loc,
                origin_lat=route.departure_lat,
                origin_lon=route.departure_lon,
                destination_lat=route.arrival_lat,
                destination_lon=route.arrival_lon,
                passenger_volume=route.estimated_passengers,
                flight_count=route.flight_count,
                timestamp=route.timestamp,
            ))

        return arcs

    def _generate_synthetic_flights(
        self,
        departure_iata: Optional[str] = None,
        arrival_iata: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Generate synthetic flight data for demo purposes."""
        import random

        flights = []
        hubs = list(self.MAJOR_HUBS.items())

        if departure_iata:
            dep_hubs = [(departure_iata, self.MAJOR_HUBS.get(departure_iata, {}))]
        else:
            dep_hubs = random.sample(hubs, min(5, len(hubs)))

        for dep_code, dep_info in dep_hubs:
            # Generate 5-15 flights per departure hub
            num_flights = random.randint(5, 15)
            arr_hubs = random.sample(hubs, min(num_flights, len(hubs)))

            for arr_code, arr_info in arr_hubs:
                if arr_code == dep_code:
                    continue

                aircraft_types = list(AIRCRAFT_CAPACITY.keys())
                aircraft = random.choice(aircraft_types)

                flights.append({
                    "departure": {
                        "iata": dep_code,
                        "airport": dep_info.get("city", ""),
                        "lat": dep_info.get("lat", 0),
                        "lon": dep_info.get("lon", 0),
                    },
                    "arrival": {
                        "iata": arr_code,
                        "airport": arr_info.get("city", ""),
                        "lat": arr_info.get("lat", 0),
                        "lon": arr_info.get("lon", 0),
                    },
                    "airline": {
                        "iata": random.choice(["AA", "UA", "DL", "BA", "LH", "AF", "NH", "SQ"]),
                        "name": "Airline",
                    },
                    "aircraft": {
                        "iata": aircraft,
                    },
                    "flight_status": "scheduled",
                })

        return flights

    def estimate_passengers(self, aircraft_code: str, flights: int = 1) -> int:
        """
        Estimate passenger count based on aircraft type.

        Args:
            aircraft_code: IATA aircraft code
            flights: Number of flights

        Returns:
            Estimated total passengers
        """
        capacity = AIRCRAFT_CAPACITY.get(aircraft_code, DEFAULT_CAPACITY)
        return int(capacity * AVG_LOAD_FACTOR * flights)

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


async def calculate_import_pressure(
    adapter: AviationStackAdapter,
    target_location: str,
    target_airport: str,
    date: datetime,
    risk_scores: Dict[str, float],
) -> float:
    """
    Calculate import pressure for a location based on incoming flights.

    Import pressure = Σ (passengers_from_origin × origin_risk_score)

    Args:
        adapter: AviationStack adapter instance
        target_location: Target location ID
        target_airport: Target airport IATA code
        date: Date to calculate for
        risk_scores: Dict mapping location_id to risk score (0-1)

    Returns:
        Import pressure score (0-1)
    """
    flights = await adapter.fetch_flights(
        arrival_iata=target_airport,
        flight_date=date.strftime("%Y-%m-%d"),
    )

    if not flights:
        return 0.0

    total_pressure = 0.0
    total_passengers = 0

    for flight in flights:
        dep_iata = flight.get("departure", {}).get("iata")
        if not dep_iata:
            continue

        # Get origin risk score
        dep_info = adapter.MAJOR_HUBS.get(dep_iata, {})
        origin_country = dep_info.get("country", "").lower()
        origin_city = dep_info.get("city", "").lower().replace(" ", "_")
        origin_loc = f"loc_{origin_country}_{origin_city}"

        origin_risk = risk_scores.get(origin_loc, 0.3)  # Default moderate risk

        # Estimate passengers
        aircraft = flight.get("aircraft", {}).get("iata", "")
        passengers = adapter.estimate_passengers(aircraft)

        total_pressure += passengers * origin_risk
        total_passengers += passengers

    if total_passengers == 0:
        return 0.0

    # Normalize to 0-1 scale
    avg_pressure = total_pressure / total_passengers
    return min(1.0, avg_pressure)
