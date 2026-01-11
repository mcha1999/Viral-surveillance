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

        # All 50 US states with populations (millions), coordinates, and connectivity scores
        self.states = {
            # Major hubs (connectivity >= 0.8)
            'California': {'pop': 39.5, 'hubs': ['LAX', 'SFO'], 'lat': 36.7, 'lon': -119.4, 'connectivity': 1.0},
            'Texas': {'pop': 29.5, 'hubs': ['DFW', 'IAH'], 'lat': 31.0, 'lon': -99.9, 'connectivity': 0.95},
            'Florida': {'pop': 22.2, 'hubs': ['MIA', 'MCO'], 'lat': 27.6, 'lon': -81.5, 'connectivity': 0.95},
            'New York': {'pop': 19.3, 'hubs': ['JFK', 'LGA'], 'lat': 42.9, 'lon': -75.5, 'connectivity': 1.0},
            'Illinois': {'pop': 12.6, 'hubs': ['ORD'], 'lat': 40.6, 'lon': -89.4, 'connectivity': 0.95},
            'Georgia': {'pop': 10.9, 'hubs': ['ATL'], 'lat': 32.2, 'lon': -83.6, 'connectivity': 0.98},
            'Washington': {'pop': 7.7, 'hubs': ['SEA'], 'lat': 47.8, 'lon': -120.7, 'connectivity': 0.85},
            'Massachusetts': {'pop': 7.0, 'hubs': ['BOS'], 'lat': 42.4, 'lon': -71.4, 'connectivity': 0.88},
            'Colorado': {'pop': 5.8, 'hubs': ['DEN'], 'lat': 39.0, 'lon': -105.5, 'connectivity': 0.85},
            'Nevada': {'pop': 3.1, 'hubs': ['LAS'], 'lat': 38.8, 'lon': -116.4, 'connectivity': 0.82},

            # Secondary hubs (connectivity 0.6-0.8)
            'Pennsylvania': {'pop': 13.0, 'hubs': ['PHL'], 'lat': 41.2, 'lon': -77.2, 'connectivity': 0.75},
            'Ohio': {'pop': 11.8, 'hubs': ['CLE', 'CMH'], 'lat': 40.4, 'lon': -82.9, 'connectivity': 0.65},
            'North Carolina': {'pop': 10.6, 'hubs': ['CLT', 'RDU'], 'lat': 35.8, 'lon': -79.0, 'connectivity': 0.75},
            'Michigan': {'pop': 10.0, 'hubs': ['DTW'], 'lat': 44.3, 'lon': -85.6, 'connectivity': 0.70},
            'New Jersey': {'pop': 9.3, 'hubs': ['EWR'], 'lat': 40.1, 'lon': -74.4, 'connectivity': 0.78},
            'Virginia': {'pop': 8.6, 'hubs': ['IAD', 'DCA'], 'lat': 37.4, 'lon': -78.2, 'connectivity': 0.75},
            'Arizona': {'pop': 7.3, 'hubs': ['PHX'], 'lat': 34.0, 'lon': -111.4, 'connectivity': 0.78},
            'Tennessee': {'pop': 7.0, 'hubs': ['BNA'], 'lat': 35.5, 'lon': -86.6, 'connectivity': 0.65},
            'Minnesota': {'pop': 5.7, 'hubs': ['MSP'], 'lat': 46.7, 'lon': -94.7, 'connectivity': 0.72},
            'Maryland': {'pop': 6.2, 'hubs': ['BWI'], 'lat': 39.0, 'lon': -76.6, 'connectivity': 0.70},
            'Missouri': {'pop': 6.2, 'hubs': ['STL', 'MCI'], 'lat': 37.9, 'lon': -91.8, 'connectivity': 0.62},
            'Indiana': {'pop': 6.8, 'hubs': ['IND'], 'lat': 40.3, 'lon': -86.1, 'connectivity': 0.58},
            'Wisconsin': {'pop': 5.9, 'hubs': ['MKE'], 'lat': 43.8, 'lon': -88.8, 'connectivity': 0.55},
            'Oregon': {'pop': 4.2, 'hubs': ['PDX'], 'lat': 43.8, 'lon': -120.6, 'connectivity': 0.65},
            'Louisiana': {'pop': 4.6, 'hubs': ['MSY'], 'lat': 31.2, 'lon': -91.9, 'connectivity': 0.58},
            'Kentucky': {'pop': 4.5, 'hubs': ['SDF'], 'lat': 37.8, 'lon': -85.8, 'connectivity': 0.52},
            'Utah': {'pop': 3.3, 'hubs': ['SLC'], 'lat': 39.3, 'lon': -111.1, 'connectivity': 0.68},

            # Lower connectivity states (< 0.6)
            'South Carolina': {'pop': 5.1, 'hubs': ['CHS'], 'lat': 34.0, 'lon': -81.0, 'connectivity': 0.50},
            'Alabama': {'pop': 5.0, 'hubs': ['BHM'], 'lat': 32.3, 'lon': -86.9, 'connectivity': 0.45},
            'Oklahoma': {'pop': 4.0, 'hubs': ['OKC'], 'lat': 35.0, 'lon': -97.1, 'connectivity': 0.48},
            'Connecticut': {'pop': 3.6, 'hubs': ['BDL'], 'lat': 41.6, 'lon': -73.1, 'connectivity': 0.52},
            'Iowa': {'pop': 3.2, 'hubs': ['DSM'], 'lat': 42.0, 'lon': -93.2, 'connectivity': 0.40},
            'Arkansas': {'pop': 3.0, 'hubs': ['LIT'], 'lat': 35.2, 'lon': -91.8, 'connectivity': 0.38},
            'Kansas': {'pop': 2.9, 'hubs': ['MCI'], 'lat': 39.0, 'lon': -98.5, 'connectivity': 0.42},
            'Mississippi': {'pop': 3.0, 'hubs': ['JAN'], 'lat': 32.4, 'lon': -89.4, 'connectivity': 0.35},
            'New Mexico': {'pop': 2.1, 'hubs': ['ABQ'], 'lat': 35.7, 'lon': -105.9, 'connectivity': 0.45},
            'Nebraska': {'pop': 2.0, 'hubs': ['OMA'], 'lat': 41.1, 'lon': -99.1, 'connectivity': 0.42},
            'Idaho': {'pop': 1.9, 'hubs': ['BOI'], 'lat': 44.1, 'lon': -114.7, 'connectivity': 0.40},
            'West Virginia': {'pop': 1.8, 'hubs': [], 'lat': 38.6, 'lon': -80.5, 'connectivity': 0.25},
            'Hawaii': {'pop': 1.5, 'hubs': ['HNL'], 'lat': 19.9, 'lon': -155.6, 'connectivity': 0.55},
            'New Hampshire': {'pop': 1.4, 'hubs': ['MHT'], 'lat': 43.2, 'lon': -71.6, 'connectivity': 0.35},
            'Maine': {'pop': 1.4, 'hubs': ['PWM'], 'lat': 45.3, 'lon': -69.4, 'connectivity': 0.32},
            'Montana': {'pop': 1.1, 'hubs': ['BZN'], 'lat': 46.9, 'lon': -110.4, 'connectivity': 0.30},
            'Rhode Island': {'pop': 1.1, 'hubs': ['PVD'], 'lat': 41.6, 'lon': -71.5, 'connectivity': 0.38},
            'Delaware': {'pop': 1.0, 'hubs': [], 'lat': 39.2, 'lon': -75.5, 'connectivity': 0.30},
            'South Dakota': {'pop': 0.9, 'hubs': ['FSD'], 'lat': 43.9, 'lon': -99.4, 'connectivity': 0.28},
            'North Dakota': {'pop': 0.8, 'hubs': ['FAR'], 'lat': 47.5, 'lon': -100.5, 'connectivity': 0.25},
            'Alaska': {'pop': 0.7, 'hubs': ['ANC'], 'lat': 64.2, 'lon': -152.5, 'connectivity': 0.45},
            'Vermont': {'pop': 0.6, 'hubs': ['BTV'], 'lat': 44.0, 'lon': -72.7, 'connectivity': 0.28},
            'Wyoming': {'pop': 0.6, 'hubs': [], 'lat': 43.1, 'lon': -107.3, 'connectivity': 0.22},
        }

        # International locations - key countries for variant emergence and travel
        self.international_locations = {
            # Europe - major hubs and sequencing leaders
            'United Kingdom': {'pop': 67.0, 'hubs': ['LHR', 'LGW'], 'lat': 51.5, 'lon': -0.1, 'connectivity': 1.0, 'sequencing_capacity': 1.0},
            'Germany': {'pop': 83.0, 'hubs': ['FRA', 'MUC'], 'lat': 51.2, 'lon': 10.4, 'connectivity': 0.95, 'sequencing_capacity': 0.9},
            'France': {'pop': 67.0, 'hubs': ['CDG', 'ORY'], 'lat': 46.2, 'lon': 2.2, 'connectivity': 0.92, 'sequencing_capacity': 0.85},
            'Netherlands': {'pop': 17.5, 'hubs': ['AMS'], 'lat': 52.4, 'lon': 4.9, 'connectivity': 0.88, 'sequencing_capacity': 0.9},
            'Denmark': {'pop': 5.9, 'hubs': ['CPH'], 'lat': 56.3, 'lon': 9.5, 'connectivity': 0.75, 'sequencing_capacity': 1.0},  # Best sequencing
            'Italy': {'pop': 60.0, 'hubs': ['FCO', 'MXP'], 'lat': 41.9, 'lon': 12.6, 'connectivity': 0.85, 'sequencing_capacity': 0.7},
            'Spain': {'pop': 47.0, 'hubs': ['MAD', 'BCN'], 'lat': 40.5, 'lon': -3.7, 'connectivity': 0.82, 'sequencing_capacity': 0.65},
            'Ireland': {'pop': 5.0, 'hubs': ['DUB'], 'lat': 53.1, 'lon': -8.2, 'connectivity': 0.70, 'sequencing_capacity': 0.75},

            # Asia-Pacific - key origin regions
            'China': {'pop': 1400.0, 'hubs': ['PEK', 'PVG', 'CAN'], 'lat': 35.9, 'lon': 104.2, 'connectivity': 0.85, 'sequencing_capacity': 0.5},
            'Japan': {'pop': 125.0, 'hubs': ['NRT', 'HND'], 'lat': 36.2, 'lon': 138.3, 'connectivity': 0.90, 'sequencing_capacity': 0.85},
            'South Korea': {'pop': 52.0, 'hubs': ['ICN'], 'lat': 35.9, 'lon': 127.8, 'connectivity': 0.88, 'sequencing_capacity': 0.8},
            'India': {'pop': 1400.0, 'hubs': ['DEL', 'BOM'], 'lat': 20.6, 'lon': 79.0, 'connectivity': 0.75, 'sequencing_capacity': 0.6},
            'Singapore': {'pop': 5.5, 'hubs': ['SIN'], 'lat': 1.4, 'lon': 103.8, 'connectivity': 0.92, 'sequencing_capacity': 0.9},
            'Australia': {'pop': 26.0, 'hubs': ['SYD', 'MEL'], 'lat': -25.3, 'lon': 133.8, 'connectivity': 0.78, 'sequencing_capacity': 0.85},
            'Thailand': {'pop': 70.0, 'hubs': ['BKK'], 'lat': 15.9, 'lon': 100.9, 'connectivity': 0.72, 'sequencing_capacity': 0.5},
            'Philippines': {'pop': 110.0, 'hubs': ['MNL'], 'lat': 12.9, 'lon': 121.8, 'connectivity': 0.65, 'sequencing_capacity': 0.4},

            # Africa - key variant emergence regions
            'South Africa': {'pop': 60.0, 'hubs': ['JNB', 'CPT'], 'lat': -30.6, 'lon': 22.9, 'connectivity': 0.65, 'sequencing_capacity': 0.9},  # Excellent sequencing
            'Nigeria': {'pop': 220.0, 'hubs': ['LOS'], 'lat': 9.1, 'lon': 8.7, 'connectivity': 0.50, 'sequencing_capacity': 0.3},
            'Kenya': {'pop': 54.0, 'hubs': ['NBO'], 'lat': -0.0, 'lon': 37.9, 'connectivity': 0.48, 'sequencing_capacity': 0.4},
            'Egypt': {'pop': 104.0, 'hubs': ['CAI'], 'lat': 26.8, 'lon': 30.8, 'connectivity': 0.55, 'sequencing_capacity': 0.35},

            # Americas (non-US)
            'Canada': {'pop': 38.0, 'hubs': ['YYZ', 'YVR', 'YUL'], 'lat': 56.1, 'lon': -106.3, 'connectivity': 0.92, 'sequencing_capacity': 0.85},
            'Mexico': {'pop': 130.0, 'hubs': ['MEX', 'CUN'], 'lat': 23.6, 'lon': -102.5, 'connectivity': 0.85, 'sequencing_capacity': 0.5},
            'Brazil': {'pop': 215.0, 'hubs': ['GRU', 'GIG'], 'lat': -14.2, 'lon': -51.9, 'connectivity': 0.72, 'sequencing_capacity': 0.65},
            'Argentina': {'pop': 45.0, 'hubs': ['EZE'], 'lat': -38.4, 'lon': -63.6, 'connectivity': 0.58, 'sequencing_capacity': 0.5},
            'Colombia': {'pop': 52.0, 'hubs': ['BOG'], 'lat': 4.6, 'lon': -74.3, 'connectivity': 0.55, 'sequencing_capacity': 0.4},

            # Middle East
            'UAE': {'pop': 10.0, 'hubs': ['DXB', 'AUH'], 'lat': 23.4, 'lon': 53.8, 'connectivity': 0.95, 'sequencing_capacity': 0.7},
            'Israel': {'pop': 9.5, 'hubs': ['TLV'], 'lat': 31.0, 'lon': 34.9, 'connectivity': 0.75, 'sequencing_capacity': 0.9},
            'Qatar': {'pop': 2.9, 'hubs': ['DOH'], 'lat': 25.4, 'lon': 51.2, 'connectivity': 0.88, 'sequencing_capacity': 0.6},
        }

        # Variant characteristics - UPDATED with realistic international origins
        self.variants = {
            'XBB.1.5': {
                'emergence_date': '2022-10-01',
                'peak_date': '2023-02-15',
                'origin': 'United States',  # First major detection in US (New York area)
                'origin_state': 'New York',  # For US spread
                'international_origin': False,
                'transmissibility': 1.0,
                'spread_rate': 0.08,
            },
            'EG.5': {
                'emergence_date': '2023-02-01',  # First detected in Indonesia/China
                'peak_date': '2023-08-15',
                'origin': 'China',
                'origin_state': None,
                'international_origin': True,
                'us_entry_points': ['California', 'New York', 'Washington'],  # West coast + NYC
                'transmissibility': 1.1,
                'spread_rate': 0.06,
            },
            'BA.2.86': {
                'emergence_date': '2023-07-15',  # First detected in Israel and Denmark
                'peak_date': '2023-11-01',
                'origin': 'Israel',
                'origin_state': None,
                'international_origin': True,
                'us_entry_points': ['New York', 'New Jersey', 'Florida'],  # East coast
                'transmissibility': 1.15,
                'spread_rate': 0.07,
            },
            'JN.1': {
                'emergence_date': '2023-08-25',  # Emerged from BA.2.86, first detected in Luxembourg
                'peak_date': '2024-01-15',
                'origin': 'France',  # European origin
                'origin_state': None,
                'international_origin': True,
                'us_entry_points': ['New York', 'Massachusetts', 'Illinois'],  # Major hubs
                'transmissibility': 1.3,
                'spread_rate': 0.10,
            },
            'KP.2': {  # Adding newer variant
                'emergence_date': '2024-01-15',
                'peak_date': '2024-05-01',
                'origin': 'India',
                'origin_state': None,
                'international_origin': True,
                'us_entry_points': ['California', 'New York', 'Texas', 'New Jersey'],
                'transmissibility': 1.25,
                'spread_rate': 0.08,
            },
        }

        # International flight routes to US - daily passenger estimates
        self.international_routes = {
            # From UK
            ('United Kingdom', 'New York'): 15000,
            ('United Kingdom', 'California'): 8000,
            ('United Kingdom', 'Florida'): 6000,
            ('United Kingdom', 'Massachusetts'): 4000,
            ('United Kingdom', 'Illinois'): 3500,
            ('United Kingdom', 'Texas'): 3000,

            # From Germany
            ('Germany', 'New York'): 8000,
            ('Germany', 'California'): 5000,
            ('Germany', 'Illinois'): 3500,
            ('Germany', 'Florida'): 2500,

            # From France
            ('France', 'New York'): 7000,
            ('France', 'California'): 4000,
            ('France', 'Florida'): 3000,
            ('France', 'Georgia'): 2000,

            # From Japan
            ('Japan', 'California'): 12000,
            ('Japan', 'New York'): 5000,
            ('Japan', 'Hawaii'): 8000,
            ('Japan', 'Texas'): 3000,

            # From South Korea
            ('South Korea', 'California'): 8000,
            ('South Korea', 'New York'): 4000,
            ('South Korea', 'Texas'): 2500,

            # From China
            ('China', 'California'): 10000,
            ('China', 'New York'): 6000,
            ('China', 'Illinois'): 3000,
            ('China', 'Washington'): 4000,

            # From India
            ('India', 'New York'): 6000,
            ('India', 'California'): 5000,
            ('India', 'New Jersey'): 4000,
            ('India', 'Texas'): 3500,
            ('India', 'Illinois'): 2500,

            # From Canada
            ('Canada', 'New York'): 12000,
            ('Canada', 'California'): 8000,
            ('Canada', 'Florida'): 10000,
            ('Canada', 'Michigan'): 5000,
            ('Canada', 'Washington'): 6000,
            ('Canada', 'Illinois'): 4000,

            # From Mexico
            ('Mexico', 'Texas'): 20000,
            ('Mexico', 'California'): 18000,
            ('Mexico', 'Florida'): 8000,
            ('Mexico', 'Arizona'): 6000,
            ('Mexico', 'Illinois'): 4000,
            ('Mexico', 'New York'): 5000,

            # From UAE (major hub)
            ('UAE', 'New York'): 5000,
            ('UAE', 'California'): 3000,
            ('UAE', 'Texas'): 2500,

            # From Brazil
            ('Brazil', 'Florida'): 6000,
            ('Brazil', 'New York'): 4000,
            ('Brazil', 'Texas'): 2000,

            # From South Africa
            ('South Africa', 'New York'): 2000,
            ('South Africa', 'Georgia'): 1500,

            # From Australia
            ('Australia', 'California'): 5000,
            ('Australia', 'Texas'): 2000,

            # From Singapore
            ('Singapore', 'California'): 3000,
            ('Singapore', 'New York'): 2500,

            # From Israel
            ('Israel', 'New York'): 4000,
            ('Israel', 'New Jersey'): 2000,
            ('Israel', 'Florida'): 1500,

            # From Netherlands
            ('Netherlands', 'New York'): 4000,
            ('Netherlands', 'California'): 2000,

            # From Ireland
            ('Ireland', 'New York'): 5000,
            ('Ireland', 'Massachusetts'): 3000,
            ('Ireland', 'Illinois'): 2000,
        }

    def generate_wastewater_data(
        self,
        start_date: str = '2023-01-01',
        end_date: str = '2024-06-30',
        include_international: bool = True
    ) -> pd.DataFrame:
        """
        Generate realistic wastewater surveillance data.

        Patterns based on:
        - Seasonal variation (winter peaks)
        - Variant wave dynamics
        - Regional spread patterns
        - International variant origins and spread to US
        """
        print("Generating realistic wastewater data...")

        dates = pd.date_range(start=start_date, end=end_date, freq='W')  # Weekly
        records = []

        # Combine US states and international locations
        all_locations = dict(self.states)
        if include_international:
            all_locations.update(self.international_locations)

        for location, info in all_locations.items():
            is_international = location in self.international_locations

            # Base viral load varies by population density proxy
            base_load = 5000 * (info['pop'] / 10) ** 0.5

            for date in dates:
                # Seasonal component (higher in winter)
                day_of_year = date.dayofyear
                # Northern hemisphere vs Southern hemisphere seasonality
                if info.get('lat', 40) < 0:  # Southern hemisphere
                    seasonal = 1 + 0.4 * np.cos(2 * np.pi * (day_of_year - 196) / 365)  # Peak in July
                else:
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

                        # Location-specific delay based on origin
                        origin_country = v_info['origin']
                        origin_state = v_info.get('origin_state')

                        if is_international:
                            # International location - check if it's the origin
                            if location == origin_country:
                                delay_factor = 1.0  # Origin country sees it first
                            else:
                                # Spread based on connectivity
                                delay_factor = info['connectivity'] * 0.7
                        else:
                            # US state
                            if v_info.get('international_origin'):
                                # International variant - spread through entry points
                                us_entry_points = v_info.get('us_entry_points', ['California', 'New York'])
                                if location in us_entry_points:
                                    delay_factor = 0.9  # Entry points see it early
                                else:
                                    # Other US states - based on connectivity to entry points
                                    delay_factor = info['connectivity'] * 0.6
                            else:
                                # Domestic US origin
                                if location == origin_state:
                                    delay_factor = 1.0
                                else:
                                    # Delay based on distance from origin state
                                    origin_info = self.states.get(origin_state, info)
                                    lat_diff = abs(info['lat'] - origin_info['lat'])
                                    delay_factor = max(0, 1 - lat_diff / 30)

                        wave_contribution += growth * v_info['transmissibility'] * delay_factor * 0.3

                # Combine components
                viral_load = base_load * seasonal * (1 + wave_contribution)

                # Add noise (international data may be noisier due to reporting differences)
                noise_factor = 0.20 if is_international else 0.15
                viral_load *= np.random.lognormal(0, noise_factor)

                records.append({
                    'location_id': location,
                    'date': date,
                    'viral_load': viral_load,
                    'wave_contribution': wave_contribution,
                    'population': info['pop'] * 1e6,
                    'is_international': is_international
                })

        df = pd.DataFrame(records)

        # Calculate ACTUAL week-over-week change from the viral load data
        df = df.sort_values(['location_id', 'date'])
        df['prev_load'] = df.groupby('location_id')['viral_load'].shift(1)
        df['pct_change_weekly'] = ((df['viral_load'] - df['prev_load']) / df['prev_load'] * 100).fillna(0)
        df = df.drop(columns=['prev_load', 'wave_contribution'])

        us_count = len(df[~df['is_international']])
        intl_count = len(df[df['is_international']])
        print(f"  Generated {len(df)} wastewater records")
        print(f"  US locations: {df[~df['is_international']]['location_id'].nunique()}")
        if include_international:
            print(f"  International locations: {df[df['is_international']]['location_id'].nunique()}")
        print(f"  Date range: {df['date'].min()} to {df['date'].max()}")

        return df

    def generate_variant_data(
        self,
        start_date: str = '2023-01-01',
        end_date: str = '2024-06-30',
        include_international: bool = True
    ) -> pd.DataFrame:
        """
        Generate realistic variant sequence data.

        Simulates:
        - Geographic spread from international origins to US entry points
        - Correlation with flight connectivity
        - Sequencing capacity differences by country
        - Realistic detection delays
        """
        print("Generating realistic variant data...")

        dates = pd.date_range(start=start_date, end=end_date, freq='D')
        records = []

        for variant, v_info in self.variants.items():
            emergence = pd.Timestamp(v_info['emergence_date'])
            is_international_origin = v_info.get('international_origin', False)
            origin_country = v_info['origin']
            origin_state = v_info.get('origin_state')

            if emergence < pd.Timestamp(start_date):
                emergence = pd.Timestamp(start_date)

            # Generate data for international locations first (if international origin)
            if include_international and is_international_origin:
                for country, c_info in self.international_locations.items():
                    if country == origin_country:
                        arrival_date = emergence
                    else:
                        # International spread based on connectivity
                        connectivity = c_info['connectivity']
                        base_delay = 14  # Slower international spread
                        delay = int(base_delay / connectivity)
                        delay = max(5, int(delay * np.random.uniform(0.7, 1.3)))
                        arrival_date = emergence + timedelta(days=delay)

                    if arrival_date > pd.Timestamp(end_date):
                        continue

                    for date in dates:
                        if date < arrival_date:
                            continue

                        days_since_arrival = (date - arrival_date).days

                        # Growth curve (logistic)
                        carrying_capacity = max(c_info['pop'] * 30, 100)
                        growth_rate = v_info['spread_rate']
                        prevalence = carrying_capacity / (1 + np.exp(-growth_rate * (days_since_arrival - 60)))

                        # Sequencing capacity affects detection
                        seq_capacity = c_info.get('sequencing_capacity', 0.5)
                        base_sample_rate = 0.008
                        sample_rate = base_sample_rate * seq_capacity * (0.5 + c_info['connectivity'])

                        expected_sequences = prevalence * sample_rate

                        if expected_sequences > 0.05:
                            sequences = np.random.poisson(max(1, expected_sequences))
                            if sequences > 0:
                                records.append({
                                    'location': country,
                                    'date': date,
                                    'variant': variant,
                                    'sequence_count': sequences,
                                    'is_international': True
                                })

            # Calculate arrival time for US states
            us_entry_points = v_info.get('us_entry_points', ['California', 'New York'])

            for state, s_info in self.states.items():
                if is_international_origin:
                    # International variant - arrives through entry points
                    if state in us_entry_points:
                        # Entry points get it after international spread
                        # Calculate delay based on international flight volume
                        intl_routes_to_state = sum(
                            pax for (orig, dest), pax in self.international_routes.items()
                            if dest == state and orig == origin_country
                        )
                        if intl_routes_to_state > 5000:
                            delay = 7  # High traffic = fast arrival
                        elif intl_routes_to_state > 2000:
                            delay = 14
                        else:
                            delay = 21

                        delay = max(5, int(delay * np.random.uniform(0.8, 1.2)))
                        arrival_date = emergence + timedelta(days=delay)
                    else:
                        # Non-entry points get it after domestic spread from entry points
                        connectivity = s_info['connectivity']
                        base_delay = 21 + (1 - connectivity) * 30  # 21-51 days
                        delay = max(14, int(base_delay * np.random.uniform(0.7, 1.3)))
                        arrival_date = emergence + timedelta(days=delay)
                else:
                    # Domestic US origin
                    if state == origin_state:
                        arrival_date = emergence
                    else:
                        connectivity = s_info['connectivity']
                        lat_distance = abs(s_info['lat'] - self.states[origin_state]['lat'])
                        base_delay = 7 + lat_distance / 2
                        delay = int(base_delay / connectivity)
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
                    carrying_capacity = max(s_info['pop'] * 50, 100)
                    growth_rate = v_info['spread_rate']
                    prevalence = carrying_capacity / (1 + np.exp(-growth_rate * (days_since_arrival - 60)))

                    # Sampling probability - higher for hub states
                    base_sample_rate = 0.01
                    sample_rate = base_sample_rate * (0.5 + s_info['connectivity'])

                    expected_sequences = prevalence * sample_rate

                    if expected_sequences > 0.05:
                        sequences = np.random.poisson(max(1, expected_sequences))
                        if sequences > 0:
                            records.append({
                                'location': state,
                                'date': date,
                                'variant': variant,
                                'sequence_count': sequences,
                                'is_international': False
                            })

        df = pd.DataFrame(records)

        # Aggregate to weekly for cleaner data
        df['week'] = df['date'].dt.to_period('W').dt.start_time
        df = df.groupby(['location', 'week', 'variant', 'is_international'])['sequence_count'].sum().reset_index()
        df = df.rename(columns={'week': 'date'})

        us_locs = df[~df['is_international']]['location'].nunique()
        intl_locs = df[df['is_international']]['location'].nunique() if include_international else 0

        print(f"  Generated {len(df)} variant records")
        print(f"  Variants: {df['variant'].unique().tolist()}")
        print(f"  US locations: {us_locs}")
        if include_international:
            print(f"  International locations: {intl_locs}")

        return df

    def generate_flight_data(
        self,
        start_date: str = '2023-01-01',
        end_date: str = '2024-06-30',
        include_international: bool = True
    ) -> pd.DataFrame:
        """
        Generate realistic domestic and international flight data.

        Based on:
        - Major hub connectivity
        - Population-weighted passenger flows
        - Seasonal travel patterns
        - International route data to US hubs
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

            # Domestic US flights
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
                        'passengers': passengers,
                        'is_international': False
                    })

            # International flights to US
            if include_international:
                for (origin_country, dest_state), base_passengers in self.international_routes.items():
                    # Apply seasonal factor with some variation
                    # International travel has different seasonal patterns
                    intl_seasonal = 1 + 0.15 * np.sin(2 * np.pi * (day_of_year - 180) / 365)

                    # Holiday boost for international
                    if date.month == 12 and date.day >= 20:
                        intl_seasonal *= 1.3
                    elif date.month in [6, 7, 8]:  # Summer peak
                        intl_seasonal *= 1.2

                    passengers = int(base_passengers * intl_seasonal)
                    passengers = max(100, int(passengers * np.random.uniform(0.85, 1.15)))

                    records.append({
                        'origin': origin_country,
                        'destination': dest_state,
                        'date': date,
                        'passengers': passengers,
                        'is_international': True
                    })

        df = pd.DataFrame(records)

        domestic_routes = df[~df['is_international']].groupby(['origin', 'destination']).ngroups
        intl_routes = df[df['is_international']].groupby(['origin', 'destination']).ngroups if include_international else 0

        print(f"  Generated {len(df)} flight records")
        print(f"  Domestic routes: {domestic_routes}")
        if include_international:
            print(f"  International routes: {intl_routes}")

        return df

    def generate_all(
        self,
        start_date: str = '2023-01-01',
        end_date: str = '2024-06-30',
        include_international: bool = True
    ) -> tuple:
        """Generate all datasets with optional international coverage."""
        print("=" * 60)
        print("GENERATING REALISTIC EPIDEMIOLOGICAL DATA")
        print("=" * 60)
        print(f"Period: {start_date} to {end_date}")
        print(f"US States: {len(self.states)}")
        if include_international:
            print(f"International locations: {len(self.international_locations)}")
        print(f"Variants: {list(self.variants.keys())}")
        intl_variants = [v for v, info in self.variants.items() if info.get('international_origin')]
        if intl_variants:
            print(f"International origin variants: {intl_variants}")
        print()

        wastewater = self.generate_wastewater_data(start_date, end_date, include_international)
        variants = self.generate_variant_data(start_date, end_date, include_international)
        flights = self.generate_flight_data(start_date, end_date, include_international)

        # Create location mapping (identity for both US states and international)
        location_mapping = {s: s for s in self.states.keys()}
        if include_international:
            location_mapping.update({c: c for c in self.international_locations.keys()})

        return wastewater, variants, flights, location_mapping


def run_validation_with_realistic_data(include_international: bool = True):
    """Run the full validation with realistic simulated data."""
    from retrospective_validation import RetrospectiveValidator

    # Generate data
    simulator = RealisticEpiSimulator(seed=42)
    wastewater_df, variant_df, flight_df, location_mapping = simulator.generate_all(
        start_date='2023-01-01',
        end_date='2024-06-30',
        include_international=include_international
    )

    print("\n" + "=" * 60)
    print("RUNNING VALIDATION ON REALISTIC DATA")
    if include_international:
        print("(WITH INTERNATIONAL COVERAGE)")
    print("=" * 60)

    # Get US-only locations for validation (validator currently focused on US)
    us_locations = list(simulator.states.keys())
    intl_locations = list(simulator.international_locations.keys()) if include_international else []

    # Initialize validator
    validator = RetrospectiveValidator(
        wastewater_df=wastewater_df,
        variant_df=variant_df,
        flight_df=flight_df,
        location_mapping=location_mapping
    )

    # Run tests
    print("\n[H1] Import pressure → Variant arrival timing...")
    print("     Testing international origin variants: EG.5, BA.2.86, JN.1, KP.2")
    h1_result = validator.test_h1_import_pressure_variant_arrival(
        variants_to_test=['JN.1', 'BA.2.86', 'EG.5', 'KP.2'],
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
        locations=us_locations[:15]  # US locations only
    )
    status = '✓ PASS' if h2_result.passed else '✗ FAIL'
    print(f"     {status}")
    print(f"     Directional accuracy: {h2_result.metric_value:.1%}")
    if 'rmse' in h2_result.details:
        print(f"     RMSE: {h2_result.details['rmse']:.2f} (baseline: {h2_result.details['baseline_rmse_no_change']:.2f})")
        print(f"     Improvement: {h2_result.details['improvement_vs_baseline']:.1f}%")

    print("\n[H3] Propagation speed by import pressure...")
    print("     Testing JN.1 (international origin: France)")
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

    # International-specific validation
    if include_international:
        print("\n" + "-" * 60)
        print("INTERNATIONAL VALIDATION")
        print("-" * 60)

        # Test international variant detection lead time
        intl_variants = ['EG.5', 'BA.2.86', 'JN.1', 'KP.2']
        variant_origins = {'EG.5': 'China', 'BA.2.86': 'Israel', 'JN.1': 'France', 'KP.2': 'India'}

        print("\n[INTL-1] International variant detection lead time:")
        for variant in intl_variants:
            origin = variant_origins.get(variant, 'Unknown')
            # Check if variant was detected in origin before US
            intl_var = variant_df[(variant_df['variant'] == variant) & (variant_df['is_international'] == True)]
            us_var = variant_df[(variant_df['variant'] == variant) & (variant_df['is_international'] == False)]

            if not intl_var.empty and not us_var.empty:
                first_intl = intl_var['date'].min()
                first_us = us_var['date'].min()
                lead_days = (first_us - first_intl).days

                print(f"   {variant} (origin: {origin})")
                print(f"     First international detection: {first_intl.strftime('%Y-%m-%d')}")
                print(f"     First US detection: {first_us.strftime('%Y-%m-%d')}")
                print(f"     Lead time: {lead_days} days")

        print("\n[INTL-2] International flight volume to US entry points:")
        intl_flights = flight_df[flight_df['is_international'] == True]
        if not intl_flights.empty:
            top_routes = intl_flights.groupby(['origin', 'destination'])['passengers'].sum()
            top_routes = top_routes.sort_values(ascending=False).head(10)
            for (orig, dest), pax in top_routes.items():
                print(f"     {orig} → {dest}: {pax:,.0f} passengers")

    # Generate report
    report = validator.generate_report()

    # Add international metrics to report
    if include_international:
        report['international_coverage'] = {
            'countries': len(intl_locations),
            'international_routes': len(simulator.international_routes),
            'international_origin_variants': [v for v, info in simulator.variants.items()
                                               if info.get('international_origin')]
        }

    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    print(f"Tests passed: {report['summary']['passed']}/{report['summary']['total_tests']}")
    print(f"Pass rate: {report['summary']['pass_rate']:.0%}")
    print(f"Overall verdict: {report['summary']['overall_verdict']}")

    if include_international:
        print(f"\nInternational coverage:")
        print(f"  Countries: {len(intl_locations)}")
        print(f"  International routes: {len(simulator.international_routes)}")
        print(f"  International variants: {len([v for v in simulator.variants.values() if v.get('international_origin')])}")

    print("\nRecommendations:")
    for i, rec in enumerate(report['recommendations'], 1):
        print(f"  {i}. {rec}")

    # Save report
    report_file = 'validation_report_international.json' if include_international else 'validation_report_realistic.json'
    with open(report_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nFull report saved to: {report_file}")

    return report


if __name__ == '__main__':
    run_validation_with_realistic_data(include_international=True)
