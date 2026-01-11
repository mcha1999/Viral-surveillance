# Retrospective Validation Methodology

> **Purpose**: Determine if Viral Weather's flight-based import pressure model provides meaningful predictive signal for variant spread.

---

## Executive Summary

Before scaling the product, we need empirical evidence that:
1. Flight data correlates with variant arrival patterns
2. Our risk scores predict actual viral activity changes
3. The model provides actionable lead time for users

This document outlines the validation framework implemented in `analysis/retrospective_validation.py`.

---

## Data Requirements

### Minimum Historical Data Needed

| Dataset | Source | Timeframe | Granularity |
|---------|--------|-----------|-------------|
| Wastewater surveillance | CDC NWSS | 12-24 months | Weekly, ~1,300 US sites |
| Variant sequences | GISAID/Nextstrain | 12-24 months | Daily, country/state level |
| Flight schedules | AviationStack/OAG | 12-24 months | Daily, route level |

### Data Schema

```
wastewater_df:
  - location_id: string (e.g., "NYC", "LAX")
  - date: datetime
  - viral_load: float (copies/mL)
  - pct_change_weekly: float (-100 to +∞)

variant_df:
  - location: string
  - date: datetime
  - variant: string (e.g., "JN.1", "BA.2.86")
  - sequence_count: int

flight_df:
  - origin: string
  - destination: string
  - date: datetime
  - passengers: int (estimated)
```

---

## Hypothesis Tests

### H1: Import Pressure Predicts Variant Arrival

**Question**: Do locations with more flights from infected areas see variants arrive earlier?

**Methodology**:
```
For each variant:
  1. Identify first detection date per location
  2. Calculate average import pressure in 30 days before detection
  3. Rank locations by detection order
  4. Compute Spearman correlation: import_pressure vs detection_rank
```

**Expected Result**:
- **Negative correlation** (r < -0.3): Higher pressure → earlier arrival (lower rank)
- p-value < 0.05 for statistical significance

**Interpretation**:
| Correlation | Interpretation |
|-------------|----------------|
| r < -0.5 | Strong predictive signal |
| -0.5 ≤ r < -0.3 | Moderate signal, useful for alerts |
| -0.3 ≤ r < 0 | Weak signal, directionally correct |
| r ≥ 0 | No predictive value from flights |

---

### H2: Risk Score Predicts Wastewater Surge

**Question**: Does our composite risk score predict future wastewater changes?

**Methodology**:
```
For each location-date pair:
  1. Calculate risk score (import_pressure × 0.6 + current_trend × 0.4)
  2. Measure actual wastewater change over next 14 days
  3. Compute RMSE and directional accuracy vs baselines
```

**Baselines**:
1. **Naive (no change)**: Predict wastewater stays the same
2. **Persistence**: Predict last week's change continues

**Success Criteria**:
| Metric | Threshold | Why |
|--------|-----------|-----|
| Directional accuracy | > 60% | Better than coin flip |
| RMSE | < baseline | Outperform naive model |
| RMSE improvement | > 10% | Meaningful improvement |

**What We Learn**:
- If directional accuracy < 55%: Risk score formula needs recalibration
- If RMSE > baseline: Model is adding noise, not signal
- If both pass: Formula is sound, consider adding more factors

---

### H3: Propagation Speed by Import Pressure

**Question**: Do high-traffic destinations see faster variant growth?

**Methodology**:
```
For a specific variant (e.g., JN.1):
  1. Split locations into high/low import pressure groups (75th vs 25th percentile)
  2. Measure days from first detection to 50% prevalence
  3. Compare groups with Mann-Whitney U test
```

**Success Criteria**:
- High-pressure group reaches 50% prevalence faster
- p-value < 0.05 (statistically significant)
- Effect size > 7 days (practically meaningful)

**Example Output**:
```
High-pressure locations: median 21 days to 50% prevalence
Low-pressure locations:  median 35 days to 50% prevalence
Effect size: 14 days faster
p-value: 0.003 (significant)
```

---

### Lead Time Analysis

**Question**: How much advance warning does the model provide?

**Methodology**:
```
For each location where variant arrived:
  1. Find first date when risk score exceeded threshold (e.g., 60)
  2. Compare to actual variant detection date
  3. Lead time = detection_date - warning_date
```

**Success Criteria**:
| Lead Time | Actionability |
|-----------|---------------|
| < 3 days | Too late for meaningful action |
| 3-7 days | Minimal awareness, limited action |
| 7-14 days | Useful for travel planning, public health prep |
| 14-30 days | High value, strategic planning possible |
| > 30 days | May have false positive concerns |

---

## Validation Report Structure

```json
{
  "summary": {
    "total_tests": 4,
    "passed": 3,
    "failed": 1,
    "pass_rate": 0.75,
    "overall_verdict": "VALIDATED"
  },
  "results": [
    {
      "hypothesis": "H1: Import pressure predicts variant arrival",
      "test": "Spearman rank correlation",
      "metric": "Average correlation",
      "value": -0.42,
      "p_value": 0.008,
      "passed": true,
      "details": {...}
    }
  ],
  "recommendations": [
    "Consider adding layover flight patterns for better coverage"
  ]
}
```

---

## Decision Framework

Based on validation results:

| Outcome | Pass Rate | Action |
|---------|-----------|--------|
| **VALIDATED** | ≥ 70% | Proceed with product, iterate on failed tests |
| **PARTIALLY VALIDATED** | 50-69% | Prioritize improving weak areas before scaling |
| **NOT VALIDATED** | < 50% | Fundamental approach may need rethinking |

---

## Improving Validation Confidence

### Additional Tests to Consider

1. **Cross-validation across time periods**
   - Train on 2023 data, test on 2024
   - Ensures model isn't overfitting to specific variant behavior

2. **Geographic holdout**
   - Exclude 20% of locations from training
   - Test predictions on held-out locations

3. **Variant-specific analysis**
   - Some variants may spread differently (immune evasion vs transmissibility)
   - Stratify results by variant characteristics

4. **Sensitivity analysis**
   - Vary import pressure lookback window (7, 14, 30 days)
   - Vary risk score weights
   - Identify optimal parameters

### Additional Data Sources to Improve Model

| Data Source | What It Adds | Effort |
|-------------|--------------|--------|
| Google/Apple mobility | Local transmission proxy | Medium |
| Hospital admissions | Severity signal | Medium |
| Seroprevalence surveys | Population immunity | High |
| Social media trends | Early detection proxy | Medium |
| Climate data | Seasonality adjustment | Low |

---

## Running the Validation

```bash
# With real data (replace paths)
cd /home/user/Viral-surveillance
python analysis/retrospective_validation.py \
  --wastewater data/nwss_historical.csv \
  --variants data/gisaid_sequences.csv \
  --flights data/aviationstack_2023_2024.csv

# With synthetic data (for testing framework)
python analysis/retrospective_validation.py
```

---

## Interpreting Results for Stakeholders

### If Validation Passes

> "Our analysis of 24 months of historical data shows that flight-based import pressure correlates with variant arrival timing (r=-0.42, p<0.01).
> The model provides a median 12 days advance warning before variants reach new locations.
> This validates the core premise that travel patterns are a useful predictor of viral spread."

### If Validation Fails

> "Initial validation shows weaker-than-expected correlation between flight patterns and variant spread.
> This may be due to: (1) domestic transmission outpacing imports, (2) flight data granularity limitations, or (3) variant-specific behavior.
> We recommend: improving data sources, adding local transmission signals, or focusing on international-only routes where import signal is stronger."

---

## Next Steps After Validation

1. **If validated**:
   - Document findings in blog post / white paper
   - Add confidence intervals to user-facing predictions
   - Build continuous monitoring for model drift

2. **If not validated**:
   - Identify weakest hypothesis
   - Explore alternative data sources
   - Consider pivoting to simpler use case (monitoring vs prediction)

---

*Last updated: January 2026*
