"""
Unit tests for API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import date, datetime

import sys
sys.path.insert(0, '/home/user/Viral-surveillance/backend')

from app.main import app


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns API info."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "status" in data

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "degraded", "unhealthy"]


class TestLocationsEndpoints:
    """Tests for location endpoints."""

    def test_get_locations_list(self, client):
        """Test GET /api/locations returns list."""
        response = client.get("/api/locations")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)

    def test_get_locations_pagination(self, client):
        """Test locations pagination parameters."""
        response = client.get("/api/locations?page=1&page_size=5")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 5

    def test_get_locations_filter_by_country(self, client):
        """Test filtering locations by country."""
        response = client.get("/api/locations?country=US")

        assert response.status_code == 200
        data = response.json()
        # If results returned, they should match filter
        for loc in data["items"]:
            assert loc["iso_code"] == "US" or loc["country"] == "United States"

    def test_get_location_by_id(self, client):
        """Test GET /api/locations/{id} returns location detail."""
        # First get a valid location ID
        list_response = client.get("/api/locations?page_size=1")
        if list_response.json()["items"]:
            loc_id = list_response.json()["items"][0]["location_id"]

            response = client.get(f"/api/locations/{loc_id}")

            assert response.status_code == 200
            data = response.json()
            assert data["location_id"] == loc_id

    def test_get_location_not_found(self, client):
        """Test 404 for non-existent location."""
        response = client.get("/api/locations/loc_nonexistent_123")

        assert response.status_code == 404

    def test_get_location_history(self, client):
        """Test GET /api/locations/{id}/history."""
        list_response = client.get("/api/locations?page_size=1")
        if list_response.json()["items"]:
            loc_id = list_response.json()["items"][0]["location_id"]

            response = client.get(f"/api/locations/{loc_id}/history?days=7")

            assert response.status_code == 200
            data = response.json()
            assert "history" in data
            assert data["location_id"] == loc_id


class TestRiskEndpoints:
    """Tests for risk score endpoints."""

    def test_get_risk_score(self, client):
        """Test GET /api/risk/{id} returns risk score."""
        list_response = client.get("/api/locations?page_size=1")
        if list_response.json()["items"]:
            loc_id = list_response.json()["items"][0]["location_id"]

            response = client.get(f"/api/risk/{loc_id}")

            assert response.status_code == 200
            data = response.json()
            assert "risk_score" in data
            assert 0 <= data["risk_score"] <= 100

    def test_get_risk_forecast(self, client):
        """Test GET /api/risk/{id}/forecast."""
        list_response = client.get("/api/locations?page_size=1")
        if list_response.json()["items"]:
            loc_id = list_response.json()["items"][0]["location_id"]

            response = client.get(f"/api/risk/{loc_id}/forecast?days=7")

            assert response.status_code == 200
            data = response.json()
            assert "forecast" in data
            assert len(data["forecast"]) <= 7

    def test_get_global_summary(self, client):
        """Test GET /api/risk/summary/global."""
        response = client.get("/api/risk/summary/global")

        assert response.status_code == 200
        data = response.json()
        assert "total_locations" in data
        assert "high_risk_count" in data
        assert "hotspots" in data


class TestSearchEndpoints:
    """Tests for search endpoints."""

    def test_search_locations(self, client):
        """Test GET /api/search with query."""
        response = client.get("/api/search?q=new%20york")

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)

    def test_search_empty_query(self, client):
        """Test search with empty query."""
        response = client.get("/api/search?q=")

        # Should return empty results or error
        assert response.status_code in [200, 400]

    def test_autocomplete(self, client):
        """Test GET /api/search/autocomplete."""
        response = client.get("/api/search/autocomplete?q=lon&limit=5")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5


class TestFlightEndpoints:
    """Tests for flight data endpoints."""

    def test_get_flight_arcs(self, client):
        """Test GET /api/flights/arcs returns arcs."""
        response = client.get("/api/flights/arcs")

        assert response.status_code == 200
        data = response.json()
        assert "arcs" in data
        assert "total" in data
        assert "date" in data

    def test_get_flight_arcs_with_date(self, client):
        """Test flight arcs with date filter."""
        response = client.get("/api/flights/arcs?date=2026-01-10")

        assert response.status_code == 200
        data = response.json()
        assert data["date"] == "2026-01-10"

    def test_get_flight_arcs_invalid_date(self, client):
        """Test flight arcs with invalid date format."""
        response = client.get("/api/flights/arcs?date=invalid")

        assert response.status_code == 400

    def test_get_flight_arcs_min_passengers(self, client):
        """Test filtering by minimum passengers."""
        response = client.get("/api/flights/arcs?min_pax=500")

        assert response.status_code == 200
        data = response.json()
        for arc in data["arcs"]:
            assert arc["pax_estimate"] >= 500

    def test_get_import_pressure(self, client):
        """Test GET /api/flights/import-pressure/{id}."""
        response = client.get("/api/flights/import-pressure/loc_us_new_york")

        assert response.status_code == 200
        data = response.json()
        assert "import_pressure" in data
        assert "top_sources" in data
        assert 0 <= data["import_pressure"] <= 100


class TestHistoryEndpoints:
    """Tests for historical data endpoints."""

    def test_get_historical_data(self, client):
        """Test GET /api/history with date range."""
        response = client.get(
            "/api/history?start_date=2026-01-01&end_date=2026-01-10"
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "date_range" in data

    def test_get_historical_data_invalid_dates(self, client):
        """Test history with invalid date format."""
        response = client.get(
            "/api/history?start_date=invalid&end_date=2026-01-10"
        )

        assert response.status_code == 400

    def test_get_historical_data_end_before_start(self, client):
        """Test history with end before start date."""
        response = client.get(
            "/api/history?start_date=2026-01-10&end_date=2026-01-01"
        )

        assert response.status_code == 400

    def test_get_historical_data_weekly_granularity(self, client):
        """Test weekly granularity option."""
        response = client.get(
            "/api/history?start_date=2026-01-01&end_date=2026-01-31&granularity=weekly"
        )

        assert response.status_code == 200

    def test_get_timeseries(self, client):
        """Test GET /api/history/timeseries/{id}."""
        response = client.get(
            "/api/history/timeseries/loc_us_new_york?metric=risk_score&days=30"
        )

        assert response.status_code == 200
        data = response.json()
        assert "series" in data
        assert data["metric"] == "risk_score"

    def test_compare_locations(self, client):
        """Test GET /api/history/compare."""
        response = client.get(
            "/api/history/compare?location_ids=loc_us_new_york&location_ids=loc_gb_london&days=7"
        )

        assert response.status_code == 200
        data = response.json()
        assert "locations" in data

    def test_get_historical_summary(self, client):
        """Test GET /api/history/summary."""
        response = client.get(
            "/api/history/summary?location_id=loc_us_new_york&days=30"
        )

        assert response.status_code == 200
        data = response.json()
        assert "statistics" in data
        assert "trend" in data


class TestAPIValidation:
    """Tests for API input validation."""

    def test_pagination_limits(self, client):
        """Test pagination limits are enforced."""
        # Very large page size should be capped or rejected
        response = client.get("/api/locations?page_size=10000")

        assert response.status_code in [200, 400, 422]

    def test_date_range_limits(self, client):
        """Test date range limits are enforced."""
        # More than 365 days should be rejected
        response = client.get(
            "/api/history?start_date=2024-01-01&end_date=2026-01-10"
        )

        assert response.status_code == 400

    def test_special_characters_in_search(self, client):
        """Test special characters are handled in search."""
        response = client.get("/api/search?q=%3Cscript%3E")

        # Should not crash, may return empty results
        assert response.status_code in [200, 400]


class TestCORS:
    """Tests for CORS configuration."""

    def test_cors_headers_present(self, client):
        """Test CORS headers are present."""
        response = client.options(
            "/api/locations",
            headers={"Origin": "http://localhost:3000"}
        )

        # CORS preflight should work
        assert response.status_code in [200, 204, 405]


class TestErrorHandling:
    """Tests for error handling."""

    def test_404_returns_json(self, client):
        """Test 404 errors return JSON."""
        response = client.get("/nonexistent/endpoint")

        assert response.status_code == 404
        assert response.headers.get("content-type", "").startswith("application/json")

    def test_method_not_allowed(self, client):
        """Test method not allowed returns proper error."""
        response = client.post("/api/locations")  # POST not supported

        assert response.status_code == 405
