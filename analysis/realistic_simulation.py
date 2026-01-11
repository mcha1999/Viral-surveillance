"""
Realistic Epidemiological Simulation
=====================================

Creates synthetic data that mirrors real-world patterns from
documented variant waves (JN.1, BA.2.86, XBB.1.5).

Based on:
- Published CDC NWSS wastewater trends (2023-2024)
- Nextstrain variant tracking data
- Known US domestic flight patterns

This provides a more realistic test of the validation framework
than purely random synthetic data.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from scipy import stats
import json


class RealisticEpiSimulator:
    """
    Generates epidemiologically realistic data based on observed patterns.
    """

    def __init__(self, seed: int = 42):
        np.random.seed(seed)

        # US state populations (millions) - top 20 states
        self.states = {
            'California': {'pop': 39.5, 'hubs': ['LAX', 'SFO'], 'lat': 36.7, 'connectivity': 1.0},
            'Texas': {'pop': 29.5, 'hubs': ['DFW', 'IAH'], 'lat': 31.0, 'connectivity': 0.9},
            'Florida': {'pop': 22.2, 'hubs': ['MIA', 'MCO'], 'lat': 27.6, 'connectivity': 0.95},
            'New York': {'pop': 19.3, 'hubs': ['JFK', 'LGA'], 'lat': 42.9, 'connectivity': 1.0},
            'Pennsylvania': {'pop': 13.0, 'hubs': ['PHL'], 'lat': 41.2, 'connectivity': 0.7},
            'Illinois': {'pop': 12.6, 'hubs': ['ORD'], 'lat': 40.6, 'connectivity': 0.9},
            'Ohio': {'pop': 11.8, 'hubs': ['CLE'], 'lat': 40.4, 'connectivity': 0.6},
            'Georgia': {'pop': 10.9, 'hubs': ['ATL'], 'lat': 32.2, 'connectivity': 0.95},
            'North Carolina': {'pop': 10.6, 'hubs': ['CLT'], 'lat': 35.8, 'connectivity': 0.7},
            'Michigan': {'pop': 10.0, 'hubs': ['DTW'], 'lat': 44.3, 'connectivity': 0.65},
            'New Jersey': {'pop': 9.3, 'hubs': ['EWR'], 'lat': 40.1, 'connectivity': 0.8},
            'Virginia': {'pop': 8.6, 'hubs': ['IAD'], 'lat': 37.4, 'connectivity': 0.75},
            'Washington': {'pop': 7.7, 'hubs': ['SEA'], 'lat': 47.8, 'connectivity': 0.8},
            'Arizona': {'pop': 7.3, 'hubs': ['PHX'], 'lat': 34.0, 'connectivity': 0.75},
            'Massachusetts': {'pop': 7.0, 'hubs': ['BOS'], 'lat': 42.4, 'connectivity': 0.85},
            'Tennessee': {'pop': 7.0, 'hubs': ['BNA'], 'lat': 35.5, 'connectivity': 0.6},
            'Indiana': {'pop': 6.8, 'hubs': ['IND'], 'lat': 40.3, 'connectivity': 0.55},
            'Missouri': {'pop': 6.2, 'hubs': ['STL'], 'lat': 37.9, 'connectivity': 0.6},
            'Maryland': {'pop': 6.2, 'hubs': ['BWI'], 'lat': 39.0, 'connectivity': 0.7},
            'Colorado': {'pop': 5.8, 'hubs': ['DEN'], 'lat': 39.0, 'connectivity': 0.8},
        }

        # Variant characteristics based on real data
        self.variants = {
            'XBB.1.5': {
                'emergence_date': '2022-10-01',
                'peak_date': '2023-02-15',
                'origin_state': 'New York',
                'transmissibility': 1.0,  # baseline
                'spread_rate': 0.08,  # daily growth rate at peak
            },
            'EG.5': {
                'emergence_date': '2023-04-01',
                'peak_date': '2023-08-15',
                'origin_state': 'California',
                'transmissibility': 1.1,
                'spread_rate': 0.06,
            },
            'BA.2.86': {
                'emergence_date': '2023-07-15',
                'peak_date': '2023-11-01',
                'origin_state': 'New York',
                'transmissibility': 1.15,
                'spread_rate': 0.07,
            },
            'JN.1': {
                'emergence_date': '2023-09-01',
                'peak_date': '2024-01-15',
                'origin_state': 'Massachusetts',
                'transmissibility': 1.3,
                'spread_rate': 0.10,
            },
        }

    def generate_wastewater_data(
        self,
        start_date: str = '2023-01-01',
        end_date: str = '2024-06-30'
    ) -> pd.DataFrame:
        """
        Generate realistic wastewater surveillance data.

        Patterns based on:
        - Seasonal variation (winter peaks)
        - Variant wave dynamics
        - Regional spread patterns
        """
        print("Generating realistic wastewater data...")

        dates = pd.date_range(start=start_date, end=end_date, freq='W')  # Weekly
        records = []

        for state, info in self.states.items():
            # Base viral load varies by population density proxy
            base_load = 5000 * (info['pop'] / 10) ** 0.5

            for date in dates:
                # Seasonal component (higher in winter)
                day_of_year = date.dayofyear
                seasonal = 1 + 0.4 * np.cos(2 * np.pi * (day_of_year - 15) / 365)

                # Variant wave contributions
                wave_contribution = 0
                for variant, v_info in self.variants.items():
                    emergence = pd.Timestamp(v_info['emergence_date'])
                    peak = pd.Timestamp(v_info['peak_date'])

                    if date >= emergence:
                        # Time since emergence
                        days_since = (date - emergence).days

                        # Logistic growth to peak, then decline
                        peak_days = (peak - emergence).days
                        if days_since <= peak_days:
                            # Growth phase
                            growth = 1 / (1 + np.exp(-0.05 * (days_since - peak_days/2)))
                        else:
                            # Decline phase
                            decline_days = days_since - peak_days
                            growth = np.exp(-0.02 * decline_days)

                        # State-specific delay based on distance from origin
                        origin = v_info['origin_state']
                        if state == origin:
                            delay_factor = 1.0
                        else:
                            # Delay proportional to "distance" (latitude difference as proxy)
                            lat_diff = abs(info['lat'] - self.states[origin]['lat'])
                            delay_factor = max(0, 1 - lat_diff / 30)

                        wave_contribution += growth * v_info['transmissibility'] * delay_factor * 0.3

                # Combine components
                viral_load = base_load * seasonal * (1 + wave_contribution)

                # Add noise
                viral_load *= np.random.lognormal(0, 0.15)

                # Calculate week-over-week change
                pct_change = np.random.normal(wave_contribution * 20, 10)

                records.append({
                    'location_id': state,
                    'date': date,
                    'viral_load': viral_load,
                    'pct_change_weekly': pct_change,
                    'population': info['pop'] * 1e6
                })

        df = pd.DataFrame(records)
        print(f"  Generated {len(df)} wastewater records")
        print(f"  States: {df['location_id'].nunique()}")
        print(f"  Date range: {df['date'].min()} to {df['date'].max()}")

        return df

    def generate_variant_data(
        self,
        start_date: str = '2023-01-01',
        end_date: str = '2024-06-30'
    ) -> pd.DataFrame:
        """
        Generate realistic variant sequence data.

        Simulates:
        - Geographic spread from origin state
        - Correlation with flight connectivity
        - Realistic detection delays
        """
        print("Generating realistic variant data...")

        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        records = []

        for variant, v_info in self.variants.items():
            emergence = pd.Timestamp(v_info['emergence_date'])
            origin = v_info['origin_state']

            if emergence < pd.Timestamp(start_date):
                emergence = pd.Timestamp(start_date)

            # Calculate arrival time for each state
            for state, s_info in self.states.items():
                if state == origin:
                    arrival_date = emergence
                else:
                    # Arrival delay based on connectivity and distance
                    connectivity = s_info['connectivity']
                    lat_distance = abs(s_info['lat'] - self.states[origin]['lat'])

                    # Higher connectivity = faster arrival
                    # Closer states = faster arrival
                    base_delay = 7 + lat_distance / 2  # days
                    delay = int(base_delay / connectivity)

                    # Add randomness
                    delay = max(3, int(delay * np.random.uniform(0.7, 1.3)))
                    arrival_date = emergence + timedelta(days=delay)

                if arrival_date > pd.Timestamp(end_date):
                    continue

                # Generate sequence counts over time
                for date in dates:
                    if date < arrival_date:
                        continue

                    days_since_arrival = (date - arrival_date).days

                    # Growth curve (logistic)
                    carrying_capacity = s_info['pop'] * 10  # Max sequences
                    growth_rate = v_info['spread_rate']
                    prevalence = carrying_capacity / (1 + np.exp(-growth_rate * (days_since_arrival - 60)))

                    # Sampling probability (sequencing is sparse)
                    sample_rate = 0.001

                    # Expected sequences
                    expected_sequences = prevalence * sample_rate

                    # Add noise and sample
                    if expected_sequences > 0.1:
                        sequences = np.random.poisson(max(1, expected_sequences))
                        if sequences > 0:
                            records.append({
                                'location': state,
                                'date': date,
                                'variant': variant,
                                'sequence_count': sequences
                            })

        df = pd.DataFrame(records)

        # Aggregate to weekly for cleaner data
        df['week'] = df['date'].dt.to_period('W').dt.start_time
        df = df.groupby(['location', 'week', 'variant'])['sequence_count'].sum().reset_index()
        df = df.rename(columns={'week': 'date'})

        print(f"  Generated {len(df)} variant records")
        print(f"  Variants: {df['variant'].unique().tolist()}")
        print(f"  States: {df['location'].nunique()}")

        return df

    def generate_flight_data(
        self,
        start_date: str = '2023-01-01',
        end_date: str = '2024-06-30'
    ) -> pd.DataFrame:
        """
        Generate realistic domestic flight data.

        Based on:
        - Major hub connectivity
        - Population-weighted passenger flows
        - Seasonal travel patterns
        """
        print("Generating realistic flight data...")

        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        records = []

        states = list(self.states.keys())

        for date in dates:
            # Seasonal travel factor (higher in summer, holidays)
            day_of_year = date.dayofyear
            seasonal = 1 + 0.2 * np.sin(2 * np.pi * (day_of_year - 180) / 365)

            # Holiday boost
            if date.month == 12 and date.day >= 20:
                seasonal *= 1.5
            elif date.month == 11 and 22 <= date.day <= 28:
                seasonal *= 1.4

            for origin in states:
                for dest in states:
                    if origin == dest:
                        continue

                    # Passenger estimate based on hub connectivity and population
                    o_info = self.states[origin]
                    d_info = self.states[dest]

                    # Gravity model
                    base_flow = (o_info['pop'] * d_info['pop']) ** 0.5 * 100
                    connectivity_factor = (o_info['connectivity'] + d_info['connectivity']) / 2

                    passengers = int(base_flow * connectivity_factor * seasonal)

                    # Add daily noise
                    passengers = max(50, int(passengers * np.random.uniform(0.8, 1.2)))

                    records.append({
                        'origin': origin,
                        'destination': dest,
                        'date': date,
                        'passengers': passengers
                    })

        df = pd.DataFrame(records)
        print(f"  Generated {len(df)} flight records")
        print(f"  Routes: {df.groupby(['origin', 'destination']).ngroups}")

        return df

    def generate_all(
        self,
        start_date: str = '2023-01-01',
        end_date: str = '2024-06-30'
    ) -> tuple:
        """Generate all datasets."""
        print("=" * 60)
        print("GENERATING REALISTIC EPIDEMIOLOGICAL DATA")
        print("=" * 60)
        print(f"Period: {start_date} to {end_date}")
        print(f"States: {len(self.states)}")
        print(f"Variants: {list(self.variants.keys())}")
        print()

        wastewater = self.generate_wastewater_data(start_date, end_date)
        variants = self.generate_variant_data(start_date, end_date)
        flights = self.generate_flight_data(start_date, end_date)

        # Create location mapping (identity for states)
        location_mapping = {s: s for s in self.states.keys()}

        return wastewater, variants, flights, location_mapping


def run_validation_with_realistic_data():
    """Run the full validation with realistic simulated data."""
    from retrospective_validation import RetrospectiveValidator

    # Generate data
    simulator = RealisticEpiSimulator(seed=42)
    wastewater_df, variant_df, flight_df, location_mapping = simulator.generate_all(
        start_date='2023-01-01',
        end_date='2024-06-30'
    )

    print("\n" + "=" * 60)
    print("RUNNING VALIDATION ON REALISTIC DATA")
    print("=" * 60)

    # Initialize validator
    validator = RetrospectiveValidator(
        wastewater_df=wastewater_df,
        variant_df=variant_df,
        flight_df=flight_df,
        location_mapping=location_mapping
    )

    # Run tests
    print("\n[H1] Import pressure → Variant arrival timing...")
    h1_result = validator.test_h1_import_pressure_variant_arrival(
        variants_to_test=['JN.1', 'BA.2.86', 'EG.5'],
        min_locations=5
    )
    status = '✓ PASS' if h1_result.passed else '✗ FAIL'
    print(f"     {status}")
    print(f"     Correlation: {h1_result.metric_value:.3f}")
    if 'variants_tested' in h1_result.details:
        for v, d in h1_result.details['variants_tested'].items():
            print(f"       {v}: r={d['correlation']:.3f}, p={d['p_value']:.4f}")

    print("\n[H2] Risk score → Wastewater surge prediction...")
    h2_result = validator.test_h2_risk_score_predicts_surge(
        forecast_horizon_days=14,
        locations=list(location_mapping.keys())[:15]
    )
    status = '✓ PASS' if h2_result.passed else '✗ FAIL'
    print(f"     {status}")
    print(f"     Directional accuracy: {h2_result.metric_value:.1%}")
    if 'rmse' in h2_result.details:
        print(f"     RMSE: {h2_result.details['rmse']:.2f} (baseline: {h2_result.details['baseline_rmse_no_change']:.2f})")
        print(f"     Improvement: {h2_result.details['improvement_vs_baseline']:.1f}%")

    print("\n[H3] Propagation speed by import pressure...")
    h3_result = validator.test_h3_propagation_speed(variant='JN.1')
    status = '✓ PASS' if h3_result.passed else '✗ FAIL'
    print(f"     {status}")
    if h3_result.details.get('high_pressure_median_days'):
        print(f"     High-pressure locations: {h3_result.details['high_pressure_median_days']:.0f} days to 50%")
        print(f"     Low-pressure locations: {h3_result.details['low_pressure_median_days']:.0f} days to 50%")
        print(f"     Effect size: {h3_result.details['effect_size_days']:.0f} days faster")
    else:
        print(f"     {h3_result.details.get('error', 'Unknown error')}")

    print("\n[Lead Time] Advance warning analysis...")
    lt_result = validator.calculate_lead_time(variant='JN.1', risk_threshold=40)
    status = '✓ PASS' if lt_result.passed else '✗ FAIL'
    print(f"     {status}")
    if lt_result.details.get('median_lead_time'):
        print(f"     Median lead time: {lt_result.details['median_lead_time']:.0f} days")
        print(f"     Locations warned: {lt_result.details['pct_locations_warned']:.0f}%")
    else:
        print(f"     {lt_result.details.get('error', 'Unknown error')}")

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
    with open('validation_report_realistic.json', 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nFull report saved to: validation_report_realistic.json")

    return report


if __name__ == '__main__':
    run_validation_with_realistic_data()
