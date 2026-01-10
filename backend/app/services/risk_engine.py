"""
Risk Score Calculation Engine

Calculates location-specific viral risk scores based on:
- Wastewater surveillance signals (40% weight)
- Growth velocity / trend (30% weight)
- Import pressure from travel (30% weight)

Risk Score Formula:
risk_score = (w1 * wastewater_component) + (w2 * velocity_component) + (w3 * import_component)

Where each component is normalized to 0-100 scale.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import math
import numpy as np


@dataclass
class RiskComponents:
    """Individual risk score components."""
    wastewater_load: float  # 0-100
    growth_velocity: float  # 0-100
    import_pressure: float  # 0-100

    def to_dict(self) -> Dict[str, float]:
        return {
            "wastewater_load": round(self.wastewater_load, 1),
            "growth_velocity": round(self.growth_velocity, 1),
            "import_pressure": round(self.import_pressure, 1),
        }


@dataclass
class RiskCalculation:
    """Complete risk calculation result."""
    location_id: str
    risk_score: float  # 0-100
    components: RiskComponents
    confidence: float  # 0-1
    trend: str  # rising, falling, stable
    last_updated: datetime

    def to_dict(self) -> dict:
        return {
            "location_id": self.location_id,
            "risk_score": round(self.risk_score, 1),
            "components": self.components.to_dict(),
            "confidence": round(self.confidence, 2),
            "trend": self.trend,
            "last_updated": self.last_updated.isoformat() + "Z",
        }


class RiskEngine:
    """
    Risk score calculation engine.

    Uses a weighted combination of wastewater signals, growth velocity,
    and import pressure to compute location-specific risk scores.
    """

    # Component weights (must sum to 1.0)
    WEIGHT_WASTEWATER = 0.40
    WEIGHT_VELOCITY = 0.30
    WEIGHT_IMPORT = 0.30

    # Normalization parameters
    WASTEWATER_MAX = 1e9  # Max expected viral load (copies/L)
    VELOCITY_MAX = 0.5  # Max expected weekly change (50%)

    # Trend thresholds
    TREND_RISING_THRESHOLD = 0.05
    TREND_FALLING_THRESHOLD = -0.05

    # Data quality thresholds
    MIN_DATA_POINTS = 3
    MAX_DATA_AGE_DAYS = 14

    def __init__(self):
        """Initialize risk engine."""
        pass

    def calculate_risk(
        self,
        location_id: str,
        wastewater_data: List[Dict],
        flight_data: Optional[List[Dict]] = None,
        risk_map: Optional[Dict[str, float]] = None,
    ) -> RiskCalculation:
        """
        Calculate risk score for a location.

        Args:
            location_id: Location identifier
            wastewater_data: List of wastewater surveillance records
                [{"timestamp": datetime, "raw_load": float, "normalized_score": float}]
            flight_data: List of incoming flight records
                [{"origin_id": str, "passengers": int}]
            risk_map: Dict mapping origin location IDs to their risk scores

        Returns:
            RiskCalculation with score and components
        """
        # Calculate individual components
        wastewater_component = self._calculate_wastewater_component(wastewater_data)
        velocity_component = self._calculate_velocity_component(wastewater_data)
        import_component = self._calculate_import_component(flight_data, risk_map)

        # Combine components
        risk_score = (
            self.WEIGHT_WASTEWATER * wastewater_component +
            self.WEIGHT_VELOCITY * velocity_component +
            self.WEIGHT_IMPORT * import_component
        )

        # Determine trend
        trend = self._determine_trend(wastewater_data)

        # Calculate confidence
        confidence = self._calculate_confidence(wastewater_data, flight_data)

        components = RiskComponents(
            wastewater_load=wastewater_component,
            growth_velocity=velocity_component,
            import_pressure=import_component,
        )

        return RiskCalculation(
            location_id=location_id,
            risk_score=risk_score,
            components=components,
            confidence=confidence,
            trend=trend,
            last_updated=datetime.utcnow(),
        )

    def _calculate_wastewater_component(
        self,
        wastewater_data: List[Dict]
    ) -> float:
        """
        Calculate wastewater component (0-100).

        Uses the most recent normalized score, or calculates from raw load.
        """
        if not wastewater_data:
            return 50.0  # Default moderate risk when no data

        # Sort by timestamp, get most recent
        sorted_data = sorted(
            wastewater_data,
            key=lambda x: x.get("timestamp", datetime.min),
            reverse=True
        )

        recent = sorted_data[0]

        # Use normalized score if available
        if "normalized_score" in recent and recent["normalized_score"] is not None:
            return min(100, max(0, recent["normalized_score"] * 100))

        # Calculate from raw load
        if "raw_load" in recent and recent["raw_load"] is not None:
            normalized = min(1.0, recent["raw_load"] / self.WASTEWATER_MAX)
            return normalized * 100

        return 50.0  # Default

    def _calculate_velocity_component(
        self,
        wastewater_data: List[Dict]
    ) -> float:
        """
        Calculate velocity/growth component (0-100).

        Based on week-over-week change in wastewater signal.
        """
        if not wastewater_data or len(wastewater_data) < 2:
            return 50.0  # Default neutral velocity

        # Sort by timestamp
        sorted_data = sorted(
            wastewater_data,
            key=lambda x: x.get("timestamp", datetime.min)
        )

        # Calculate velocity from recent data points
        if len(sorted_data) >= 7:
            # Use 7-day rolling average comparison
            recent_week = sorted_data[-7:]
            prior_week = sorted_data[-14:-7] if len(sorted_data) >= 14 else sorted_data[:7]

            recent_avg = self._calculate_average_load(recent_week)
            prior_avg = self._calculate_average_load(prior_week)

            if prior_avg > 0:
                velocity = (recent_avg - prior_avg) / prior_avg
            else:
                velocity = 0.0
        else:
            # Simple comparison with available data
            newest = self._get_load(sorted_data[-1])
            oldest = self._get_load(sorted_data[0])

            if oldest > 0:
                velocity = (newest - oldest) / oldest
            else:
                velocity = 0.0

        # Normalize velocity to 0-100 scale
        # Positive velocity = higher risk, negative = lower risk
        # Clamp to max velocity
        velocity = max(-self.VELOCITY_MAX, min(self.VELOCITY_MAX, velocity))

        # Map [-0.5, 0.5] to [0, 100]
        normalized = ((velocity / self.VELOCITY_MAX) + 1) / 2 * 100

        return normalized

    def _calculate_import_component(
        self,
        flight_data: Optional[List[Dict]],
        risk_map: Optional[Dict[str, float]],
    ) -> float:
        """
        Calculate import pressure component (0-100).

        Based on incoming passenger volume weighted by origin risk.
        """
        if not flight_data or not risk_map:
            return 30.0  # Default moderate import pressure

        total_risk_weighted_pax = 0.0
        total_passengers = 0

        for flight in flight_data:
            origin_id = flight.get("origin_id", "")
            passengers = flight.get("passengers", 0)

            # Get origin risk (default to moderate if unknown)
            origin_risk = risk_map.get(origin_id, 50.0) / 100.0

            total_risk_weighted_pax += passengers * origin_risk
            total_passengers += passengers

        if total_passengers == 0:
            return 30.0

        # Average risk-weighted import pressure
        avg_import_risk = total_risk_weighted_pax / total_passengers

        # Scale based on passenger volume (more passengers = higher pressure)
        # Assume 10000 pax/day is high volume
        volume_factor = min(1.0, total_passengers / 10000)

        # Combine risk level with volume
        import_component = avg_import_risk * 100 * (0.5 + 0.5 * volume_factor)

        return min(100, max(0, import_component))

    def _determine_trend(self, wastewater_data: List[Dict]) -> str:
        """Determine trend (rising, falling, stable)."""
        if not wastewater_data or len(wastewater_data) < 3:
            return "stable"

        # Sort by timestamp
        sorted_data = sorted(
            wastewater_data,
            key=lambda x: x.get("timestamp", datetime.min)
        )

        # Use linear regression for trend
        loads = [self._get_load(d) for d in sorted_data[-7:]]

        if len(loads) < 3:
            return "stable"

        # Simple slope calculation
        n = len(loads)
        x_mean = (n - 1) / 2
        y_mean = sum(loads) / n

        numerator = sum((i - x_mean) * (loads[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return "stable"

        slope = numerator / denominator

        # Normalize slope relative to mean
        if y_mean > 0:
            relative_slope = slope / y_mean
        else:
            relative_slope = 0

        if relative_slope > self.TREND_RISING_THRESHOLD:
            return "rising"
        elif relative_slope < self.TREND_FALLING_THRESHOLD:
            return "falling"
        else:
            return "stable"

    def _calculate_confidence(
        self,
        wastewater_data: List[Dict],
        flight_data: Optional[List[Dict]],
    ) -> float:
        """
        Calculate confidence score (0-1).

        Based on data availability, recency, and consistency.
        """
        confidence = 1.0

        # Penalize for missing or sparse wastewater data
        if not wastewater_data:
            confidence *= 0.5
        elif len(wastewater_data) < self.MIN_DATA_POINTS:
            confidence *= 0.7

        # Penalize for stale data
        if wastewater_data:
            latest = max(
                wastewater_data,
                key=lambda x: x.get("timestamp", datetime.min)
            )
            latest_ts = latest.get("timestamp")
            if latest_ts:
                age_days = (datetime.utcnow() - latest_ts).days
                if age_days > self.MAX_DATA_AGE_DAYS:
                    confidence *= 0.5
                elif age_days > 7:
                    confidence *= 0.8

        # Penalize for missing flight data
        if not flight_data:
            confidence *= 0.9

        return max(0.1, min(1.0, confidence))

    def _calculate_average_load(self, data: List[Dict]) -> float:
        """Calculate average load from data points."""
        loads = [self._get_load(d) for d in data]
        valid_loads = [l for l in loads if l > 0]

        if not valid_loads:
            return 0.0

        return sum(valid_loads) / len(valid_loads)

    def _get_load(self, data_point: Dict) -> float:
        """Extract load value from data point."""
        if "normalized_score" in data_point and data_point["normalized_score"]:
            return data_point["normalized_score"]
        if "raw_load" in data_point and data_point["raw_load"]:
            return data_point["raw_load"] / self.WASTEWATER_MAX
        return 0.0

    def calculate_forecast(
        self,
        historical_data: List[Dict],
        days: int = 7,
    ) -> List[Dict]:
        """
        Generate risk score forecast.

        Uses simple exponential smoothing for projection.

        Args:
            historical_data: List of historical risk scores
                [{"date": str, "risk_score": float}]
            days: Number of days to forecast

        Returns:
            List of forecast points with confidence intervals
        """
        if not historical_data:
            return []

        # Sort by date
        sorted_data = sorted(historical_data, key=lambda x: x.get("date", ""))

        # Extract risk scores
        scores = [d.get("risk_score", 50.0) for d in sorted_data]

        if len(scores) < 3:
            # Not enough data for forecast
            last_score = scores[-1] if scores else 50.0
            return self._generate_flat_forecast(last_score, days)

        # Exponential smoothing
        alpha = 0.3  # Smoothing factor
        smoothed = [scores[0]]

        for i in range(1, len(scores)):
            smoothed.append(alpha * scores[i] + (1 - alpha) * smoothed[-1])

        # Calculate trend
        if len(smoothed) >= 7:
            recent_trend = (smoothed[-1] - smoothed[-7]) / 7
        else:
            recent_trend = (smoothed[-1] - smoothed[0]) / len(smoothed)

        # Generate forecast
        forecast = []
        last_date = datetime.strptime(sorted_data[-1]["date"], "%Y-%m-%d")
        last_score = smoothed[-1]

        # Confidence interval expands over time
        base_confidence = 5.0

        for i in range(1, days + 1):
            forecast_date = last_date + timedelta(days=i)
            forecast_score = last_score + (recent_trend * i)

            # Clamp to valid range
            forecast_score = max(0, min(100, forecast_score))

            # Confidence interval expands
            confidence_margin = base_confidence * math.sqrt(i)

            forecast.append({
                "date": forecast_date.strftime("%Y-%m-%d"),
                "risk_score": round(forecast_score, 1),
                "confidence_low": round(max(0, forecast_score - confidence_margin), 1),
                "confidence_high": round(min(100, forecast_score + confidence_margin), 1),
            })

        return forecast

    def _generate_flat_forecast(
        self,
        last_score: float,
        days: int
    ) -> List[Dict]:
        """Generate flat forecast when insufficient data."""
        forecast = []
        today = datetime.utcnow().date()
        base_confidence = 10.0

        for i in range(1, days + 1):
            forecast_date = today + timedelta(days=i)
            confidence_margin = base_confidence * math.sqrt(i)

            forecast.append({
                "date": forecast_date.strftime("%Y-%m-%d"),
                "risk_score": round(last_score, 1),
                "confidence_low": round(max(0, last_score - confidence_margin), 1),
                "confidence_high": round(min(100, last_score + confidence_margin), 1),
            })

        return forecast

    def aggregate_regional_risk(
        self,
        location_risks: List[RiskCalculation],
        weights: Optional[Dict[str, float]] = None,
    ) -> float:
        """
        Aggregate risk scores from multiple locations.

        Args:
            location_risks: List of individual location risk calculations
            weights: Optional dict of location_id -> weight (e.g., population)

        Returns:
            Aggregated risk score
        """
        if not location_risks:
            return 50.0

        if weights:
            total_weight = sum(
                weights.get(r.location_id, 1.0) for r in location_risks
            )
            weighted_sum = sum(
                r.risk_score * weights.get(r.location_id, 1.0)
                for r in location_risks
            )
            return weighted_sum / total_weight if total_weight > 0 else 50.0
        else:
            # Simple average
            return sum(r.risk_score for r in location_risks) / len(location_risks)
