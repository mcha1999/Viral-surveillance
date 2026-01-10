# Viral Weather PRD Analysis & Recommendations

## Executive Summary

This document provides a comprehensive analysis of the Viral Weather PRD with recommendations for MVP development. The platform aims to be "The Waze for Viral Avoidance" - a predictive radar for viral risk by fusing genomic, wastewater, and flight data.

### MVP Scope Constraints

| Constraint | MVP Scope |
|------------|-----------|
| **Platform** | Web only (mobile optionality preserved for future) |
| **Cloud** | Google Cloud Platform (GCP) |
| **Data Budget** | ≤$75/month for APIs/licenses |
| **Data Sources** | Public APIs and web-scrapable only |
| **Geographic** | Top 50 countries, granularity as data permits |
| **Deferred** | Accessibility (post-MVP), Pro tier, monetization, mobile app |

---

## 1. User Experience (UX) Enhancements

### 1.1 Critical UX Gaps (MVP Priorities)

| Gap | Risk | MVP Recommendation |
|-----|------|-------------------|
| No onboarding flow | High bounce rate | Simple location picker on first visit |
| No error states | User confusion | Comprehensive error state design |
| Alert fatigue | Users ignore notifications | Basic threshold controls |
| No keyboard nav | Power user friction | Essential shortcuts only |

*Note: Full WCAG 2.1 AA accessibility deferred to post-MVP*

### 1.2 Recommended UX (MVP)

#### A. Simplified Onboarding
```
First Visit Flow:
1. Globe loads with global "hot zones" view
2. Optional prompt: "Set your home location"
3. If set → zoom to home, show local risk
4. If skipped → remain on global view
```

#### B. Responsive Web (Mobile-Friendly, Not Native)
- **Breakpoints**: Desktop (1200px+), Tablet (768-1199px), Mobile (320-767px)
- **Mobile Web**: 2D map fallback (3D globe too heavy on mobile browsers)
- **Dossier Panel**: Bottom sheet on mobile, side panel on desktop
- **Future Mobile App**: React Native can share component logic

#### C. Basic Alert System (MVP)
```
MVP Alerts (In-App Only):
- Watchlist: Up to 5 locations (LocalStorage)
- Alert threshold: >50% week-over-week change
- Visual badge on watched locations

Post-MVP:
- Push notifications
- Email digests
- Configurable thresholds
```

#### D. Keyboard Shortcuts (MVP)
```
/        → Focus search
Esc      → Close panels
← →      → Navigate time scrubber
Space    → Play/pause animation
```

---

## 2. Design Specifications

### 2.1 UI States (Critical)

#### Empty States
| Scenario | Design |
|----------|--------|
| No data for region | "No surveillance data available for [Region]" + coverage map link |
| No flights from region | "Flight data unavailable" (hide arc layer) |
| Search no results | "No results found. Try a different spelling." |

#### Loading States
| Component | Pattern |
|-----------|---------|
| Globe initial | Skeleton globe + "Loading global data..." |
| Dossier panel | Gray placeholder blocks |
| Time scrubber | Optimistic UI + spinner |

#### Error States
| Type | Message | Recovery |
|------|---------|----------|
| API timeout | "Data temporarily unavailable" | Auto-retry 3x + manual refresh |
| Stale data (>48h) | Yellow banner with timestamp | Show anyway |
| Partial failure | "Some sources offline" | Show available data |
| Total failure | "Service unavailable" | Status page link |

### 2.2 User State (LocalStorage - No Auth for MVP)
```json
{
  "user_preferences": {
    "home_location": "loc_nyc_01",
    "watchlist": ["loc_lon_01", "loc_tok_01"],
    "units": "metric",
    "last_viewed": "2026-01-10T12:00:00Z"
  }
}
```

---

## 3. Architecture Hardening

### 3.1 Fault Tolerance

#### Circuit Breaker Pattern
```
CLOSED → OPEN (after 5 failures in 60s)
OPEN → HALF-OPEN (after 30s cooldown)
HALF-OPEN → CLOSED (after 3 successes)

Implementation: pybreaker (Python) or opossum (Node.js)
```

#### Graceful Degradation
| Failed Service | Degraded UX | User Message |
|----------------|-------------|--------------|
| Nextstrain | Show "Unknown Strain" | "Genomic data unavailable" |
| Wastewater | Show stale data with badge | "Data from [X] ago" |
| Flights | Hide vector layer | "Flight data offline" |
| All sources | Static snapshot | Full-page degraded banner |

### 3.2 Data Validation
```python
VALIDATION_RULES = {
    "wastewater_load": {"type": "float", "min": 0, "max": 10_000_000},
    "coordinates": {"lat": [-90, 90], "lon": [-180, 180]},
    "risk_score": {"min": 0, "max": 100},
    "timestamp": {"max_future": "24h", "max_past": "365d"}
}
```

### 3.3 Security (MVP)
```
No user accounts for MVP:
- All data is public/read-only
- Rate limiting by IP (100 req/min via Cloud Armor)
- HTTPS only, CORS restricted
- Input sanitization, parameterized queries
```

### 3.4 Observability (GCP-Native)
```
Cloud Monitoring: Request latency, error rates, data freshness
Cloud Logging: Structured JSON, correlation IDs
Cloud Alerting: Slack/PagerDuty for P0/P1
```

---

## 4. Resolved Decisions

| Decision | Resolution |
|----------|------------|
| Total budget | ~$150-250/mo (infra + data) approved |
| Data staleness | 14 days = show with warning, 30 days = hide |
| Legal disclaimer | Not required for MVP |
| Variant naming | Use Pango lineages (BA.2.86) as primary |

---

## 5. Technology Stack Summary

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Frontend** | Next.js 14 | SSR, great DX |
| **Globe** | Deck.gl + Mapbox GL JS | WebGL performance |
| **API** | Python FastAPI + GraphQL | Rapid development |
| **Tile Server** | pg_tileserv | Direct PostGIS → MVT |
| **Ingestion** | Cloud Functions (Python) | Serverless |
| **Primary DB** | Cloud SQL PostgreSQL 15 + PostGIS 3.4 | Managed, geospatial |
| **Cache** | Memorystore Redis | Low latency |
| **CDN** | Cloud CDN | Global edge |

---

## Related Documents

- [DATA_SOURCES.md](./DATA_SOURCES.md) - Detailed data source integration guide
- [ARCHITECTURE.md](./ARCHITECTURE.md) - GCP architecture specification
- [EDGE_CASES.md](./EDGE_CASES.md) - Edge case catalog
- [IMPLEMENTATION_PLAN.md](./IMPLEMENTATION_PLAN.md) - 16-week roadmap
