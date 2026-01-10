"""
Unit tests for Risk Score Calculation Engine.
"""

import pytest
from datetime import datetime, timedelta

import sys
sys.path.insert(0, '/home/user/Viral-surveillance/backend')

from app.services.risk_engine import (
    RiskEngine,
    RiskCalculation,
    RiskComponents,
)


@pytest.fixture
def risk_engine():
    """Create risk engine instance."""
    return RiskEngine()


@pytest.fixture
def sample_wastewater_data():
    """Sample wastewater data for 7 days."""
    base_date = datetime.utcnow()
    return [
        {
            "timestamp": base_date - timedelta(days=i),
            "raw_load": (1e7 * (1 + i * 0.1)),  # Decreasing trend (going back)
            "normalized_score": 0.3 + (i * 0.05),
        }
        for i in range(7)
    ]


@pytest.fixture
def sample_flight_data():
    """Sample flight data."""
    return [
        {"origin_id": "loc_gb_london", "passengers": 1500},
        {"origin_id": "loc_fr_paris", "passengers": 1200},
        {"origin_id": "loc_jp_tokyo", "passengers": 800},
    ]


@pytest.fixture
def sample_risk_map():
    """Sample risk map for origins."""
    return {
        "loc_gb_london": 55.0,
        "loc_fr_paris": 50.0,
        "loc_jp_tokyo": 35.0,
    }


class TestRiskComponents:
    """Tests for RiskComponents dataclass."""

    def test_to_dict(self):
        """Test components to dictionary conversion."""
        components = RiskComponents(
            wastewater_load=45.5,
            growth_velocity=30.2,
            import_pressure=25.8,
        )

        result = components.to_dict()

        assert result["wastewater_load"] == 45.5
        assert result["growth_velocity"] == 30.2
        assert result["import_pressure"] == 25.8


class TestRiskCalculation:
    """Tests for RiskCalculation dataclass."""

    def test_to_dict(self):
        """Test calculation to dictionary conversion."""
        components = RiskComponents(
            wastewater_load=45.0,
            growth_velocity=30.0,
            import_pressure=25.0,
        )

        calc = RiskCalculation(
            location_id="loc_test",
            risk_score=35.0,
            components=components,
            confidence=0.85,
            trend="rising",
            last_updated=datetime(2026, 1, 10, 12, 0, 0),
        )

        result = calc.to_dict()

        assert result["location_id"] == "loc_test"
        assert result["risk_score"] == 35.0
        assert result["confidence"] == 0.85
        assert result["trend"] == "rising"
        assert "components" in result


class TestRiskEngine:
    """Tests for RiskEngine class."""

    def test_weights_sum_to_one(self, risk_engine):
        """Test that component weights sum to 1.0."""
        total = (
            risk_engine.WEIGHT_WASTEWATER +
            risk_engine.WEIGHT_VELOCITY +
            risk_engine.WEIGHT_IMPORT
        )
        assert abs(total - 1.0) < 0.001

    def test_calculate_risk_basic(
        self,
        risk_engine,
        sample_wastewater_data,
        sample_flight_data,
        sample_risk_map
    ):
        """Test basic risk calculation."""
        result = risk_engine.calculate_risk(
            location_id="loc_us_new_york",
            wastewater_data=sample_wastewater_data,
            flight_data=sample_flight_data,
            risk_map=sample_risk_map,
        )

        assert isinstance(result, RiskCalculation)
        assert result.location_id == "loc_us_new_york"
        assert 0 <= result.risk_score <= 100
        assert 0 <= result.confidence <= 1
        assert result.trend in ["rising", "falling", "stable"]

    def test_calculate_risk_no_wastewater_data(self, risk_engine):
        """Test risk calculation with no wastewater data."""
        result = risk_engine.calculate_risk(
            location_id="loc_test",
            wastewater_data=[],
        )

        # Should use default values
        assert result.components.wastewater_load == 50.0
        assert result.confidence < 1.0

    def test_calculate_risk_no_flight_data(
        self,
        risk_engine,
        sample_wastewater_data
    ):
        """Test risk calculation with no flight data."""
        result = risk_engine.calculate_risk(
            location_id="loc_test",
            wastewater_data=sample_wastewater_data,
            flight_data=None,
        )

        # Should use default import pressure
        assert result.components.import_pressure == 30.0

    def test_risk_score_bounded(self, risk_engine):
        """Test that risk score is always in 0-100 range."""
        # Test with extreme values
        extreme_data = [
            {"timestamp": datetime.utcnow(), "raw_load": 1e12, "normalized_score": 2.0},
        ]

        result = risk_engine.calculate_risk(
            location_id="loc_test",
            wastewater_data=extreme_data,
        )

        assert 0 <= result.risk_score <= 100


class TestWastewaterComponent:
    """Tests for wastewater component calculation."""

    def test_uses_normalized_score(self, risk_engine):
        """Test that normalized score is preferred."""
        data = [
            {"timestamp": datetime.utcnow(), "normalized_score": 0.75, "raw_load": 1e6},
        ]

        result = risk_engine.calculate_risk("loc_test", data)

        # Should be 75 (0.75 * 100)
        assert abs(result.components.wastewater_load - 75.0) < 1.0

    def test_falls_back_to_raw_load(self, risk_engine):
        """Test fallback to raw load when no normalized score."""
        data = [
            {"timestamp": datetime.utcnow(), "raw_load": 5e8},  # Half of max
        ]

        result = risk_engine.calculate_risk("loc_test", data)

        assert result.components.wastewater_load == 50.0

    def test_uses_most_recent_data(self, risk_engine):
        """Test that most recent data point is used."""
        old_date = datetime.utcnow() - timedelta(days=5)
        recent_date = datetime.utcnow()

        data = [
            {"timestamp": old_date, "normalized_score": 0.3},
            {"timestamp": recent_date, "normalized_score": 0.8},
        ]

        result = risk_engine.calculate_risk("loc_test", data)

        # Should use 0.8 (80)
        assert result.components.wastewater_load == 80.0


class TestVelocityComponent:
    """Tests for velocity component calculation."""

    def test_increasing_trend(self, risk_engine):
        """Test velocity with increasing trend."""
        base = datetime.utcnow()
        data = [
            {"timestamp": base - timedelta(days=i), "normalized_score": 0.3 + (0.1 * (7 - i))}
            for i in range(7)
        ]

        result = risk_engine.calculate_risk("loc_test", data)

        # Increasing trend should give velocity > 50
        assert result.components.growth_velocity > 50

    def test_decreasing_trend(self, risk_engine):
        """Test velocity with decreasing trend."""
        base = datetime.utcnow()
        data = [
            {"timestamp": base - timedelta(days=i), "normalized_score": 0.8 - (0.1 * (7 - i))}
            for i in range(7)
        ]

        result = risk_engine.calculate_risk("loc_test", data)

        # Decreasing trend should give velocity < 50
        assert result.components.growth_velocity < 50

    def test_stable_trend(self, risk_engine):
        """Test velocity with stable trend."""
        base = datetime.utcnow()
        data = [
            {"timestamp": base - timedelta(days=i), "normalized_score": 0.5}
            for i in range(7)
        ]

        result = risk_engine.calculate_risk("loc_test", data)

        # Stable trend should give velocity around 50
        assert 45 <= result.components.growth_velocity <= 55


class TestImportComponent:
    """Tests for import pressure component calculation."""

    def test_high_risk_origins(self, risk_engine):
        """Test import from high-risk origins."""
        flight_data = [
            {"origin_id": "loc_high", "passengers": 1000},
        ]
        risk_map = {"loc_high": 90.0}

        result = risk_engine.calculate_risk(
            "loc_test", [], flight_data, risk_map
        )

        # Should have elevated import pressure
        assert result.components.import_pressure > 50

    def test_low_risk_origins(self, risk_engine):
        """Test import from low-risk origins."""
        flight_data = [
            {"origin_id": "loc_low", "passengers": 1000},
        ]
        risk_map = {"loc_low": 10.0}

        result = risk_engine.calculate_risk(
            "loc_test", [], flight_data, risk_map
        )

        # Should have lower import pressure
        assert result.components.import_pressure < 50

    def test_volume_effect(self, risk_engine):
        """Test that passenger volume affects import pressure."""
        low_volume = [{"origin_id": "loc_a", "passengers": 100}]
        high_volume = [{"origin_id": "loc_a", "passengers": 10000}]
        risk_map = {"loc_a": 50.0}

        result_low = risk_engine.calculate_risk("loc_test", [], low_volume, risk_map)
        result_high = risk_engine.calculate_risk("loc_test", [], high_volume, risk_map)

        # Higher volume should increase pressure
        assert result_high.components.import_pressure > result_low.components.import_pressure


class TestTrendDetermination:
    """Tests for trend determination."""

    def test_rising_trend(self, risk_engine):
        """Test rising trend detection."""
        base = datetime.utcnow()
        data = [
            {"timestamp": base - timedelta(days=i), "normalized_score": 0.3 + (0.1 * (7 - i))}
            for i in range(7)
        ]

        result = risk_engine.calculate_risk("loc_test", data)

        assert result.trend == "rising"

    def test_falling_trend(self, risk_engine):
        """Test falling trend detection."""
        base = datetime.utcnow()
        data = [
            {"timestamp": base - timedelta(days=i), "normalized_score": 0.8 - (0.1 * (7 - i))}
            for i in range(7)
        ]

        result = risk_engine.calculate_risk("loc_test", data)

        assert result.trend == "falling"

    def test_stable_trend(self, risk_engine):
        """Test stable trend detection."""
        base = datetime.utcnow()
        data = [
            {"timestamp": base - timedelta(days=i), "normalized_score": 0.5 + (0.01 * ((i % 2) * 2 - 1))}
            for i in range(7)
        ]

        result = risk_engine.calculate_risk("loc_test", data)

        assert result.trend == "stable"


class TestConfidenceCalculation:
    """Tests for confidence calculation."""

    def test_high_confidence_with_complete_data(
        self,
        risk_engine,
        sample_wastewater_data,
        sample_flight_data,
        sample_risk_map
    ):
        """Test high confidence with complete recent data."""
        result = risk_engine.calculate_risk(
            "loc_test",
            sample_wastewater_data,
            sample_flight_data,
            sample_risk_map,
        )

        assert result.confidence > 0.7

    def test_low_confidence_with_sparse_data(self, risk_engine):
        """Test low confidence with sparse data."""
        data = [
            {"timestamp": datetime.utcnow(), "normalized_score": 0.5},
        ]

        result = risk_engine.calculate_risk("loc_test", data)

        assert result.confidence < 0.8

    def test_low_confidence_with_stale_data(self, risk_engine):
        """Test low confidence with stale data."""
        old_date = datetime.utcnow() - timedelta(days=20)
        data = [
            {"timestamp": old_date, "normalized_score": 0.5},
        ]

        result = risk_engine.calculate_risk("loc_test", data)

        assert result.confidence < 0.6


class TestForecast:
    """Tests for forecast generation."""

    def test_generate_forecast(self, risk_engine):
        """Test forecast generation."""
        historical = [
            {"date": f"2026-01-0{i+1}", "risk_score": 40.0 + i * 2}
            for i in range(7)
        ]

        forecast = risk_engine.calculate_forecast(historical, days=7)

        assert len(forecast) == 7
        for point in forecast:
            assert "date" in point
            assert "risk_score" in point
            assert "confidence_low" in point
            assert "confidence_high" in point

    def test_forecast_confidence_expands(self, risk_engine):
        """Test that confidence interval expands over time."""
        historical = [
            {"date": f"2026-01-0{i+1}", "risk_score": 50.0}
            for i in range(7)
        ]

        forecast = risk_engine.calculate_forecast(historical, days=7)

        # Later forecasts should have wider confidence intervals
        first_range = forecast[0]["confidence_high"] - forecast[0]["confidence_low"]
        last_range = forecast[-1]["confidence_high"] - forecast[-1]["confidence_low"]

        assert last_range > first_range

    def test_forecast_follows_trend(self, risk_engine):
        """Test that forecast follows historical trend."""
        # Rising trend
        historical = [
            {"date": f"2026-01-0{i+1}", "risk_score": 40.0 + i * 3}
            for i in range(7)
        ]

        forecast = risk_engine.calculate_forecast(historical, days=3)

        # Forecast should continue upward
        assert forecast[-1]["risk_score"] > historical[-1]["risk_score"]

    def test_forecast_bounded(self, risk_engine):
        """Test that forecast stays in 0-100 range."""
        # Extreme rising trend
        historical = [
            {"date": f"2026-01-0{i+1}", "risk_score": 80.0 + i * 5}
            for i in range(7)
        ]

        forecast = risk_engine.calculate_forecast(historical, days=10)

        for point in forecast:
            assert 0 <= point["risk_score"] <= 100
            assert 0 <= point["confidence_low"] <= 100
            assert 0 <= point["confidence_high"] <= 100


class TestRegionalAggregation:
    """Tests for regional risk aggregation."""

    def test_simple_average(self, risk_engine):
        """Test simple average aggregation."""
        components = RiskComponents(50, 50, 50)

        risks = [
            RiskCalculation("loc_1", 40.0, components, 0.9, "stable", datetime.utcnow()),
            RiskCalculation("loc_2", 60.0, components, 0.9, "stable", datetime.utcnow()),
        ]

        result = risk_engine.aggregate_regional_risk(risks)

        assert result == 50.0

    def test_weighted_average(self, risk_engine):
        """Test weighted average aggregation."""
        components = RiskComponents(50, 50, 50)

        risks = [
            RiskCalculation("loc_1", 40.0, components, 0.9, "stable", datetime.utcnow()),
            RiskCalculation("loc_2", 60.0, components, 0.9, "stable", datetime.utcnow()),
        ]

        weights = {"loc_1": 3.0, "loc_2": 1.0}  # loc_1 has 3x weight

        result = risk_engine.aggregate_regional_risk(risks, weights)

        # (40 * 3 + 60 * 1) / 4 = 45
        assert result == 45.0
