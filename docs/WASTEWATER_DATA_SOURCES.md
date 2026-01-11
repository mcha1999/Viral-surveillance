# Wastewater Surveillance Data Sources

This document catalogs all validated wastewater surveillance data sources that can be used for risk modeling validation.

## US Federal Sources

### CDC NWSS (National Wastewater Surveillance System)

**Status**: ✅ Active, Production-ready

| Property | Value |
|----------|-------|
| Endpoint | `https://data.cdc.gov/resource/2ew6-ywp6.json` |
| Format | JSON, CSV |
| Update Frequency | Weekly (Fridays) |
| Coverage | ~1,500 sites across US |
| Historical Data | 2020-present |
| Authentication | Optional (Socrata app token for higher rate limits) |

**Key Fields**:
- `wwtp_id`: Wastewater treatment plant ID
- `reporting_jurisdiction`: State abbreviation
- `sample_collect_date`: Collection date
- `percentile`: National percentile ranking (0-100)
- `ptc_15d`: 15-day percent change
- `detect_prop_15d`: Detection proportion
- `population_served`: Population covered

**Example Query**:
```python
import requests

url = "https://data.cdc.gov/resource/2ew6-ywp6.json"
params = {
    "$limit": 10000,
    "$where": "sample_collect_date >= '2024-01-01'",
    "$order": "sample_collect_date DESC",
    "$$app_token": "YOUR_SOCRATA_TOKEN"  # Optional
}
response = requests.get(url, params=params)
data = response.json()
```

**Notes**:
- The old dataset ID `g653-rqe2` was deprecated
- No authentication required for basic access
- Rate limits: 1000 requests/hour without token

---

## US State-Level Sources

### California Cal-SuWers

**Status**: ✅ Active

| Property | Value |
|----------|-------|
| Endpoint | `https://data.chhs.ca.gov/dataset/wastewater-surveillance-data-california` |
| Format | CSV, JSON via CKAN API |
| Coverage | 100+ sites in California |
| Pathogens | SARS-CoV-2, Influenza, RSV, Mpox, Norovirus |

**Data Access**:
```python
url = "https://data.chhs.ca.gov/api/3/action/datastore_search"
params = {"resource_id": "s3r7-wgpq", "limit": 5000}
response = requests.get(url, params=params)
data = response.json()["result"]["records"]
```

### Massachusetts MWRA (Biobot)

**Status**: ✅ Active

| Property | Value |
|----------|-------|
| Endpoint | `https://www.mwra.com/biobot/biobotdata.csv` |
| Format | CSV |
| Coverage | Greater Boston area (~2.5M population) |
| Update Frequency | Daily (2-3 day lag) |
| Pathogens | SARS-CoV-2, variants |

**Notes**:
- High-quality data from Biobot Analytics
- Includes variant screening results
- Northern and Southern plant data

### New York State

**Status**: ✅ Active

| Property | Value |
|----------|-------|
| Portal | `https://coronavirus.health.ny.gov/covid-19-wastewater-surveillance` |
| Format | Web dashboard + downloadable CSV |
| Coverage | Multiple regions across NY |

### Other State Programs

| State | Portal | Notes |
|-------|--------|-------|
| Texas | DSHS dashboard | Weekly updates |
| North Carolina | covid19.ncdhhs.gov/dashboard/wastewater-monitoring | Includes measles |
| Virginia | vdh.virginia.gov | SARS-CoV-2 |

---

## European Sources

### EU Wastewater Observatory (JRC)

**Status**: ✅ Active (Launched January 2025)

| Property | Value |
|----------|-------|
| Dashboard | `https://wastewater-observatory.jrc.ec.europa.eu/` |
| Coverage | 11 EU countries |
| Pathogens | SARS-CoV-2, Influenza, RSV |
| Data Points | 1+ million measurements |

**Notes**:
- New dashboard launched January 29, 2025
- Developed by JRC with HERA
- Data standardization via recast Urban Wastewater Treatment Directive

### Germany RKI AMELAG

**Status**: ✅ Active

| Property | Value |
|----------|-------|
| Endpoint | `https://raw.githubusercontent.com/robert-koch-institut/Abwassersurveillance_AMELAG/main/Abwassersurveillance.csv` |
| Format | CSV (semicolon-separated) |
| Coverage | 16 German states (Bundesländer) |
| Update Frequency | Weekly |

**Key Fields**:
- `datum`: Date
- `bundesland`: State name
- `viruslast`: Viral load

### UK UKHSA

**Status**: ⚠️ API changes pending

| Property | Value |
|----------|-------|
| Legacy Portal | `https://coronavirus.data.gov.uk/` |
| Coverage | England, Wales, Scotland, Northern Ireland |

**Notes**:
- The coronavirus.data.gov.uk site was wound down in 2024
- Data may be available through UKHSA's new surveillance platforms

---

## Other International Sources

### WHO Wastewater Dashboard

| Property | Value |
|----------|-------|
| Portal | `https://data.who.int/dashboards/covid19/wastewater` |
| Coverage | 55+ countries (aggregated) |
| Notes | Links to official country dashboards |

### Canada (Ottawa)

| Property | Value |
|----------|-------|
| GitHub | `https://github.com/Big-Life-Lab/covid-19-wastewater` |
| Dashboard | 613covid.ca |
| Format | Open Data Model (ODM) |

### New Zealand (ESR)

| Property | Value |
|----------|-------|
| GitHub | `https://github.com/ESR-NZ/covid_in_wastewater` |
| Coverage | National wastewater program |
| Historical | 2021-2024 |

---

## Research Networks

### WastewaterSCAN (Stanford/Emory)

**Status**: ⚠️ No public API

| Property | Value |
|----------|-------|
| Dashboard | `https://data.wastewaterscan.org/` |
| Contact | info@wastewaterscan.org |
| Pathogens | SARS-CoV-2, Influenza, RSV, West Nile, Measles, Rotavirus, Adenovirus, Parvovirus |

**Notes**:
- Operated by Stanford and Emory universities
- Data primarily accessible via interactive dashboard
- Contact for API access: info@wastewaterscan.org
- Added West Nile (Oct 2025), Measles (May 2025)

### Biobot Analytics

**Status**: ⚠️ Request access required

| Property | Value |
|----------|-------|
| Portal | `https://biobot.io/data-access/` |
| Network | 400+ sites nationally |
| Pathogens | SARS-CoV-2, Influenza, RSV |

**Data Access**:
- Free Biobot Network program available
- Form submission required for data access
- Publishes weekly risk reports

---

## Data Quality Tiers

| Tier | Source Type | Quality Score | Update Lag |
|------|-------------|--------------|------------|
| 1 | Federal (CDC NWSS) | 0.95 | 3-7 days |
| 2 | Research Networks (WastewaterSCAN, Biobot) | 0.90 | 2-3 days |
| 3 | State Health Depts | 0.85 | 3-7 days |
| 4 | International (EU, RKI) | 0.85 | 7-14 days |
| 5 | WHO Aggregated | 0.75 | 14+ days |

---

## Integration Priority for Viral Weather

### Phase 1 (Immediate)
1. **CDC NWSS** - Primary US data, public API
2. **Germany RKI** - Primary EU data, GitHub CSV
3. **Massachusetts MWRA** - High-quality site data

### Phase 2 (Next)
1. **California Cal-SuWers** - State-level depth
2. **EU Observatory** - When API becomes available
3. **New Zealand ESR** - Southern hemisphere baseline

### Phase 3 (Future)
1. **WastewaterSCAN** - Request API access
2. **Biobot Network** - Apply for free tier
3. **Additional state programs** - As APIs mature

---

## References

- [CDC NWSS Main Page](https://www.cdc.gov/nwss/index.html)
- [CDC Wastewater Data Methodology](https://www.cdc.gov/nwss/data-methods.html)
- [EU Wastewater Observatory Launch](https://health.ec.europa.eu/latest-updates/launching-eu-wastewater-surveillance-dashboard-2025-01-29_en)
- [ECDC Framework for WBS Integration](https://www.ecdc.europa.eu/en/publications-data/ecdc-framework-guide-integration-wastewater-based-surveillance-infectious-disease)
- [Socrata API Documentation](https://dev.socrata.com/foundry/data.cdc.gov/2ew6-ywp6)
