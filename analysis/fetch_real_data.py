"""
Fetch Real Historical Data for Validation
==========================================

Fetches data from:
1. CDC NWSS (Wastewater surveillance) - via Socrata API
2. Nextstrain (Variant sequences) - via public JSON
3. Flight data - estimates based on major routes

Usage:
    python fetch_real_data.py --output-dir ./data/validation
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os
import gzip
from io import StringIO
import time


class RealDataFetcher:
    """Fetches real historical data from public APIs."""

    def __init__(self, output_dir: str = "./data/validation"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

        # CDC NWSS Socrata endpoint
        self.cdc_endpoint = "https://data.cdc.gov/resource/g653-rqe2.json"

        # Nextstrain metadata (smaller sample file)
        self.nextstrain_metadata = "https://data.nextstrain.org/files/ncov/open/metadata.tsv.gz"
        self.nextstrain_sample = "https://data.nextstrain.org/files/ncov/open/north-america/metadata.tsv.gz"

    def fetch_cdc_nwss(
        self,
        start_date: str = "2023-01-01",
        end_date: str = None,
        limit: int = 50000
    ) -> pd.DataFrame:
        """
        Fetch CDC NWSS wastewater surveillance data.

        Returns DataFrame with:
        - location_id (state + county)
        - date
        - viral_load (normalized SARS-CoV-2 levels)
        - pct_change_weekly
        """
        print("Fetching CDC NWSS wastewater data...")

        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        # Socrata query parameters
        params = {
            "$where": f"date_end >= '{start_date}' AND date_end <= '{end_date}'",
            "$limit": limit,
            "$order": "date_end DESC",
            "$select": "wwtp_jurisdiction,county_names,date_end,ptc_15d,percentile,population_served"
        }

        try:
            response = requests.get(self.cdc_endpoint, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()

            if not data:
                print("  Warning: No data returned from CDC API")
                return pd.DataFrame()

            df = pd.DataFrame(data)

            # Clean and transform
            df = df.rename(columns={
                'wwtp_jurisdiction': 'state',
                'county_names': 'county',
                'date_end': 'date',
                'ptc_15d': 'pct_change_15d',
                'percentile': 'viral_load_percentile',
                'population_served': 'population'
            })

            # Create location_id
            df['location_id'] = df['state'] + '_' + df['county'].fillna('unknown').str.replace(',', '_')

            # Convert types
            df['date'] = pd.to_datetime(df['date'])
            df['viral_load'] = pd.to_numeric(df['viral_load_percentile'], errors='coerce')
            df['pct_change_weekly'] = pd.to_numeric(df['pct_change_15d'], errors='coerce') / 2  # Approximate weekly

            # Clean up
            df = df.dropna(subset=['viral_load'])
            df = df[['location_id', 'state', 'date', 'viral_load', 'pct_change_weekly', 'population']]

            print(f"  Fetched {len(df)} wastewater records")
            print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
            print(f"  Unique locations: {df['location_id'].nunique()}")

            return df

        except requests.exceptions.RequestException as e:
            print(f"  Error fetching CDC data: {e}")
            return pd.DataFrame()

    def fetch_nextstrain_variants(
        self,
        sample_size: int = 10000,
        region: str = "north-america"
    ) -> pd.DataFrame:
        """
        Fetch Nextstrain variant sequence metadata.

        Returns DataFrame with:
        - location (country/division)
        - date (collection date)
        - variant (Pango lineage)
        - sequence_count
        """
        print("Fetching Nextstrain variant data...")

        # Use regional file (smaller, faster)
        url = f"https://data.nextstrain.org/files/ncov/open/{region}/metadata.tsv.gz"

        try:
            print(f"  Downloading from {url}...")
            response = requests.get(url, timeout=120, stream=True)
            response.raise_for_status()

            # Decompress and read as TSV
            content = gzip.decompress(response.content).decode('utf-8')

            # Read only needed columns to save memory
            df = pd.read_csv(
                StringIO(content),
                sep='\t',
                usecols=['strain', 'date', 'country', 'division', 'Nextstrain_clade', 'pango_lineage'],
                nrows=sample_size * 10  # Read more, then filter valid
            )

            # Clean dates
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
            df = df.dropna(subset=['date', 'pango_lineage'])

            # Filter to recent data
            cutoff = datetime.now() - timedelta(days=730)  # Last 2 years
            df = df[df['date'] >= cutoff]

            # Sample if too large
            if len(df) > sample_size:
                df = df.sample(n=sample_size, random_state=42)

            # Create location (country_division)
            df['location'] = df['country'] + '_' + df['division'].fillna('unknown')
            df['variant'] = df['pango_lineage']

            # Aggregate to daily counts per location-variant
            variant_counts = df.groupby(['location', 'date', 'variant']).size().reset_index(name='sequence_count')

            print(f"  Fetched {len(variant_counts)} variant records")
            print(f"  Date range: {variant_counts['date'].min()} to {variant_counts['date'].max()}")
            print(f"  Unique variants: {variant_counts['variant'].nunique()}")
            print(f"  Top variants: {variant_counts['variant'].value_counts().head(5).to_dict()}")

            return variant_counts

        except Exception as e:
            print(f"  Error fetching Nextstrain data: {e}")
            return pd.DataFrame()

    def generate_flight_estimates(
        self,
        locations: list,
        start_date: str = "2023-01-01",
        end_date: str = None
    ) -> pd.DataFrame:
        """
        Generate estimated flight data based on major airport hubs.

        Uses realistic passenger volume estimates between major US cities.
        """
        print("Generating flight estimates...")

        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")

        # Major US airport hubs with daily passenger estimates
        hubs = {
            'California_Los Angeles': {'code': 'LAX', 'daily_pax': 250000},
            'New York_New York': {'code': 'JFK', 'daily_pax': 150000},
            'Illinois_Chicago': {'code': 'ORD', 'daily_pax': 200000},
            'Texas_Dallas': {'code': 'DFW', 'daily_pax': 180000},
            'Colorado_Denver': {'code': 'DEN', 'daily_pax': 170000},
            'Georgia_Atlanta': {'code': 'ATL', 'daily_pax': 275000},
            'Florida_Miami': {'code': 'MIA', 'daily_pax': 120000},
            'Washington_Seattle': {'code': 'SEA', 'daily_pax': 130000},
            'Arizona_Phoenix': {'code': 'PHX', 'daily_pax': 120000},
            'Massachusetts_Boston': {'code': 'BOS', 'daily_pax': 100000},
        }

        # Find matching locations
        location_hubs = {}
        for loc in locations:
            for hub_loc, hub_info in hubs.items():
                # Match by state
                if loc.split('_')[0] == hub_loc.split('_')[0]:
                    location_hubs[loc] = hub_info
                    break

        if not location_hubs:
            print("  Warning: No locations matched to airport hubs")
            # Use top locations as proxies
            for i, loc in enumerate(locations[:10]):
                hub_list = list(hubs.values())
                location_hubs[loc] = hub_list[i % len(hub_list)]

        # Generate daily flight records
        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        records = []

        hub_locs = list(location_hubs.keys())

        for date in dates:
            for origin in hub_locs:
                for dest in hub_locs:
                    if origin != dest:
                        # Estimate passengers between hubs (fraction of total)
                        origin_pax = location_hubs[origin]['daily_pax']
                        dest_pax = location_hubs[dest]['daily_pax']

                        # Simple gravity model estimate
                        base_pax = int(np.sqrt(origin_pax * dest_pax) * 0.001)

                        # Add some noise
                        passengers = max(50, int(base_pax * np.random.uniform(0.8, 1.2)))

                        records.append({
                            'origin': origin,
                            'destination': dest,
                            'date': date,
                            'passengers': passengers
                        })

        df = pd.DataFrame(records)
        print(f"  Generated {len(df)} flight records")
        print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
        print(f"  Routes: {df.groupby(['origin', 'destination']).ngroups}")

        return df

    def save_data(self, wastewater_df, variant_df, flight_df):
        """Save fetched data to CSV files."""
        if not wastewater_df.empty:
            path = os.path.join(self.output_dir, 'wastewater_historical.csv')
            wastewater_df.to_csv(path, index=False)
            print(f"Saved wastewater data to {path}")

        if not variant_df.empty:
            path = os.path.join(self.output_dir, 'variant_historical.csv')
            variant_df.to_csv(path, index=False)
            print(f"Saved variant data to {path}")

        if not flight_df.empty:
            path = os.path.join(self.output_dir, 'flight_historical.csv')
            flight_df.to_csv(path, index=False)
            print(f"Saved flight data to {path}")

    def fetch_all(self, start_date: str = "2023-06-01") -> tuple:
        """Fetch all data sources and save."""
        print("=" * 60)
        print("FETCHING REAL HISTORICAL DATA")
        print("=" * 60)

        # Fetch wastewater
        wastewater_df = self.fetch_cdc_nwss(start_date=start_date)

        # Get locations from wastewater for variant matching
        if not wastewater_df.empty:
            locations = wastewater_df['location_id'].unique().tolist()
        else:
            locations = []

        # Fetch variants
        variant_df = self.fetch_nextstrain_variants(sample_size=20000)

        # Generate flight estimates
        flight_df = self.generate_flight_estimates(
            locations=locations if locations else ['California_unknown', 'New York_unknown'],
            start_date=start_date
        )

        # Save
        self.save_data(wastewater_df, variant_df, flight_df)

        return wastewater_df, variant_df, flight_df


def main():
    fetcher = RealDataFetcher(output_dir="./data/validation")
    wastewater_df, variant_df, flight_df = fetcher.fetch_all(start_date="2023-06-01")

    print("\n" + "=" * 60)
    print("DATA FETCH SUMMARY")
    print("=" * 60)
    print(f"Wastewater records: {len(wastewater_df):,}")
    print(f"Variant records: {len(variant_df):,}")
    print(f"Flight records: {len(flight_df):,}")

    if not wastewater_df.empty and not variant_df.empty:
        print("\nData ready for validation!")
        print("Run: python analysis/run_real_validation.py")
    else:
        print("\nWarning: Some data sources failed to fetch.")


if __name__ == '__main__':
    main()
