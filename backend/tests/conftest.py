"""
Pytest configuration and fixtures for Viral Weather backend tests.
"""

import asyncio
from datetime import datetime, date
from typing import AsyncGenerator, Generator
import pytest
from unittest.mock import AsyncMock, MagicMock

# Import app and models
import sys
sys.path.insert(0, str(__file__).rsplit('/tests', 1)[0])

# Lazy import for app - only when needed for integration tests
_app = None

def get_app():
    global _app
    if _app is None:
        from app.main import app
        _app = app
    return _app


# Event loop fixture for async tests
@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Sync test client (for integration tests)
@pytest.fixture
def client() -> Generator:
    """Create synchronous test client."""
    from fastapi.testclient import TestClient
    with TestClient(get_app()) as c:
        yield c


# Async test client (for integration tests)
@pytest.fixture
async def async_client() -> AsyncGenerator:
    """Create async test client."""
    from httpx import AsyncClient
    async with AsyncClient(app=get_app(), base_url="http://test") as ac:
        yield ac


# Mock HTTP client for adapter tests
@pytest.fixture
def mock_httpx_client():
    """Create mock httpx async client."""
    mock = AsyncMock()
    mock.get = AsyncMock()
    mock.aclose = AsyncMock()
    return mock


# Sample location data
@pytest.fixture
def sample_location():
    """Sample location data for tests."""
    return {
        "location_id": "loc_us_new_york",
        "name": "New York",
        "country": "United States",
        "iso_code": "US",
        "granularity": "tier_1",
        "coordinates": {"lat": 40.7128, "lon": -74.0060},
        "risk_score": 45.5,
        "last_updated": "2026-01-10T12:00:00Z",
        "variants": ["JN.1", "BA.2.86"],
    }


# Sample surveillance event
@pytest.fixture
def sample_event():
    """Sample surveillance event data."""
    return {
        "event_id": "evt_123456",
        "location_id": "loc_us_new_york",
        "timestamp": datetime(2026, 1, 10, 12, 0, 0),
        "data_source": "CDC_NWSS",
        "signal_type": "wastewater",
        "raw_load": 5.5e7,
        "normalized_score": 0.55,
        "velocity": 0.12,
        "quality_score": 0.9,
    }


# Sample flight arc data
@pytest.fixture
def sample_flight_arc():
    """Sample flight arc data."""
    return {
        "arc_id": "arc_abc123",
        "origin_lat": 40.6413,
        "origin_lon": -73.7781,
        "origin_name": "New York",
        "origin_country": "US",
        "dest_lat": 51.4700,
        "dest_lon": -0.4543,
        "dest_name": "London",
        "dest_country": "GB",
        "pax_estimate": 1500,
        "flight_count": 8,
        "origin_risk": 45.0,
    }


# Sample CDC NWSS response
@pytest.fixture
def sample_cdc_response():
    """Sample CDC NWSS API response."""
    return [
        {
            "wwtp_id": "WWTP_123",
            "reporting_jurisdiction": "New York",
            "state": "NY",
            "county_names": "New York County",
            "county_fips": "36061",
            "population_served": 5000000,
            "date_start": "2026-01-01",
            "date_end": "2026-01-07",
            "ptc_15d": 15.5,
            "percentile": 75,
            "detect_prop_15d": 0.95,
            "wwtp_latitude": 40.7128,
            "wwtp_longitude": -74.0060,
        },
        {
            "wwtp_id": "WWTP_456",
            "reporting_jurisdiction": "California",
            "state": "CA",
            "county_names": "Los Angeles County",
            "county_fips": "06037",
            "population_served": 3000000,
            "date_start": "2026-01-01",
            "date_end": "2026-01-07",
            "ptc_15d": -5.2,
            "percentile": 45,
            "detect_prop_15d": 0.88,
            "wwtp_latitude": 34.0522,
            "wwtp_longitude": -118.2437,
        },
    ]


# Sample UKHSA response
@pytest.fixture
def sample_ukhsa_response():
    """Sample UK UKHSA API response."""
    return [
        {
            "areaType": "region",
            "areaName": "London",
            "date": "2026-01-10",
            "newCasesBySpecimenDateRollingRate": 125.5,
        },
        {
            "areaType": "region",
            "areaName": "South East",
            "date": "2026-01-10",
            "newCasesBySpecimenDateRollingRate": 98.3,
        },
    ]


# Dates for testing
@pytest.fixture
def test_date():
    """Standard test date."""
    return date(2026, 1, 10)


@pytest.fixture
def test_datetime():
    """Standard test datetime."""
    return datetime(2026, 1, 10, 12, 0, 0)


# Risk score test data
@pytest.fixture
def risk_components():
    """Sample risk score components."""
    return {
        "wastewater_load": 55.0,
        "growth_velocity": 12.0,
        "import_pressure": 35.0,
    }


# Historical data fixture
@pytest.fixture
def historical_data():
    """Sample historical data points."""
    return [
        {"date": "2026-01-01", "risk_score": 40.0, "velocity": 0.05},
        {"date": "2026-01-02", "risk_score": 42.0, "velocity": 0.08},
        {"date": "2026-01-03", "risk_score": 45.0, "velocity": 0.10},
        {"date": "2026-01-04", "risk_score": 44.0, "velocity": -0.02},
        {"date": "2026-01-05", "risk_score": 46.0, "velocity": 0.05},
        {"date": "2026-01-06", "risk_score": 48.0, "velocity": 0.06},
        {"date": "2026-01-07", "risk_score": 50.0, "velocity": 0.07},
    ]
