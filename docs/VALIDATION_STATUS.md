# Risk Modeling Validation Status

**Last Updated**: January 2026
**Status**: Partially Validated (Simulated Data Only)

## Executive Summary

The Viral Weather risk modeling has undergone preliminary validation using epidemiologically realistic simulated data. While the simulation-based tests show promise for certain hypotheses, **real-world validation with actual wastewater surveillance data is required** before production deployment.

| Hypothesis | Simulated Result | Real Data Status |
|------------|------------------|------------------|
| H1: Import pressure predicts variant arrival | ✅ Passed | ⏳ Pending |
| H2: Risk score predicts wastewater surge | ❌ Failed | ⏳ Pending |
| H3: High connectivity = faster propagation | ✅ Passed | ⏳ Pending |
| H4: Lead time analysis | ✅ Passed (60 days) | ⏳ Pending |

---

## What Has Been Validated (Simulated Data)

### H1: Import Pressure Predicts Variant Arrival Timing ✅

**Result**: Strong correlation found

| Variant | Correlation | P-value | Significant |
|---------|-------------|---------|-------------|
| JN.1 | 0.99 | <0.001 | ✅ |
| BA.2.86 | 0.87 | <0.001 | ✅ |
| EG.5 | -0.93* | <0.001 | ✅ |

*Negative correlation indicates inverse pattern - may reflect different emergence dynamics.

**Interpretation**: High-connectivity hubs (NY, CA, GA, TX, IL) consistently see variants arrive earlier than low-connectivity states.

### H3: High Import Pressure = Faster Propagation ✅

**Result**: 49-day difference in reaching 50% variant prevalence

- High-pressure locations: 119 days median
- Low-pressure locations: 168 days median
- P-value: <0.001 (Mann-Whitney U test)

**Interpretation**: Flight connectivity meaningfully accelerates variant spread within the US.

### Lead Time Analysis ✅

**Result**: 60 days median advance warning

- 100% of locations received warning before variant arrival
- Risk threshold used: 40/100
- Actionable for public health planning

---

## What Has NOT Been Validated ❌

### H2: Risk Score Predicts Wastewater Surge ❌ FAILED

**This is the critical failure.**

| Metric | Value | Baseline | Difference |
|--------|-------|----------|------------|
| Directional Accuracy | 28.8% | 50% (random) | -21.2% |
| RMSE | 93.05 | 71.60 (naive) | +30% worse |

**Root Cause Analysis**:
The current risk score formula (40% wastewater + 30% velocity + 30% import) does NOT effectively predict future wastewater levels. This undermines the core predictive claim.

**Recommended Fixes**:
1. Add seasonality factors (respiratory virus cycles)
2. Incorporate population immunity estimates
3. Use variant-specific transmissibility multipliers
4. Consider using ensemble methods instead of linear combination

### Real Data Validation ❌ NOT DONE

All validation was performed on **simulated data** from `analysis/realistic_simulation.py`. While the simulation was designed to mirror real patterns from CDC NWSS, GISAID, and flight data, it is not a substitute for actual validation.

**Data Sources Ready for Integration**:
- ✅ CDC NWSS: `data.cdc.gov/resource/2ew6-ywp6.json`
- ✅ Germany RKI: GitHub CSV available
- ✅ Massachusetts MWRA: Biobot data available
- ⚠️ EU Observatory: Dashboard live, API pending
- ⚠️ WastewaterSCAN: Requires contact for API access

---

## Wastewater ↔ Other Data Relationships

### Current Architecture

```
Risk Score = (0.40 × Wastewater Load) + (0.30 × Velocity) + (0.30 × Import Pressure)
                    ↑                         ↑                      ↑
            CDC NWSS data            Derived from WW        Flight data × origin risk
```

### Missing Relationships

| Relationship | Current Status | Impact |
|--------------|---------------|--------|
| Wastewater ↔ Genomic Sequences | Schema exists, no integration | Cannot confirm variants |
| Wastewater ↔ Hospitalizations | Not implemented | No severity weighting |
| Wastewater ↔ Case Rates | Not validated | Lead time unproven |
| Flight Passengers ↔ Actual Counts | Estimated from aircraft type | May be inaccurate |

### Recommended Connections

1. **Nextstrain/GISAID Integration**: Cross-validate wastewater variant spikes with genomic data
2. **CDC Hospital Admissions**: Add severity component to risk score
3. **State-Level Case Rates**: Validate wastewater as leading indicator
4. **OAG/Cirium Flight Data**: Replace estimated passenger counts with actual data

---

## Validation Roadmap

### Phase 1: Real Data Connection (Immediate)

- [ ] Test CDC NWSS API with real queries
- [ ] Fetch 12+ months of historical wastewater data
- [ ] Integrate Germany RKI data for EU coverage
- [ ] Connect Massachusetts MWRA Biobot data

### Phase 2: Retrospective Validation (Week 1-2)

- [ ] Run H1-H4 tests against real data
- [ ] Compare simulated vs actual variant emergence patterns
- [ ] Validate velocity calculation against CDC-reported changes
- [ ] Measure actual lead time for historical surges

### Phase 3: Model Recalibration (Week 2-3)

- [ ] Address H2 failure (risk score prediction)
- [ ] Test alternative formulas (ensemble, ML-based)
- [ ] Add seasonality and immunity factors
- [ ] Re-run validation with updated model

### Phase 4: Cross-Source Validation (Week 3-4)

- [ ] Integrate Nextstrain for variant confirmation
- [ ] Cross-validate wastewater spikes with case data
- [ ] Add confidence scoring based on data agreement
- [ ] Document edge cases and mitigation

---

## Technical Debt

| Issue | Priority | Effort |
|-------|----------|--------|
| CDC dataset ID needs update (g653-rqe2 → 2ew6-ywp6) | ✅ Fixed | Done |
| UK UKHSA adapter uses case rates, not wastewater | High | 2 days |
| No rate limiting on API calls | Medium | 1 day |
| Missing retry logic for network failures | Medium | 1 day |
| No data quality scoring per source | Medium | 2 days |

---

## Conclusion

The risk modeling framework shows promise based on simulated data, particularly for:
- Predicting variant arrival timing based on air travel connectivity
- Identifying high-risk locations through import pressure analysis
- Providing advance warning for variant spread

However, **production deployment should be gated on**:
1. Successful validation with real CDC NWSS data
2. Resolution of the H2 prediction accuracy failure
3. Integration of at least one secondary data source for redundancy

The infrastructure for real data validation is now in place. The next step is to execute the validation with actual historical wastewater data.
