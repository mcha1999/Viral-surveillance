# Data Sources Integration Guide

## Budget Summary

| Source | Cost | Priority |
|--------|------|----------|
| AviationStack (10k calls) | $49/mo | P0 - Flight data |
| Socrata App Token (CDC) | Free | P0 - US wastewater |
| OpenSky Network | Free (registered) | P1 - Flight validation |
| Nextstrain | Free | P0 - Genomic data |
| EU/International sources | Free (scraping) | P1 - Global coverage |
| **Buffer** | $26/mo | Contingency |
| **Total** | **≤$75/mo** | |

---

## 1. Wastewater Surveillance Data (FREE)

### 1.1 United States: CDC NWSS (Tier 1 - Excellent)

```
Endpoint: https://data.cdc.gov/resource/g653-rqe2.json
Format: JSON (Socrata API)
Frequency: 2x weekly (Tuesday, Thursday)
Coverage: ~1,300 sites, 50 states
Granularity: County/Plant level (Tier 1)
Cost: FREE (get app token for higher rate limits)
Rate Limit: 1000 requests/hour with app token
```

**Integration Code:**
```python
from sodapy import Socrata

client = Socrata("data.cdc.gov", app_token=SOCRATA_TOKEN)
results = client.get("g653-rqe2", limit=5000, where="date_start > '2026-01-01'")

# Key fields:
# - wwtp_id: Unique plant identifier
# - date_start, date_end: Sampling period
# - ptc_15d: Percent change 15-day
# - detect_prop_15d: Detection proportion
# - population_served: Catchment size
# - county_fips: For geographic join
```

### 1.2 Europe (Mixed Granularity)

| Country | Source | Granularity | Format | URL |
|---------|--------|-------------|--------|-----|
| UK | UKHSA Dashboard | Tier 1 (Site) | JSON API | coronavirus.data.gov.uk |
| Netherlands | RIVM CoronaWatchNL | Tier 1 (Site) | CSV | data.rivm.nl |
| Germany | RKI | Tier 2 (State) | CSV | github.com/robert-koch-institut |
| France | data.gouv.fr | Tier 2 (Region) | CSV | data.gouv.fr |
| Spain | ISCIII | Tier 2 (Region) | CSV | cnecovid.isciii.es |
| Italy | ISS | Tier 2 (Region) | CSV | epicentro.iss.it |
| Austria | AGES | Tier 1 (Site) | JSON | data.gv.at |
| Switzerland | BAG | Tier 2 (Canton) | CSV | opendata.swiss |
| Belgium | Sciensano | Tier 2 (Region) | CSV | epistat.sciensano.be |
| Denmark | SSI | Tier 1 (Site) | CSV | covid19.ssi.dk |

**Example: UK UKHSA Integration**
```python
import requests

url = "https://api.coronavirus.data.gov.uk/v2/data"
params = {
    "areaType": "nation",
    "metric": "covidOccupiedMVBeds",
    "format": "json"
}
response = requests.get(url, params=params)
data = response.json()
```

### 1.3 Asia-Pacific

| Country | Source | Granularity | Access |
|---------|--------|-------------|--------|
| Japan | NIID | Tier 1 (Prefecture) | CSV, Free |
| Australia | health.gov.au | Tier 1 (Site) | JSON, Free |
| New Zealand | ESR | Tier 1 (Site) | CSV, Free |
| Singapore | NEA | Tier 2 (National) | JSON, Free |
| South Korea | KDCA | Tier 2 (Province) | Scrape, Free |

### 1.4 Americas (Outside US)

| Country | Source | Granularity | Access |
|---------|--------|-------------|--------|
| Canada | HC-SC | Tier 2 (Province) | CSV, Free |
| Brazil | Fiocruz | Tier 2 (State) | CSV, Free |
| Mexico | CONAGUA | Tier 3 (National) | Limited |
| Argentina | Min. Salud | Tier 2 (Province) | CSV, Free |
| Chile | Minsal | Tier 2 (Region) | CSV, Free |

### 1.5 Coverage Gaps & Strategies

| Region | Coverage | Strategy |
|--------|----------|----------|
| Africa | South Africa only | Sentinel inference from flights |
| Middle East | Israel, UAE spotty | National-level only |
| South Asia | India (major cities) | Academic partnerships |
| Southeast Asia | Thailand, Vietnam | National-level only |

---

## 2. Genomic Data: Nextstrain (FREE)

```
Endpoints:
- Tree: https://data.nextstrain.org/ncov_global.json
- Metadata: https://data.nextstrain.org/metadata.tsv.gz

Frequency: Daily builds
Coverage: Global (sequencing-capable nations)
Cost: FREE
```

**Key Fields:**
- `strain`: Unique sequence identifier
- `date`: Collection date
- `country`, `division`, `location`: Geographic hierarchy
- `clade_membership`: Variant classification (Pango lineage)
- `QC_overall_status`: Data quality flag

**Integration Notes:**
- metadata.tsv is ~2GB compressed - use incremental sync
- Track last processed date to avoid reprocessing
- Use Augur library for phylogenetic calculations: `pip install augur`

**Example Integration:**
```python
import pandas as pd
import gzip
from urllib.request import urlretrieve

# Download metadata
urlretrieve(
    "https://data.nextstrain.org/metadata.tsv.gz",
    "metadata.tsv.gz"
)

# Read incrementally
with gzip.open("metadata.tsv.gz", "rt") as f:
    df = pd.read_csv(f, sep="\t", usecols=[
        "strain", "date", "country", "division",
        "location", "clade_membership"
    ])

# Filter recent data
df["date"] = pd.to_datetime(df["date"], errors="coerce")
recent = df[df["date"] > "2026-01-01"]
```

---

## 3. Flight Data

### 3.1 Primary: AviationStack ($49/mo for 10k calls)

```
Endpoint: https://api.aviationstack.com/v1/flights
Coverage: Global schedules, historical flights
Pricing: $49/mo for 10,000 API calls

Budget: 10,000 calls/month = ~333 calls/day
Strategy: Cache route pairs, query top 500 routes daily
```

**Example Request:**
```python
import requests

url = "http://api.aviationstack.com/v1/flights"
params = {
    "access_key": AVIATIONSTACK_KEY,
    "dep_iata": "JFK",
    "arr_iata": "LHR",
    "flight_date": "2026-01-10"
}
response = requests.get(url, params=params)
flights = response.json()["data"]

# Key fields:
# - departure.iata, arrival.iata: Airport codes
# - flight_date: Schedule date
# - airline.name: Carrier
# - aircraft.iata: Aircraft type (for pax estimation)
# - flight_status: scheduled/active/landed/cancelled
```

**Note:** AviationStack does NOT include passenger counts. Estimate from aircraft type.

### 3.2 Validation: OpenSky Network (FREE)

```
Endpoint: https://opensky-network.org/api
Coverage: Real-time ADS-B positions
Rate Limit: 400 req/day (anonymous), 4000 req/day (registered)
Use Case: Validate flight counts, detect route changes
```

**Example:**
```python
import requests

# Get all flights in bounding box
url = "https://opensky-network.org/api/states/all"
params = {
    "lamin": 40.0,
    "lomin": -75.0,
    "lamax": 42.0,
    "lomax": -73.0
}
response = requests.get(url, auth=(OPENSKY_USER, OPENSKY_PASS))
states = response.json()["states"]
```

### 3.3 Passenger Estimation (No Enterprise License Needed)

```python
AIRCRAFT_CAPACITY = {
    "A319": 130, "A320": 150, "A321": 185, "A330": 250,
    "A350": 300, "A380": 500,
    "B737": 160, "B738": 175, "B739": 180,
    "B747": 400, "B777": 350, "B787": 290,
    "E170": 70, "E190": 100, "CRJ9": 90
}
AVG_LOAD_FACTOR = 0.82  # Industry average

def estimate_passengers(flights: list) -> int:
    """Estimate passenger count from flight list."""
    total = 0
    for flight in flights:
        aircraft = flight.get("aircraft", {}).get("iata", "")
        capacity = AIRCRAFT_CAPACITY.get(aircraft, 150)  # Default 150
        total += int(capacity * AVG_LOAD_FACTOR)
    return total
```

---

## 4. Global Coverage Summary (Top 50 Countries)

| Tier | Countries | Granularity | Data Quality |
|------|-----------|-------------|--------------|
| **Tier 1** (14) | USA, UK, Netherlands, Australia, NZ, Japan, Austria, Denmark, Belgium, Switzerland, Germany, Canada, France, Spain | State/Site | Excellent |
| **Tier 2** (18) | Italy, Sweden, Norway, Finland, Portugal, Ireland, Poland, Czech, Singapore, South Korea, Taiwan, Israel, Brazil, Argentina, Chile, South Africa, Mexico, India | State/Region | Good |
| **Tier 3** (18) | UAE, Saudi Arabia, Turkey, Egypt, Morocco, Nigeria, Kenya, Thailand, Vietnam, Malaysia, Indonesia, Philippines, Colombia, Peru, Russia, Ukraine, Pakistan, Bangladesh | National only | Limited |

---

## 5. Ingestion Schedule

```python
INGESTION_SCHEDULE = {
    # Wastewater sources (aligned with publication schedules)
    "wastewater_cdc": "0 6 * * 2,4",      # Tue/Thu 6am UTC
    "wastewater_uk": "0 8 * * 1,4",        # Mon/Thu 8am UTC
    "wastewater_eu": "0 8 * * 1,3,5",      # MWF 8am UTC
    "wastewater_apac": "0 2 * * 2,5",      # Tue/Fri 2am UTC

    # Genomic data
    "nextstrain_sync": "0 4 * * *",        # Daily 4am UTC

    # Flight data
    "flight_routes": "0 */6 * * *",        # Every 6 hours

    # Risk calculation
    "risk_engine": "0 * * * *",            # Hourly
}
```

---

## 6. Data Quality Scoring

Each data point receives a quality score:

```python
def calculate_quality_score(record: dict) -> float:
    """Calculate 0-1 quality score for a data record."""
    score = 1.0

    # Freshness penalty
    age_days = (datetime.now() - record["timestamp"]).days
    if age_days > 7:
        score -= 0.1 * (age_days - 7)

    # Granularity bonus
    tier = record.get("granularity_tier", 3)
    score += (3 - tier) * 0.1  # Tier 1 = +0.2, Tier 2 = +0.1

    # Source reliability
    reliability = SOURCE_RELIABILITY.get(record["source"], 0.8)
    score *= reliability

    return max(0, min(1, score))
```

---

## 7. Adapter Template

Each data source requires an adapter following this pattern:

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List

@dataclass
class SurveillanceEvent:
    location_id: str
    timestamp: datetime
    data_source: str
    signal_type: str  # "wastewater" | "genomic" | "flight"
    metrics: dict
    quality_score: float

class DataAdapter(ABC):
    """Base class for all data source adapters."""

    @abstractmethod
    def fetch(self) -> List[dict]:
        """Fetch raw data from source."""
        pass

    @abstractmethod
    def normalize(self, raw_data: List[dict]) -> List[SurveillanceEvent]:
        """Normalize to common schema."""
        pass

    def run(self) -> List[SurveillanceEvent]:
        """Full pipeline: fetch → normalize."""
        raw = self.fetch()
        return self.normalize(raw)
```
