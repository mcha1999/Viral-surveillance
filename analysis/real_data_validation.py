"""
Real Data Validation Framework
==============================

Fetches actual historical data from:
- CDC NWSS (US wastewater surveillance)
- EU Wastewater Observatory (European data)
- GISAID/Nextstrain (variant sequences - metadata only)
- AviationStack (flight data)

Then runs retrospective validation to verify model hypotheses.

Usage:
    python analysis/real_data_validation.py --output validation_results_real.json
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import hashlib

import pandas as pd
import numpy as np
from scipy import stats
import httpx

# Data source configurations
CDC_NWSS_ENDPOINT = "https://data.cdc.gov/resource/2ew6-ywp6.json"
CDC_NWSS_LEGACY_ENDPOINT = "https://data.cdc.gov/resource/g653-rqe2.json"

EU_OBSERVATORY_BASE = "https://wastewater-observatory.jrc.ec.europa.eu"

RKI_GITHUB_URL = "https://raw.githubusercontent.com/robert-koch-institut/Abwassersurveillance_AMELAG/main/Abwassersurveillance_AMELAG.csv"

# Nextstrain open data
NEXTSTRAIN_METADATA_URL = "https://data.nextstrain.org/files/ncov/open/metadata.tsv.zst"
NEXTSTRAIN_CLADES_URL = "https://data.nextstrain.org/files/workflows/forecasts-ncov/gisaid/nextstrain_clades/global/latest_results.json"


class RealDataFetcher:
    """Fetches real surveillance data from public APIs."""

    def __init__(self, cache_dir: str = "data/cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.client = httpx.Client(timeout=120.0, follow_redirects=True)

    def _cache_path(self, key: str) -> str:
        """Generate cache file path."""
        hash_key = hashlib.md5(key.encode()).hexdigest()[:12]
        return os.path.join(self.cache_dir, f"{hash_key}.json")

    def _load_cache(self, key: str, max_age_hours: int = 24) -> Optional[dict]:
        """Load data from cache if fresh enough."""
        path = self._cache_path(key)
        if os.path.exists(path):
            mtime = datetime.fromtimestamp(os.path.getmtime(path))
            age = datetime.now() - mtime
            if age < timedelta(hours=max_age_hours):
                with open(path) as f:
                    return json.load(f)
        return None

    def _save_cache(self, key: str, data: dict):
        """Save data to cache."""
        path = self._cache_path(key)
        with open(path, 'w') as f:
            json.dump(data, f)

    def fetch_cdc_nwss(
        self,
        start_date: str = "2023-01-01",
        end_date: Optional[str] = None,
        limit: int = 50000
    ) -> pd.DataFrame:
        """
        Fetch CDC NWSS wastewater data.

        Data fields:
        - wwtp_id: Wastewater treatment plant ID
        - reporting_jurisdiction: State
        - sample_collect_date: Collection date
        - pcr_conc_smoothed: Smoothed SARS-CoV-2 concentration
        - percentile: National percentile ranking
        - ptc_15d: 15-day percent change
        - detect_prop_15d: Detection proportion over 15 days
        - population_served: Population covered by this site
        """
        cache_key = f"cdc_nwss_{start_date}_{end_date}_{limit}"
        cached = self._load_cache(cache_key, max_age_hours=12)
        if cached:
            print(f"[CDC NWSS] Using cached data ({len(cached)} records)")
            return pd.DataFrame(cached)

        print(f"[CDC NWSS] Fetching data from {start_date}...")

        # Build query with SoQL
        params = {
            "$limit": limit,
            "$order": "sample_collect_date DESC",
            "$where": f"sample_collect_date >= '{start_date}'"
        }
        if end_date:
            params["$where"] += f" AND sample_collect_date <= '{end_date}'"

        try:
            # Try new endpoint first
            response = self.client.get(CDC_NWSS_ENDPOINT, params=params)
            if response.status_code == 404:
                # Fall back to legacy endpoint
                print("[CDC NWSS] New endpoint not found, trying legacy...")
                response = self.client.get(CDC_NWSS_LEGACY_ENDPOINT, params=params)

            response.raise_for_status()
            data = response.json()

            print(f"[CDC NWSS] Fetched {len(data)} records")
            self._save_cache(cache_key, data)

            return pd.DataFrame(data)

        except httpx.HTTPError as e:
            print(f"[CDC NWSS] Error fetching data: {e}")
            return pd.DataFrame()

    def fetch_rki_germany(self) -> pd.DataFrame:
        """
        Fetch German RKI wastewater surveillance data.

        AMELAG (Abwassermonitoring für die epidemiologische Lagebewertung)
        provides state-level wastewater data.
        """
        cache_key = "rki_amelag_latest"
        cached = self._load_cache(cache_key, max_age_hours=24)
        if cached:
            print(f"[RKI] Using cached data ({len(cached)} records)")
            return pd.DataFrame(cached)

        print("[RKI] Fetching German wastewater data...")

        try:
            response = self.client.get(RKI_GITHUB_URL)
            response.raise_for_status()

            # Parse CSV
            from io import StringIO
            df = pd.read_csv(StringIO(response.text), sep=";")

            print(f"[RKI] Fetched {len(df)} records")

            # Cache as list of dicts
            self._save_cache(cache_key, df.to_dict('records'))

            return df

        except Exception as e:
            print(f"[RKI] Error fetching data: {e}")
            return pd.DataFrame()

    def fetch_nextstrain_clades(self) -> Dict:
        """
        Fetch Nextstrain variant/clade frequency data.

        This provides global variant prevalence over time.
        """
        cache_key = "nextstrain_clades_latest"
        cached = self._load_cache(cache_key, max_age_hours=24)
        if cached:
            print("[Nextstrain] Using cached clade data")
            return cached

        print("[Nextstrain] Fetching variant frequency data...")

        try:
            response = self.client.get(NEXTSTRAIN_CLADES_URL)
            response.raise_for_status()
            data = response.json()

            print(f"[Nextstrain] Fetched clade data for {len(data.get('locations', []))} locations")
            self._save_cache(cache_key, data)

            return data

        except Exception as e:
            print(f"[Nextstrain] Error fetching data: {e}")
            return {}

    def close(self):
        self.client.close()


class RealDataValidator:
    """
    Validates risk model hypotheses using real data.
    """

    def __init__(self, fetcher: RealDataFetcher):
        self.fetcher = fetcher
        self.results = []

    def validate_all(self) -> Dict:
        """Run all validation tests."""
        print("\n" + "="*60)
        print("REAL DATA VALIDATION")
        print("="*60 + "\n")

        # Fetch data
        cdc_df = self.fetcher.fetch_cdc_nwss(start_date="2023-06-01")
        rki_df = self.fetcher.fetch_rki_germany()
        nextstrain_data = self.fetcher.fetch_nextstrain_clades()

        # Data availability summary
        data_summary = {
            "cdc_nwss_records": len(cdc_df),
            "cdc_nwss_sites": cdc_df['wwtp_id'].nunique() if 'wwtp_id' in cdc_df.columns else 0,
            "cdc_nwss_states": cdc_df['reporting_jurisdiction'].nunique() if 'reporting_jurisdiction' in cdc_df.columns else 0,
            "rki_records": len(rki_df),
            "nextstrain_available": bool(nextstrain_data),
        }

        print("\n--- Data Summary ---")
        for key, value in data_summary.items():
            print(f"  {key}: {value}")

        # Run validations
        results = []

        if len(cdc_df) > 0:
            results.append(self._validate_wastewater_state_correlation(cdc_df))
            results.append(self._validate_trend_consistency(cdc_df))
            results.append(self._validate_geographic_spread_pattern(cdc_df))
            results.append(self._validate_velocity_prediction(cdc_df))
        else:
            print("\n[WARNING] No CDC data available - skipping US validations")

        if len(rki_df) > 0:
            results.append(self._validate_eu_wastewater_trends(rki_df))

        # Compile report
        passed = sum(1 for r in results if r.get('passed', False))
        total = len(results)

        report = {
            "summary": {
                "total_tests": total,
                "passed": passed,
                "failed": total - passed,
                "pass_rate": passed / total if total > 0 else 0,
                "overall_verdict": "VALIDATED" if passed >= total * 0.6 else "NEEDS_WORK",
                "generated_at": datetime.utcnow().isoformat(),
                "data_sources": data_summary,
            },
            "results": results,
            "recommendations": self._generate_recommendations(results),
        }

        return report

    def _validate_wastewater_state_correlation(self, df: pd.DataFrame) -> Dict:
        """
        Test H1: High-connectivity states should show correlated wastewater trends.

        Hypothesis: States with major airports (NY, CA, TX, FL, IL, GA) should
        show correlated viral load patterns due to travel connectivity.
        """
        print("\n--- H1: Interstate Wastewater Correlation ---")

        # High-connectivity states
        hub_states = ['NY', 'CA', 'TX', 'FL', 'IL', 'GA']

        # Get state-level aggregated data
        if 'reporting_jurisdiction' not in df.columns:
            return {
                "hypothesis": "H1: Interstate wastewater correlation",
                "test": "Pairwise Spearman correlation",
                "passed": False,
                "details": {"error": "Missing 'reporting_jurisdiction' column"}
            }

        # Parse dates and aggregate by state and week
        df = df.copy()
        try:
            df['date'] = pd.to_datetime(df['sample_collect_date'])
        except:
            df['date'] = pd.to_datetime(df.get('date_start', df.get('date')))

        df['week'] = df['date'].dt.to_period('W')

        # Get metric column
        metric_col = None
        for col in ['pcr_conc_smoothed', 'percentile', 'detect_prop_15d', 'normalized_score']:
            if col in df.columns:
                metric_col = col
                break

        if not metric_col:
            return {
                "hypothesis": "H1: Interstate wastewater correlation",
                "test": "Pairwise Spearman correlation",
                "passed": False,
                "details": {"error": "No suitable metric column found"}
            }

        # Convert to numeric
        df[metric_col] = pd.to_numeric(df[metric_col], errors='coerce')

        # Aggregate by state and week
        state_weekly = df.groupby(['reporting_jurisdiction', 'week'])[metric_col].mean().reset_index()
        state_pivot = state_weekly.pivot(index='week', columns='reporting_jurisdiction', values=metric_col)

        # Filter to hub states that exist
        available_hubs = [s for s in hub_states if s in state_pivot.columns]

        if len(available_hubs) < 2:
            return {
                "hypothesis": "H1: Interstate wastewater correlation",
                "test": "Pairwise Spearman correlation",
                "passed": False,
                "details": {"error": f"Only {len(available_hubs)} hub states available"}
            }

        hub_data = state_pivot[available_hubs].dropna()

        # Calculate pairwise correlations
        correlations = []
        pairs_tested = []

        for i, s1 in enumerate(available_hubs):
            for s2 in available_hubs[i+1:]:
                data1 = hub_data[s1].values
                data2 = hub_data[s2].values

                if len(data1) >= 10:
                    corr, pval = stats.spearmanr(data1, data2)
                    correlations.append(corr)
                    pairs_tested.append({
                        "pair": f"{s1}-{s2}",
                        "correlation": round(corr, 3),
                        "p_value": round(pval, 6),
                        "significant": pval < 0.05
                    })

        avg_correlation = np.mean(correlations) if correlations else 0
        significant_pairs = sum(1 for p in pairs_tested if p['significant'])

        # Threshold: Average correlation > 0.3 and >50% pairs significant
        passed = avg_correlation > 0.3 and significant_pairs > len(pairs_tested) / 2

        result = {
            "hypothesis": "H1: Interstate wastewater correlation (hub states)",
            "test": "Pairwise Spearman correlation",
            "metric": "Average correlation across hub state pairs",
            "value": round(avg_correlation, 3),
            "passed": passed,
            "details": {
                "hub_states_tested": available_hubs,
                "weeks_of_data": len(hub_data),
                "pairs_tested": len(pairs_tested),
                "significant_pairs": significant_pairs,
                "pair_details": pairs_tested[:5],  # Top 5 for brevity
                "interpretation": f"Hub states show {'correlated' if passed else 'uncorrelated'} wastewater trends (r={avg_correlation:.2f})"
            }
        }

        print(f"  Average correlation: {avg_correlation:.3f}")
        print(f"  Significant pairs: {significant_pairs}/{len(pairs_tested)}")
        print(f"  Result: {'PASSED' if passed else 'FAILED'}")

        return result

    def _validate_trend_consistency(self, df: pd.DataFrame) -> Dict:
        """
        Test H2: Velocity signals should predict future wastewater levels.

        Uses percent change (ptc_15d) to predict next week's levels.
        """
        print("\n--- H2: Trend/Velocity Prediction Accuracy ---")

        df = df.copy()

        # Find velocity and level columns
        velocity_col = None
        for col in ['ptc_15d', 'percent_change', 'trend']:
            if col in df.columns:
                velocity_col = col
                break

        level_col = None
        for col in ['percentile', 'pcr_conc_smoothed', 'detect_prop_15d']:
            if col in df.columns:
                level_col = col
                break

        if not velocity_col or not level_col:
            return {
                "hypothesis": "H2: Velocity predicts future levels",
                "test": "Directional accuracy",
                "passed": False,
                "details": {"error": f"Missing columns: velocity={velocity_col}, level={level_col}"}
            }

        # Parse dates
        try:
            df['date'] = pd.to_datetime(df['sample_collect_date'])
        except:
            df['date'] = pd.to_datetime(df.get('date_start', df.get('date')))

        # Convert to numeric
        df[velocity_col] = pd.to_numeric(df[velocity_col], errors='coerce')
        df[level_col] = pd.to_numeric(df[level_col], errors='coerce')

        # Aggregate by state and week
        df['week'] = df['date'].dt.to_period('W')

        if 'reporting_jurisdiction' in df.columns:
            group_cols = ['reporting_jurisdiction', 'week']
        else:
            group_cols = ['week']

        weekly = df.groupby(group_cols).agg({
            velocity_col: 'mean',
            level_col: 'mean'
        }).reset_index()

        # For each state, check if positive velocity predicts increase
        correct_predictions = 0
        total_predictions = 0

        if 'reporting_jurisdiction' in weekly.columns:
            for state in weekly['reporting_jurisdiction'].unique():
                state_data = weekly[weekly['reporting_jurisdiction'] == state].sort_values('week')

                for i in range(len(state_data) - 1):
                    velocity = state_data.iloc[i][velocity_col]
                    current_level = state_data.iloc[i][level_col]
                    next_level = state_data.iloc[i + 1][level_col]

                    if pd.notna(velocity) and pd.notna(current_level) and pd.notna(next_level):
                        predicted_direction = 1 if velocity > 0 else -1 if velocity < 0 else 0
                        actual_direction = 1 if next_level > current_level else -1 if next_level < current_level else 0

                        if predicted_direction == actual_direction:
                            correct_predictions += 1
                        total_predictions += 1

        accuracy = correct_predictions / total_predictions if total_predictions > 0 else 0

        # Threshold: Better than random (50%)
        passed = accuracy > 0.55

        result = {
            "hypothesis": "H2: Velocity predicts future wastewater levels",
            "test": "Directional accuracy (1-week ahead)",
            "metric": "Proportion of correct directional predictions",
            "value": round(accuracy, 3),
            "passed": passed,
            "details": {
                "correct_predictions": correct_predictions,
                "total_predictions": total_predictions,
                "baseline_random": 0.5,
                "improvement_vs_random": round((accuracy - 0.5) * 100, 1),
                "interpretation": f"Velocity signal predicts direction correctly {accuracy*100:.1f}% of time"
            }
        }

        print(f"  Directional accuracy: {accuracy:.1%}")
        print(f"  Improvement vs random: {(accuracy - 0.5)*100:.1f}%")
        print(f"  Result: {'PASSED' if passed else 'FAILED'}")

        return result

    def _validate_geographic_spread_pattern(self, df: pd.DataFrame) -> Dict:
        """
        Test H3: Geographic spread pattern follows connectivity.

        When a surge starts, high-connectivity states should show
        elevated levels before low-connectivity states.
        """
        print("\n--- H3: Geographic Spread Pattern ---")

        # Connectivity ranking (based on airport passengers)
        connectivity_rank = {
            'GA': 1,   # ATL - busiest airport
            'CA': 2,   # LAX + SFO
            'TX': 3,   # DFW + IAH
            'IL': 4,   # ORD
            'CO': 5,   # DEN
            'NY': 6,   # JFK + LGA + EWR (shared with NJ)
            'FL': 7,   # MIA + MCO
            'NC': 8,   # CLT
            'NV': 9,   # LAS
            'AZ': 10,  # PHX
            # Lower connectivity states
            'WY': 45,
            'VT': 46,
            'SD': 47,
            'ND': 48,
            'MT': 49,
            'WV': 50,
        }

        if 'reporting_jurisdiction' not in df.columns:
            return {
                "hypothesis": "H3: Geographic spread follows connectivity",
                "test": "Lead time correlation",
                "passed": False,
                "details": {"error": "Missing state column"}
            }

        df = df.copy()
        try:
            df['date'] = pd.to_datetime(df['sample_collect_date'])
        except:
            df['date'] = pd.to_datetime(df.get('date_start'))

        # Find level column
        level_col = None
        for col in ['percentile', 'pcr_conc_smoothed', 'detect_prop_15d']:
            if col in df.columns:
                level_col = col
                break

        if not level_col:
            return {
                "hypothesis": "H3: Geographic spread follows connectivity",
                "test": "Surge detection timing",
                "passed": False,
                "details": {"error": "No level metric found"}
            }

        df[level_col] = pd.to_numeric(df[level_col], errors='coerce')

        # Identify surge periods (national 75th percentile)
        national_75pct = df[level_col].quantile(0.75)

        # For each state, find first date above 75th percentile
        first_surge_date = {}
        for state in df['reporting_jurisdiction'].unique():
            state_df = df[df['reporting_jurisdiction'] == state]
            above_threshold = state_df[state_df[level_col] >= national_75pct]
            if len(above_threshold) > 0:
                first_date = above_threshold['date'].min()
                first_surge_date[state] = first_date

        # Calculate correlation between connectivity rank and surge timing
        states_with_both = [s for s in first_surge_date.keys() if s in connectivity_rank]

        if len(states_with_both) < 10:
            return {
                "hypothesis": "H3: Geographic spread follows connectivity",
                "test": "Surge timing vs connectivity",
                "passed": False,
                "details": {"error": f"Only {len(states_with_both)} states with both data points"}
            }

        ranks = [connectivity_rank[s] for s in states_with_both]
        surge_days = [(first_surge_date[s] - min(first_surge_date.values())).days for s in states_with_both]

        corr, pval = stats.spearmanr(ranks, surge_days)

        # Negative correlation expected (low rank = high connectivity = early surge)
        # But we want high connectivity to be first, so positive correlation with our ranking
        passed = corr > 0.2 and pval < 0.1

        result = {
            "hypothesis": "H3: High connectivity states see surges first",
            "test": "Spearman correlation (connectivity rank vs surge day)",
            "metric": "Correlation coefficient",
            "value": round(corr, 3),
            "p_value": round(pval, 4),
            "passed": passed,
            "details": {
                "states_analyzed": len(states_with_both),
                "earliest_surge": min(first_surge_date.values()).strftime("%Y-%m-%d"),
                "latest_surge": max(first_surge_date.values()).strftime("%Y-%m-%d"),
                "spread_duration_days": (max(first_surge_date.values()) - min(first_surge_date.values())).days,
                "interpretation": f"{'Confirmed' if passed else 'Not confirmed'}: high-connectivity states see surges before low-connectivity states"
            }
        }

        print(f"  Correlation (connectivity vs timing): {corr:.3f} (p={pval:.4f})")
        print(f"  States analyzed: {len(states_with_both)}")
        print(f"  Result: {'PASSED' if passed else 'FAILED'}")

        return result

    def _validate_velocity_prediction(self, df: pd.DataFrame) -> Dict:
        """
        Test H4: Model velocity component matches observed changes.

        Compare calculated velocity from the risk engine formula
        against actual week-over-week changes.
        """
        print("\n--- H4: Velocity Calculation Accuracy ---")

        df = df.copy()

        # Parse dates
        try:
            df['date'] = pd.to_datetime(df['sample_collect_date'])
        except:
            df['date'] = pd.to_datetime(df.get('date_start'))

        # Get both velocity (reported) and raw level
        reported_velocity_col = None
        for col in ['ptc_15d', 'percent_change']:
            if col in df.columns:
                reported_velocity_col = col
                break

        level_col = None
        for col in ['pcr_conc_smoothed', 'percentile']:
            if col in df.columns:
                level_col = col
                break

        if not reported_velocity_col or not level_col:
            return {
                "hypothesis": "H4: Velocity calculation accuracy",
                "test": "Reported vs calculated velocity correlation",
                "passed": False,
                "details": {"error": "Missing required columns"}
            }

        df[reported_velocity_col] = pd.to_numeric(df[reported_velocity_col], errors='coerce')
        df[level_col] = pd.to_numeric(df[level_col], errors='coerce')

        # Calculate our own velocity (7-day change)
        df = df.sort_values(['reporting_jurisdiction', 'date'] if 'reporting_jurisdiction' in df.columns else ['date'])

        if 'reporting_jurisdiction' in df.columns:
            df['calculated_velocity'] = df.groupby('reporting_jurisdiction')[level_col].pct_change(periods=7) * 100
        else:
            df['calculated_velocity'] = df[level_col].pct_change(periods=7) * 100

        # Compare reported vs calculated
        valid = df[[reported_velocity_col, 'calculated_velocity']].dropna()

        if len(valid) < 100:
            return {
                "hypothesis": "H4: Velocity calculation accuracy",
                "test": "Reported vs calculated correlation",
                "passed": False,
                "details": {"error": f"Only {len(valid)} valid comparisons"}
            }

        corr, pval = stats.pearsonr(valid[reported_velocity_col], valid['calculated_velocity'])

        # Also calculate MAE
        mae = np.abs(valid[reported_velocity_col] - valid['calculated_velocity']).mean()

        passed = corr > 0.5

        result = {
            "hypothesis": "H4: Our velocity matches CDC-reported velocity",
            "test": "Pearson correlation",
            "metric": "Correlation between reported and calculated velocity",
            "value": round(corr, 3),
            "p_value": round(pval, 6),
            "passed": passed,
            "details": {
                "n_comparisons": len(valid),
                "mean_absolute_error": round(mae, 2),
                "reported_velocity_mean": round(valid[reported_velocity_col].mean(), 2),
                "calculated_velocity_mean": round(valid['calculated_velocity'].mean(), 2),
                "interpretation": f"Velocity calculations {'align well' if passed else 'diverge'} with CDC methodology (r={corr:.2f})"
            }
        }

        print(f"  Correlation: {corr:.3f}")
        print(f"  MAE: {mae:.2f}%")
        print(f"  Result: {'PASSED' if passed else 'FAILED'}")

        return result

    def _validate_eu_wastewater_trends(self, df: pd.DataFrame) -> Dict:
        """
        Validate German RKI wastewater data follows similar patterns.
        """
        print("\n--- H5: EU Wastewater Data Consistency ---")

        if len(df) == 0:
            return {
                "hypothesis": "H5: EU data follows consistent patterns",
                "test": "Data availability check",
                "passed": False,
                "details": {"error": "No RKI data available"}
            }

        # Check data completeness
        expected_columns = ['datum', 'bundesland', 'viruslast']
        available = [c for c in expected_columns if c in df.columns or any(c in col.lower() for col in df.columns)]

        # Get actual column names (may differ slightly)
        date_col = next((c for c in df.columns if 'datum' in c.lower() or 'date' in c.lower()), None)
        state_col = next((c for c in df.columns if 'bundesland' in c.lower() or 'state' in c.lower() or 'land' in c.lower()), None)
        load_col = next((c for c in df.columns if 'virus' in c.lower() or 'load' in c.lower() or 'conc' in c.lower()), None)

        n_states = df[state_col].nunique() if state_col else 0
        n_weeks = 0

        if date_col:
            try:
                df['parsed_date'] = pd.to_datetime(df[date_col])
                n_weeks = (df['parsed_date'].max() - df['parsed_date'].min()).days // 7
            except:
                pass

        # Pass if we have data for multiple states and weeks
        passed = n_states >= 5 and n_weeks >= 10

        result = {
            "hypothesis": "H5: EU (German) wastewater data is usable",
            "test": "Data availability and completeness",
            "metric": "States × Weeks coverage",
            "value": f"{n_states} states × {n_weeks} weeks",
            "passed": passed,
            "details": {
                "columns_found": list(df.columns),
                "n_records": len(df),
                "n_states": n_states,
                "n_weeks": n_weeks,
                "date_range": f"{df['parsed_date'].min()} to {df['parsed_date'].max()}" if 'parsed_date' in df.columns else "unknown",
                "interpretation": f"German data is {'sufficient' if passed else 'insufficient'} for validation"
            }
        }

        print(f"  States: {n_states}")
        print(f"  Weeks: {n_weeks}")
        print(f"  Records: {len(df)}")
        print(f"  Result: {'PASSED' if passed else 'FAILED'}")

        return result

    def _generate_recommendations(self, results: List[Dict]) -> List[str]:
        """Generate recommendations based on validation results."""
        recommendations = []

        failed = [r for r in results if not r.get('passed', False)]

        for f in failed:
            hypothesis = f.get('hypothesis', '')
            details = f.get('details', {})

            if 'error' in details:
                recommendations.append(f"Fix data issue: {details['error']}")
            elif 'correlation' in hypothesis.lower():
                recommendations.append(
                    f"Review correlation assumptions in {hypothesis}. "
                    f"Actual correlation ({f.get('value', 'N/A')}) may require model recalibration."
                )
            elif 'velocity' in hypothesis.lower():
                recommendations.append(
                    "Velocity prediction is underperforming. Consider: "
                    "1) Adding seasonality factors, "
                    "2) Using exponential smoothing instead of linear, "
                    "3) Incorporating population immunity estimates."
                )
            elif 'geographic' in hypothesis.lower():
                recommendations.append(
                    "Geographic spread pattern not confirmed. "
                    "Import pressure weights may need adjustment based on actual flight data."
                )

        if len(failed) == 0:
            recommendations.append("All tests passed! Consider expanding validation to cover more variants and time periods.")

        return recommendations


def main():
    parser = argparse.ArgumentParser(description="Validate risk model with real data")
    parser.add_argument("--output", default="validation_results_real.json", help="Output file path")
    parser.add_argument("--start-date", default="2023-06-01", help="Start date for data fetch")
    parser.add_argument("--no-cache", action="store_true", help="Disable caching")
    args = parser.parse_args()

    # Create fetcher and validator
    fetcher = RealDataFetcher()
    validator = RealDataValidator(fetcher)

    try:
        # Run validation
        report = validator.validate_all()

        # Print summary
        print("\n" + "="*60)
        print("VALIDATION SUMMARY")
        print("="*60)
        print(f"Tests passed: {report['summary']['passed']}/{report['summary']['total_tests']}")
        print(f"Pass rate: {report['summary']['pass_rate']*100:.1f}%")
        print(f"Verdict: {report['summary']['overall_verdict']}")

        if report['recommendations']:
            print("\nRecommendations:")
            for i, rec in enumerate(report['recommendations'], 1):
                print(f"  {i}. {rec}")

        # Save report
        output_path = os.path.join(os.path.dirname(__file__), '..', args.output)
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        print(f"\nFull report saved to: {output_path}")

    finally:
        fetcher.close()

    return report


if __name__ == "__main__":
    main()
