# Data Source Audit - January 2026

## 🚨 CRITICAL FINDING: Mixed Real/Synthetic Data

The production system is operating in a **hybrid state** where:
1. Data ingestion adapters CAN fetch real data, but have silent synthetic fallbacks
2. API endpoints serving the frontend **bypass the database entirely** and generate synthetic data
3. No monitoring exists to detect when synthetic fallbacks activate

---

## Adapter-Level Audit

| Source | Intended | Adapter Status | Synthetic Fallback | Risk |
|--------|----------|----------------|-------------------|------|
| **CDC NWSS** | Real US wastewater | ✅ Real API | ❌ None | Dataset ID was wrong (fixed) |
| **AviationStack** | Real flight data | ⚠️ Conditional | ✅ **Line 169-171**: If no API key, returns synthetic | **HIGH** - No key = fake data |
| **UK UKHSA** | Real UK wastewater | ⚠️ Wrong metric | ❌ None | Uses case rates, not wastewater |
| **NL RIVM** | Real NL wastewater | ✅ Real API | ❌ None | Good |
| **DE RKI** | Real DE wastewater | ✅ Real API | ❌ None | Good |
| **JP NIID** | Real JP wastewater | ⚠️ Conditional | ✅ **Line 119-120**: On HTTP error | **MEDIUM** - Silent fallback |
| **FR DataGouv** | Real FR wastewater | ⚠️ Conditional | ✅ **Line 81-83**: On HTTP error | **MEDIUM** - Silent fallback |
| **AU Health** | Real AU wastewater | ⚠️ Conditional | ✅ **Line 96-97**: On HTTP error | **MEDIUM** - Silent fallback |

---

## API Endpoint Audit

| Endpoint | Database Query? | Actual Behavior | Risk |
|----------|----------------|-----------------|------|
| `GET /api/risk/{location_id}` | ✅ Yes | Queries `surveillance_events` | Good (if DB populated) |
| `GET /api/risk/summary/global` | ✅ Yes | Queries `risk_scores` | Good (if DB populated) |
| `GET /api/flights/arcs` | ❌ **NO** | `generate_synthetic_arcs()` | **CRITICAL** |
| `GET /api/flights/import-pressure/{id}` | ❌ **NO** | Uses synthetic arcs | **CRITICAL** |
| `GET /api/history` | ❌ **NO** | `generate_historical_data()` | **CRITICAL** |
| `GET /api/history/timeseries/{id}` | ❌ **NO** | `generate_historical_data()` | **CRITICAL** |
| `GET /api/history/compare` | ❌ **NO** | `generate_historical_data()` | **CRITICAL** |
| `GET /api/history/summary` | ❌ **NO** | `generate_historical_data()` | **CRITICAL** |

---

## Silent Synthetic Fallback Code Locations

### aviationstack.py:169-171
```python
if not self.api_key:
    # Return synthetic data if no API key
    return self._generate_synthetic_flights(departure_iata, arrival_iata)
```

### jp_niid.py:117-120
```python
except httpx.HTTPError as e:
    self.logger.warning(f"Failed to fetch NIID data: {e}")
    # Return synthetic data for demo
    return self._generate_synthetic_data()
```

### fr_datagouv.py:80-83
```python
except httpx.HTTPError as e:
    self.logger.warning(f"Failed to fetch data.gouv.fr data: {e}")
    # Return synthetic data for demo purposes
    return self._generate_synthetic_data()
```

### au_health.py:93-97
```python
except httpx.HTTPError as e:
    self.logger.warning(f"Failed to fetch AU Health API data: {e}")

# Fallback to synthetic data
return self._generate_synthetic_data()
```

### flights.py:194-196
```python
# For MVP, generate synthetic data
# In production, this would query the database populated by AviationStack adapter
arcs = generate_synthetic_arcs(...)
```

### history.py:161-163
```python
# For MVP, generate synthetic data
# In production, this would query the database
data = generate_historical_data(...)
```

---

## Original Scope vs Implementation

### Wastewater (Intended: 14+ countries)

| Country | Source | Intended | Actual |
|---------|--------|----------|--------|
| 🇺🇸 USA | CDC NWSS | Real | ⚠️ Old dataset ID (fixed) |
| 🇬🇧 UK | UKHSA | Wastewater | ❌ Case rates as proxy |
| 🇳🇱 Netherlands | RIVM | Real | ✅ Real |
| 🇩🇪 Germany | RKI | Real | ✅ Real |
| 🇫🇷 France | data.gouv | Real | ⚠️ Synthetic fallback |
| 🇯🇵 Japan | NIID | Real | ⚠️ Synthetic fallback |
| 🇦🇺 Australia | health.gov.au | Real | ⚠️ Synthetic fallback |
| 🇪🇸 Spain | ISCIII | Real | ❌ Not implemented |
| 🇮🇹 Italy | ISS | Real | ❌ Not implemented |
| 🇦🇹 Austria | AGES | Real | ❌ Not implemented |
| 🇨🇭 Switzerland | BAG | Real | ❌ Not implemented |
| 🇧🇪 Belgium | Sciensano | Real | ❌ Not implemented |
| 🇩🇰 Denmark | SSI | Real | ❌ Not implemented |
| 🇨🇦 Canada | HC-SC | Real | ❌ Not implemented |
| 🇳🇿 New Zealand | ESR | Real | ❌ Not implemented |
| 🇸🇬 Singapore | NEA | Real | ❌ Not implemented |
| 🇰🇷 South Korea | KDCA | Real | ❌ Not implemented |
| 🇧🇷 Brazil | Fiocruz | Real | ❌ Not implemented |

### Genomic Data (Intended: Nextstrain)

| Source | Intended | Actual |
|--------|----------|--------|
| Nextstrain tree | Daily variant tracking | ❌ **Not implemented** |
| Nextstrain metadata | Sequence locations | ❌ **Not implemented** |
| GISAID (via Nextstrain) | Variant classification | ❌ **Not implemented** |

### Flight Data (Intended: AviationStack + OpenSky)

| Source | Intended | Actual |
|--------|----------|--------|
| AviationStack | Real routes | ⚠️ Requires API key, synthetic fallback |
| OpenSky | Validation | ❌ **Not implemented** |

---

## Required Fixes

### Priority 1: Fix API Endpoints (CRITICAL)

1. **flights.py**: Replace `generate_synthetic_arcs()` with database query
2. **history.py**: Replace `generate_historical_data()` with database query

### Priority 2: Remove Silent Fallbacks (HIGH)

1. Remove synthetic data generation from adapters
2. If API fails, raise error and alert - don't silently return fake data
3. Add data source health monitoring

### Priority 3: Fix UK Adapter (MEDIUM)

1. UKHSA adapter uses case rates, not actual wastewater data
2. Update to use correct wastewater endpoint or note as "proxy data"

### Priority 4: Implement Missing Sources (LOW)

1. Nextstrain genomic data integration
2. Additional EU countries (Spain, Italy, Austria, etc.)
3. OpenSky for flight validation

---

## Validation Impact

**ALL VALIDATION PERFORMED TO DATE IS INVALID** because:
1. The validation framework used simulated data
2. The production system serves synthetic data from API endpoints
3. No real data has been verified to be flowing through the pipeline

**Before any validation can be considered valid, we must:**
1. Confirm Cloud Functions are actually executing
2. Verify database contains real surveillance events
3. Update API endpoints to query actual data
4. Remove all synthetic fallbacks or make them explicit
