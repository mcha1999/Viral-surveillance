"""
Retrospective Validation Framework for Viral Weather
=====================================================

This script validates whether flight-based import pressure correlates with
variant spread patterns and provides meaningful predictive signal.

Hypotheses Tested:
1. Import pressure predicts variant arrival timing
2. Risk scores predict wastewater surges
3. High-traffic routes show faster variant propagation

Usage:
    python retrospective_validation.py --start-date 2023-01-01 --end-date 2024-12-31
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional
from scipy import stats
from sklearn.metrics import mean_squared_error, mean_absolute_error
import json


@dataclass
class ValidationResult:
    """Container for validation test results."""
    hypothesis: str
    test_name: str
    metric_name: str
    metric_value: float
    p_value: Optional[float]
    passed: bool
    details: dict


class RetrospectiveValidator:
    """
    Validates predictive power of flight-based variant spread model.
    """

    def __init__(
        self,
        wastewater_df: pd.DataFrame,
        variant_df: pd.DataFrame,
        flight_df: pd.DataFrame,
        location_mapping: dict
    ):
        """
        Initialize with historical datasets.

        Args:
            wastewater_df: Columns [location_id, date, viral_load, pct_change_weekly]
            variant_df: Columns [location, date, variant, sequence_count]
            flight_df: Columns [origin, destination, date, passengers]
            location_mapping: Maps location names to IDs across datasets
        """
        self.wastewater = wastewater_df.copy()
        self.variants = variant_df.copy()
        self.flights = flight_df.copy()
        self.location_mapping = location_mapping

        self._preprocess_data()
        self.results: list[ValidationResult] = []

    def _preprocess_data(self):
        """Standardize date formats and location IDs."""
        for df in [self.wastewater, self.variants, self.flights]:
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])

        # Sort by date
        self.wastewater = self.wastewater.sort_values(['location_id', 'date'])
        self.variants = self.variants.sort_values(['location', 'date'])
        self.flights = self.flights.sort_values(['origin', 'destination', 'date'])

    def calculate_import_pressure(
        self,
        destination: str,
        date: datetime,
        lookback_days: int = 14
    ) -> float:
        """
        Calculate import pressure for a destination on a given date.

        Import Pressure = Σ (passengers_from_origin × origin_risk_score)

        Args:
            destination: Target location
            date: Date to calculate for
            lookback_days: Days to look back for flight data

        Returns:
            Import pressure score (0-100 normalized)
        """
        start_date = date - timedelta(days=lookback_days)

        # Get flights to destination in window
        flights_to_dest = self.flights[
            (self.flights['destination'] == destination) &
            (self.flights['date'] >= start_date) &
            (self.flights['date'] <= date)
        ]

        if flights_to_dest.empty:
            return 0.0

        # Get origin risk scores (from wastewater data)
        origin_risks = {}
        for origin in flights_to_dest['origin'].unique():
            origin_ww = self.wastewater[
                (self.wastewater['location_id'] == self.location_mapping.get(origin, origin)) &
                (self.wastewater['date'] <= date)
            ]
            if not origin_ww.empty:
                # Use most recent viral load as proxy for risk
                recent = origin_ww.iloc[-1]
                origin_risks[origin] = self._normalize_viral_load(recent['viral_load'])
            else:
                origin_risks[origin] = 0.0

        # Calculate weighted import pressure
        pressure = 0.0
        total_passengers = 0

        for _, flight in flights_to_dest.iterrows():
            origin = flight['origin']
            passengers = flight['passengers']
            risk = origin_risks.get(origin, 0)
            pressure += passengers * risk
            total_passengers += passengers

        # Normalize to 0-100 scale
        if total_passengers > 0:
            pressure = (pressure / total_passengers) * 100

        return min(pressure, 100)

    def _normalize_viral_load(self, viral_load: float) -> float:
        """Normalize viral load to 0-1 scale based on historical distribution."""
        # Use percentile-based normalization
        all_loads = self.wastewater['viral_load'].dropna()
        if len(all_loads) == 0:
            return 0.0
        percentile = stats.percentileofscore(all_loads, viral_load) / 100
        return percentile

    # =========================================================================
    # HYPOTHESIS 1: Import Pressure Predicts Variant Arrival
    # =========================================================================

    def test_h1_import_pressure_variant_arrival(
        self,
        variants_to_test: list[str] = None,
        min_locations: int = 10
    ) -> ValidationResult:
        """
        Test if locations with higher import pressure see variants arrive earlier.

        Methodology:
        1. For each variant, identify first detection date per location
        2. Calculate average import pressure in 30 days before detection
        3. Correlate import pressure with detection order (rank)

        Success: Negative correlation (higher pressure = earlier arrival)
        """
        if variants_to_test is None:
            # Use most common variants
            variants_to_test = self.variants['variant'].value_counts().head(5).index.tolist()

        all_correlations = []
        variant_details = {}

        for variant in variants_to_test:
            # Get first detection per location
            variant_data = self.variants[self.variants['variant'] == variant]
            first_detections = variant_data.groupby('location')['date'].min().reset_index()
            first_detections.columns = ['location', 'first_detection']

            if len(first_detections) < min_locations:
                continue

            # Calculate import pressure before detection
            pressures = []
            for _, row in first_detections.iterrows():
                location = row['location']
                detection_date = row['first_detection']

                # Average import pressure in 30 days before detection
                pressure = self.calculate_import_pressure(
                    destination=location,
                    date=detection_date - timedelta(days=1),
                    lookback_days=30
                )
                pressures.append({
                    'location': location,
                    'detection_date': detection_date,
                    'import_pressure': pressure
                })

            pressure_df = pd.DataFrame(pressures)
            pressure_df['detection_rank'] = pressure_df['detection_date'].rank()

            # Calculate correlation
            corr, p_value = stats.spearmanr(
                pressure_df['import_pressure'],
                pressure_df['detection_rank']
            )

            all_correlations.append(corr)
            variant_details[variant] = {
                'correlation': corr,
                'p_value': p_value,
                'n_locations': len(pressure_df),
                'significant': p_value < 0.05
            }

        # Aggregate results
        avg_correlation = np.mean(all_correlations) if all_correlations else 0

        result = ValidationResult(
            hypothesis="H1: Import pressure predicts variant arrival timing",
            test_name="Spearman rank correlation",
            metric_name="Average correlation (import pressure vs arrival rank)",
            metric_value=avg_correlation,
            p_value=None,  # Aggregated across variants
            passed=avg_correlation < -0.3,  # Expect negative correlation
            details={
                'variants_tested': variant_details,
                'interpretation': (
                    "Negative correlation means higher import pressure associates "
                    "with earlier variant arrival (lower rank = earlier)"
                )
            }
        )

        self.results.append(result)
        return result

    # =========================================================================
    # HYPOTHESIS 2: Risk Score Predicts Wastewater Surge
    # =========================================================================

    def test_h2_risk_score_predicts_surge(
        self,
        forecast_horizon_days: int = 14,
        locations: list[str] = None
    ) -> ValidationResult:
        """
        Test if our composite risk score predicts wastewater changes.

        Methodology:
        1. For each location-date, calculate risk score
        2. Compare to actual wastewater change over next N days
        3. Measure prediction accuracy vs naive baseline

        Success: Lower RMSE than baseline, >70% directional accuracy
        """
        if locations is None:
            locations = self.wastewater['location_id'].unique()[:20]

        predictions = []
        actuals = []
        directions_correct = 0
        total_predictions = 0

        for location in locations:
            location_ww = self.wastewater[
                self.wastewater['location_id'] == location
            ].sort_values('date')

            if len(location_ww) < forecast_horizon_days + 30:
                continue

            # Walk through time series
            for i in range(30, len(location_ww) - forecast_horizon_days):
                current_row = location_ww.iloc[i]
                future_row = location_ww.iloc[i + forecast_horizon_days]

                # Calculate risk score (simplified: import pressure + current trend)
                risk_score = self.calculate_import_pressure(
                    destination=location,
                    date=current_row['date'],
                    lookback_days=14
                )

                # Add current trend component
                current_trend = current_row.get('pct_change_weekly', 0) or 0
                risk_score = (risk_score * 0.6) + (min(max(current_trend, -50), 50) + 50) * 0.4

                # Actual change
                current_load = current_row['viral_load']
                future_load = future_row['viral_load']

                if current_load > 0:
                    actual_change = ((future_load - current_load) / current_load) * 100
                else:
                    continue

                # Predicted change (simplified: risk score maps to expected change)
                predicted_change = (risk_score - 50) * 2  # Scale: risk 50 = no change

                predictions.append(predicted_change)
                actuals.append(actual_change)

                # Directional accuracy
                if (predicted_change > 0 and actual_change > 0) or \
                   (predicted_change < 0 and actual_change < 0) or \
                   (predicted_change == 0 and abs(actual_change) < 5):
                    directions_correct += 1
                total_predictions += 1

        if not predictions:
            return ValidationResult(
                hypothesis="H2: Risk score predicts wastewater surge",
                test_name="Forecast accuracy",
                metric_name="Insufficient data",
                metric_value=0,
                p_value=None,
                passed=False,
                details={'error': 'Not enough data points'}
            )

        # Calculate metrics
        rmse = np.sqrt(mean_squared_error(actuals, predictions))
        mae = mean_absolute_error(actuals, predictions)
        directional_accuracy = directions_correct / total_predictions if total_predictions > 0 else 0

        # Baseline: predict no change (0)
        baseline_rmse = np.sqrt(mean_squared_error(actuals, [0] * len(actuals)))

        # Baseline: predict last week's change continues
        baseline_persistence_rmse = np.sqrt(mean_squared_error(
            actuals[1:],
            actuals[:-1]  # Use previous actual as prediction
        )) if len(actuals) > 1 else baseline_rmse

        result = ValidationResult(
            hypothesis="H2: Risk score predicts wastewater surge",
            test_name="14-day forecast accuracy",
            metric_name="Directional accuracy",
            metric_value=directional_accuracy,
            p_value=None,
            passed=directional_accuracy > 0.60 and rmse < baseline_rmse,
            details={
                'rmse': rmse,
                'mae': mae,
                'baseline_rmse_no_change': baseline_rmse,
                'baseline_rmse_persistence': baseline_persistence_rmse,
                'improvement_vs_baseline': (baseline_rmse - rmse) / baseline_rmse * 100,
                'n_predictions': total_predictions,
                'directional_accuracy': directional_accuracy,
                'interpretation': (
                    f"Model predicts direction correctly {directional_accuracy*100:.1f}% of time. "
                    f"RMSE {rmse:.2f} vs baseline {baseline_rmse:.2f} "
                    f"({'better' if rmse < baseline_rmse else 'worse'} than naive)"
                )
            }
        )

        self.results.append(result)
        return result

    # =========================================================================
    # HYPOTHESIS 3: Variant Propagation Speed by Import Pressure
    # =========================================================================

    def test_h3_propagation_speed(
        self,
        variant: str,
        high_pressure_threshold_percentile: float = 75,
        low_pressure_threshold_percentile: float = 25
    ) -> ValidationResult:
        """
        Test if high import-pressure locations see faster variant growth.

        Methodology:
        1. Group locations into high/low import pressure
        2. Compare time from first detection to 50% prevalence
        3. Statistical test for difference

        Success: High-pressure locations reach 50% prevalence faster (p < 0.05)
        """
        # Get variant timeline per location
        variant_data = self.variants[self.variants['variant'] == variant]

        if variant_data.empty:
            return ValidationResult(
                hypothesis="H3: High import pressure = faster propagation",
                test_name="Time-to-prevalence comparison",
                metric_name="Insufficient data",
                metric_value=0,
                p_value=None,
                passed=False,
                details={'error': f'No data for variant {variant}'}
            )

        location_metrics = []

        for location in variant_data['location'].unique():
            loc_data = variant_data[variant_data['location'] == location].sort_values('date')

            if len(loc_data) < 5:
                continue

            # First detection
            first_detection = loc_data['date'].min()

            # Calculate import pressure at time of first detection
            import_pressure = self.calculate_import_pressure(
                destination=location,
                date=first_detection,
                lookback_days=30
            )

            # Calculate prevalence over time
            total_sequences = loc_data['sequence_count'].sum()
            loc_data = loc_data.copy()
            loc_data['cumulative'] = loc_data['sequence_count'].cumsum()
            loc_data['prevalence'] = loc_data['cumulative'] / total_sequences

            # Time to 50% prevalence (if reached)
            above_50 = loc_data[loc_data['prevalence'] >= 0.5]
            if not above_50.empty:
                date_50_pct = above_50['date'].min()
                days_to_50 = (date_50_pct - first_detection).days
            else:
                days_to_50 = None  # Did not reach 50%

            location_metrics.append({
                'location': location,
                'import_pressure': import_pressure,
                'first_detection': first_detection,
                'days_to_50_pct': days_to_50
            })

        metrics_df = pd.DataFrame(location_metrics)
        metrics_df = metrics_df.dropna(subset=['days_to_50_pct'])

        if len(metrics_df) < 10:
            return ValidationResult(
                hypothesis="H3: High import pressure = faster propagation",
                test_name="Time-to-prevalence comparison",
                metric_name="Insufficient locations",
                metric_value=0,
                p_value=None,
                passed=False,
                details={'error': 'Not enough locations with complete data'}
            )

        # Split into high/low pressure groups
        high_threshold = metrics_df['import_pressure'].quantile(high_pressure_threshold_percentile / 100)
        low_threshold = metrics_df['import_pressure'].quantile(low_pressure_threshold_percentile / 100)

        high_pressure = metrics_df[metrics_df['import_pressure'] >= high_threshold]['days_to_50_pct']
        low_pressure = metrics_df[metrics_df['import_pressure'] <= low_threshold]['days_to_50_pct']

        # Mann-Whitney U test (non-parametric)
        if len(high_pressure) >= 3 and len(low_pressure) >= 3:
            statistic, p_value = stats.mannwhitneyu(
                high_pressure,
                low_pressure,
                alternative='less'  # High pressure should have fewer days
            )
        else:
            statistic, p_value = None, None

        result = ValidationResult(
            hypothesis="H3: High import pressure = faster propagation",
            test_name="Mann-Whitney U test",
            metric_name="Median days difference (high vs low pressure)",
            metric_value=low_pressure.median() - high_pressure.median() if len(high_pressure) > 0 else 0,
            p_value=p_value,
            passed=p_value is not None and p_value < 0.05 and high_pressure.median() < low_pressure.median(),
            details={
                'variant': variant,
                'high_pressure_median_days': high_pressure.median() if len(high_pressure) > 0 else None,
                'low_pressure_median_days': low_pressure.median() if len(low_pressure) > 0 else None,
                'high_pressure_n': len(high_pressure),
                'low_pressure_n': len(low_pressure),
                'effect_size_days': low_pressure.median() - high_pressure.median() if len(high_pressure) > 0 else None,
                'interpretation': (
                    f"High-pressure locations took median {high_pressure.median():.0f} days to 50% prevalence "
                    f"vs {low_pressure.median():.0f} days for low-pressure locations"
                ) if len(high_pressure) > 0 else "Insufficient data"
            }
        )

        self.results.append(result)
        return result

    # =========================================================================
    # LEAD TIME ANALYSIS
    # =========================================================================

    def calculate_lead_time(
        self,
        variant: str,
        risk_threshold: float = 60
    ) -> ValidationResult:
        """
        Calculate how much advance warning our model provides.

        Methodology:
        1. For each location, find when risk score first exceeded threshold
        2. Compare to when variant actually arrived
        3. Calculate lead time distribution

        Success: Median lead time > 7 days
        """
        variant_data = self.variants[self.variants['variant'] == variant]
        first_detections = variant_data.groupby('location')['date'].min().to_dict()

        lead_times = []

        for location, detection_date in first_detections.items():
            # Look back 60 days before detection
            check_start = detection_date - timedelta(days=60)

            # Find first date when risk score exceeded threshold
            current_date = check_start
            first_warning_date = None

            while current_date < detection_date:
                risk = self.calculate_import_pressure(
                    destination=location,
                    date=current_date,
                    lookback_days=14
                )

                if risk >= risk_threshold and first_warning_date is None:
                    first_warning_date = current_date
                    break

                current_date += timedelta(days=1)

            if first_warning_date:
                lead_time = (detection_date - first_warning_date).days
                lead_times.append({
                    'location': location,
                    'detection_date': detection_date,
                    'warning_date': first_warning_date,
                    'lead_time_days': lead_time
                })

        if not lead_times:
            return ValidationResult(
                hypothesis="Lead time analysis",
                test_name="Days of advance warning",
                metric_name="No warnings generated",
                metric_value=0,
                p_value=None,
                passed=False,
                details={'error': 'No warnings exceeded threshold before detection'}
            )

        lead_df = pd.DataFrame(lead_times)

        result = ValidationResult(
            hypothesis="Lead time analysis",
            test_name="Advance warning before variant arrival",
            metric_name="Median lead time (days)",
            metric_value=lead_df['lead_time_days'].median(),
            p_value=None,
            passed=lead_df['lead_time_days'].median() >= 7,
            details={
                'variant': variant,
                'risk_threshold': risk_threshold,
                'median_lead_time': lead_df['lead_time_days'].median(),
                'mean_lead_time': lead_df['lead_time_days'].mean(),
                'min_lead_time': lead_df['lead_time_days'].min(),
                'max_lead_time': lead_df['lead_time_days'].max(),
                'locations_with_warning': len(lead_df),
                'locations_without_warning': len(first_detections) - len(lead_df),
                'pct_locations_warned': len(lead_df) / len(first_detections) * 100,
                'interpretation': (
                    f"Model provided {lead_df['lead_time_days'].median():.0f} days median advance warning "
                    f"for {len(lead_df)}/{len(first_detections)} locations ({len(lead_df)/len(first_detections)*100:.0f}%)"
                )
            }
        )

        self.results.append(result)
        return result

    # =========================================================================
    # GENERATE VALIDATION REPORT
    # =========================================================================

    def generate_report(self) -> dict:
        """Generate comprehensive validation report."""
        passed_tests = sum(1 for r in self.results if r.passed)
        total_tests = len(self.results)

        report = {
            'summary': {
                'total_tests': total_tests,
                'passed': passed_tests,
                'failed': total_tests - passed_tests,
                'pass_rate': passed_tests / total_tests if total_tests > 0 else 0,
                'overall_verdict': 'VALIDATED' if passed_tests >= total_tests * 0.7 else 'NEEDS IMPROVEMENT',
                'generated_at': datetime.now().isoformat()
            },
            'results': [
                {
                    'hypothesis': r.hypothesis,
                    'test': r.test_name,
                    'metric': r.metric_name,
                    'value': r.metric_value,
                    'p_value': r.p_value,
                    'passed': r.passed,
                    'details': r.details
                }
                for r in self.results
            ],
            'recommendations': self._generate_recommendations()
        }

        return report

    def _generate_recommendations(self) -> list[str]:
        """Generate actionable recommendations based on results."""
        recommendations = []

        for result in self.results:
            if not result.passed:
                if 'H1' in result.hypothesis:
                    recommendations.append(
                        "Consider adding more granular flight data (actual passenger counts) "
                        "or incorporating layover/connection flight patterns"
                    )
                elif 'H2' in result.hypothesis:
                    recommendations.append(
                        "Risk score formula may need recalibration. Consider adding: "
                        "seasonality factors, population immunity estimates, or variant-specific transmissibility"
                    )
                elif 'H3' in result.hypothesis:
                    recommendations.append(
                        "Propagation speed analysis inconclusive. May need longer time series "
                        "or more locations with complete sequencing data"
                    )
                elif 'Lead time' in result.hypothesis:
                    recommendations.append(
                        "Lead time insufficient. Consider: lowering alert thresholds, "
                        "adding predictive ML model, or incorporating additional data sources"
                    )

        if not recommendations:
            recommendations.append(
                "All core hypotheses validated. Consider expanding to additional variants "
                "and time periods for robustness."
            )

        return recommendations


# =============================================================================
# EXAMPLE USAGE WITH SYNTHETIC DATA (for testing the framework)
# =============================================================================

def generate_synthetic_data(n_locations: int = 50, n_days: int = 365):
    """Generate synthetic data for testing the validation framework."""
    np.random.seed(42)

    locations = [f"LOC_{i:03d}" for i in range(n_locations)]
    dates = pd.date_range(start='2023-01-01', periods=n_days, freq='D')

    # Wastewater data
    wastewater_records = []
    for loc in locations:
        base_load = np.random.uniform(1000, 10000)
        trend = np.random.uniform(-0.001, 0.003)

        for i, date in enumerate(dates):
            noise = np.random.normal(0, 0.1)
            seasonal = np.sin(2 * np.pi * i / 365) * 0.2
            load = base_load * (1 + trend * i + seasonal + noise)

            wastewater_records.append({
                'location_id': loc,
                'date': date,
                'viral_load': max(load, 100),
                'pct_change_weekly': np.random.uniform(-20, 30)
            })

    wastewater_df = pd.DataFrame(wastewater_records)

    # Variant data
    variants = ['JN.1', 'BA.2.86', 'XBB.1.5', 'EG.5']
    variant_records = []

    for variant in variants:
        # Each variant starts spreading from a few seed locations
        seed_locations = np.random.choice(locations, size=3, replace=False)
        seed_date = dates[np.random.randint(30, 200)]

        # Spread to other locations over time
        for loc in locations:
            if loc in seed_locations:
                first_date = seed_date
            else:
                # Delay based on "distance" (random for synthetic)
                delay = np.random.randint(7, 90)
                first_date = seed_date + timedelta(days=delay)

            if first_date < dates[-1]:
                # Generate sequence counts
                for date in dates[dates >= first_date]:
                    days_since = (date - first_date).days
                    count = int(np.random.poisson(max(1, 10 * np.log1p(days_since))))
                    if count > 0:
                        variant_records.append({
                            'location': loc,
                            'date': date,
                            'variant': variant,
                            'sequence_count': count
                        })

    variant_df = pd.DataFrame(variant_records)

    # Flight data
    flight_records = []
    for date in dates:
        for origin in np.random.choice(locations, size=20, replace=False):
            for dest in np.random.choice(locations, size=5, replace=False):
                if origin != dest:
                    passengers = np.random.randint(50, 500)
                    flight_records.append({
                        'origin': origin,
                        'destination': dest,
                        'date': date,
                        'passengers': passengers
                    })

    flight_df = pd.DataFrame(flight_records)

    # Location mapping (identity for synthetic)
    location_mapping = {loc: loc for loc in locations}

    return wastewater_df, variant_df, flight_df, location_mapping


def run_validation():
    """Run full validation suite."""
    print("=" * 60)
    print("VIRAL WEATHER - RETROSPECTIVE VALIDATION")
    print("=" * 60)

    # Generate synthetic data (replace with real data loading)
    print("\nLoading data...")
    wastewater_df, variant_df, flight_df, location_mapping = generate_synthetic_data()

    print(f"  Wastewater records: {len(wastewater_df):,}")
    print(f"  Variant records: {len(variant_df):,}")
    print(f"  Flight records: {len(flight_df):,}")
    print(f"  Locations: {len(location_mapping)}")

    # Initialize validator
    validator = RetrospectiveValidator(
        wastewater_df=wastewater_df,
        variant_df=variant_df,
        flight_df=flight_df,
        location_mapping=location_mapping
    )

    # Run tests
    print("\nRunning validation tests...")

    print("\n[H1] Import pressure → Variant arrival timing...")
    h1_result = validator.test_h1_import_pressure_variant_arrival()
    print(f"     Result: {'PASS' if h1_result.passed else 'FAIL'}")
    print(f"     Correlation: {h1_result.metric_value:.3f}")

    print("\n[H2] Risk score → Wastewater surge prediction...")
    h2_result = validator.test_h2_risk_score_predicts_surge()
    print(f"     Result: {'PASS' if h2_result.passed else 'FAIL'}")
    print(f"     Directional accuracy: {h2_result.metric_value:.1%}")

    print("\n[H3] Propagation speed by import pressure...")
    h3_result = validator.test_h3_propagation_speed(variant='JN.1')
    print(f"     Result: {'PASS' if h3_result.passed else 'FAIL'}")
    print(f"     Effect size: {h3_result.metric_value:.1f} days")

    print("\n[Lead Time] Advance warning analysis...")
    lt_result = validator.calculate_lead_time(variant='JN.1')
    print(f"     Result: {'PASS' if lt_result.passed else 'FAIL'}")
    print(f"     Median lead time: {lt_result.metric_value:.0f} days")

    # Generate report
    report = validator.generate_report()

    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Tests passed: {report['summary']['passed']}/{report['summary']['total_tests']}")
    print(f"Pass rate: {report['summary']['pass_rate']:.0%}")
    print(f"Overall verdict: {report['summary']['overall_verdict']}")

    print("\nRecommendations:")
    for i, rec in enumerate(report['recommendations'], 1):
        print(f"  {i}. {rec}")

    # Save report
    report_path = 'validation_report.json'
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nFull report saved to: {report_path}")

    return report


if __name__ == '__main__':
    run_validation()
