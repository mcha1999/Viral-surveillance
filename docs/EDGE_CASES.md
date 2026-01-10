# Edge Cases Catalog

This document catalogs edge cases identified during PRD analysis, along with detection methods and mitigation strategies.

---

## 1. Data Edge Cases

### 1.1 Anomalous Values

| Edge Case | Detection | Mitigation |
|-----------|-----------|------------|
| **Wastewater spike (non-viral)** | Value >3 standard deviations from rolling mean + no corroborating genomic data | Flag as "Anomaly - Unconfirmed" in UI, require manual verification before including in risk score |
| **Negative values** | Validation layer checks value >= 0 | Reject record, use last known good value, log error |
| **Null/missing values** | Schema validation | Use interpolation for time series, or exclude from calculations with "data unavailable" indicator |
| **Extreme outliers** | Value exceeds physical plausibility (e.g., >10M copies/L) | Cap at maximum threshold, flag for review |

### 1.2 Data Freshness

| Edge Case | Detection | Mitigation |
|-----------|-----------|------------|
| **Stale data (7-14 days)** | `timestamp < NOW() - 7 days` | Show with yellow warning badge: "Data from X days ago" |
| **Very stale data (14-30 days)** | `timestamp < NOW() - 14 days` | Show with red warning badge, reduce confidence weighting |
| **Expired data (>30 days)** | `timestamp < NOW() - 30 days` | Hide from display, exclude from risk calculations |
| **Future timestamps** | `timestamp > NOW() + 24h` | Reject as invalid, log error |

### 1.3 Source Integrity

| Edge Case | Detection | Mitigation |
|-----------|-----------|------------|
| **Duplicate events** | Same (location_id, timestamp, source) tuple | Dedup using composite key, keep most recent ingestion |
| **Source schema changes** | Ingestion adapter throws parsing errors | Circuit breaker opens, alert team, fall back to cached data |
| **Retroactive corrections** | Source republishes historical data with different values | Version all data, recalculate affected risk scores, show "revised" badge |
| **Source goes offline** | HTTP errors / timeouts for >1 hour | Circuit breaker, graceful degradation, show "source offline" in UI |

---

## 2. Geographic Edge Cases

### 2.1 Political/Administrative

| Edge Case | Challenge | Solution |
|-----------|-----------|----------|
| **Territories** (Puerto Rico, Hong Kong, Macau) | Ambiguous relationship to parent country | Use ISO 3166-2 codes, display as sub-national entity, allow parent country fallback |
| **Disputed regions** (Crimea, Kashmir, Taiwan) | Geopolitical sensitivity | Default to UN designation, avoid taking political positions, use neutral naming |
| **City name collisions** | "Springfield" exists in 30+ countries, "San Jose" in multiple countries | Always display with country/admin1 in disambiguation, use unique location_id |
| **Cross-border metros** | Cities spanning borders (e.g., El Paso/Juárez) | Create "metro area" composite nodes that aggregate data from both sides |

### 2.2 Coverage Gaps

| Edge Case | Challenge | Solution |
|-----------|-----------|----------|
| **No data for country** | User expects global coverage | Clear "No surveillance data" state, show on coverage map, don't interpolate |
| **Partial country coverage** | Only major cities have data | Show data points that exist, clearly indicate limited coverage |
| **Airport-to-metro mapping** | JFK serves NYC, NJ, CT | Map airports to primary metro, note catchment area in metadata |

### 2.3 Coordinate Edge Cases

| Edge Case | Challenge | Solution |
|-----------|-----------|----------|
| **Antimeridian crossing** | 180° longitude wrap-around | Use proper GeoJSON handling, normalize longitudes to [-180, 180] |
| **Polar regions** | Map projections distort, low population | Exclude from globe visualization, note as "not applicable" |
| **Ocean/international waters** | No fixed location | For cruise ships, track as mobile nodes linked to departure port |

---

## 3. Temporal Edge Cases

### 3.1 Time Handling

| Edge Case | Challenge | Solution |
|-----------|-----------|----------|
| **DST transitions** | Time series gaps or overlaps | Store all timestamps in UTC, convert to local time only on display |
| **Missing timezone info** | Raw data lacks TZ specification | Assume source's local timezone, document assumption, prefer sources with explicit TZ |
| **Date-only timestamps** | No time component, ambiguous | Default to 00:00:00 UTC of that date, flag as low-precision |

### 3.2 Reporting Patterns

| Edge Case | Challenge | Solution |
|-----------|-----------|----------|
| **Variable reporting lag** | US: 3 days, EU: 7 days, others: 14+ days | Per-source lag coefficient in freshness calculation, display expected next update |
| **Weekend gaps** | Many sources don't publish weekends | Interpolate for display continuity, note "estimated" values |
| **Holiday gaps** | Extended gaps around holidays | Show last known data with extended staleness warning |
| **Batch corrections** | Source publishes large retroactive update | Process incrementally, version data, highlight "revised" data points |

### 3.3 Time Scrubber

| Edge Case | Challenge | Solution |
|-----------|-----------|----------|
| **Rapid scrubbing** | User drags slider quickly, spamming API | Client-side debounce (300ms), request coalescing on backend |
| **Historical data gaps** | No data for certain dates | Interpolate for visualization, show gap indicator |
| **Future projection limits** | Forecast accuracy degrades rapidly | Limit forecast to 7 days, show confidence bands that widen over time |

---

## 4. Scale Edge Cases

### 4.1 Traffic Spikes

| Scenario | Challenge | Solution |
|----------|-----------|----------|
| **Pandemic surge** | 10x normal traffic | Cloud Run auto-scaling, CDN caching for tiles, read replicas |
| **Breaking news event** | Everyone searches same location | Request coalescing, aggressive caching (5-min TTL), consistent hashing |
| **DDoS attack** | Malicious traffic flood | Cloud Armor WAF, rate limiting (100 req/min per IP), geographic filtering |

### 4.2 Data Volume

| Scenario | Challenge | Solution |
|----------|-----------|----------|
| **Nextstrain metadata** | ~2GB compressed, daily updates | Incremental sync, track last processed date, stream processing |
| **Historical backfill** | Loading years of historical data | Batch processing during off-peak, progress indicators |
| **Arc explosion** | 10,000+ flight routes to render | Filter by risk threshold, LOD (Level of Detail) based on zoom, GPU-based rendering |

### 4.3 Resource Limits

| Scenario | Challenge | Solution |
|----------|-----------|----------|
| **Mobile browser memory** | 3D globe + large datasets | Fallback to 2D map on mobile, aggressive data decimation |
| **LocalStorage limits** | 5-10MB browser limit | Prune old data, use IndexedDB for larger storage needs |
| **API rate limits** | External APIs have quotas | Implement caching, respect rate limits, queue requests |

---

## 5. User Experience Edge Cases

### 5.1 Input Validation

| Edge Case | Challenge | Solution |
|-----------|-----------|----------|
| **Invalid search query** | SQL injection, XSS attempts | Input sanitization, parameterized queries, CSP headers |
| **Empty search results** | User types obscure location | Suggest alternatives, show "no results" with helpful message |
| **Partial location match** | "New York" matches city and state | Show disambiguation UI with clear options |

### 5.2 Browser Compatibility

| Edge Case | Challenge | Solution |
|-----------|-----------|----------|
| **WebGL not supported** | Older browsers, some mobile | Detect capability, fallback to static image map |
| **JavaScript disabled** | Rare but possible | Server-render basic content, show "enable JS" message |
| **Slow connection** | High latency, low bandwidth | Progressive loading, skeleton states, service worker caching |

### 5.3 Accessibility (Post-MVP)

| Edge Case | Challenge | Solution |
|-----------|-----------|----------|
| **Screen reader** | 3D globe not accessible | ARIA labels for key data, text alternative view |
| **Color blindness** | Red/green risk colors | Use patterns + colors, ensure sufficient contrast |
| **Reduced motion** | Animations cause discomfort | Respect `prefers-reduced-motion`, disable pulse effects |
| **Keyboard navigation** | Mouse-centric globe | Tab navigation, keyboard shortcuts, focus indicators |

---

## 6. Integration Edge Cases

### 6.1 External API Failures

| Edge Case | Detection | Mitigation |
|-----------|-----------|------------|
| **AviationStack down** | 5xx errors or timeouts | Circuit breaker, serve cached flight data, hide arc layer after 24h |
| **CDC API changes** | Parsing errors, missing fields | Version adapters, alert on schema changes, fallback to last good data |
| **Nextstrain unavailable** | Download failures | Local cache, retry with exponential backoff, show "genomic data unavailable" |

### 6.2 Data Conflicts

| Edge Case | Challenge | Solution |
|-----------|-----------|----------|
| **Sources disagree** | Two sources report different values for same metric | Prefer higher-granularity source, prefer more recent, log conflict for review |
| **Overlapping coverage** | Multiple sources for same region | Deduplicate, merge with priority rules, track data provenance |

---

## 7. Error Recovery Matrix

| Error State | User Experience | Auto-Recovery | Manual Recovery |
|-------------|-----------------|---------------|-----------------|
| Single API timeout | Retry indicator, then error message | 3 automatic retries with backoff | Refresh button |
| Data source offline | Banner: "Some data unavailable" | Check every 5 minutes | None needed |
| All data sources offline | Full-page degraded mode | Check every minute | Status page link |
| Invalid user input | Inline validation error | N/A | User corrects input |
| LocalStorage full | Warning toast | Auto-prune old data | Clear watchlist |
| WebGL crash | Fallback to 2D map | N/A | Reload page |

---

## 8. Monitoring Alerts for Edge Cases

```python
EDGE_CASE_ALERTS = {
    "data_anomaly": {
        "condition": "wastewater_value > 3 * rolling_std",
        "severity": "P2",
        "action": "flag_for_review"
    },
    "source_stale": {
        "condition": "last_update > 24h",
        "severity": "P1",
        "action": "slack_alert"
    },
    "schema_change": {
        "condition": "ingestion_parse_error_rate > 50%",
        "severity": "P1",
        "action": "pagerduty"
    },
    "traffic_spike": {
        "condition": "rps > 10 * baseline",
        "severity": "P2",
        "action": "scale_up"
    }
}
```
