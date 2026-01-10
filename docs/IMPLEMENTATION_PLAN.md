# Implementation Plan

## Overview

16-week implementation plan divided into 4 phases, building from foundation to production-ready MVP.

---

## Phase 1: Foundation (Weeks 1-4)

**Goal**: Static wastewater heatmap for US + 10 countries
**Deliverable**: Basic globe with CDC NWSS data rendering

### Week 1: Infrastructure Setup

| Task | Owner | Tech | Priority |
|------|-------|------|----------|
| Create GCP project + enable APIs | DevOps | GCP Console | P0 |
| Set up Terraform for IaC | DevOps | Terraform | P0 |
| Deploy Cloud SQL (PostgreSQL + PostGIS) | DevOps | Cloud SQL | P0 |
| Create database schema | Backend | SQL | P0 |
| Set up Cloud Storage buckets | DevOps | GCS | P1 |

**Deliverables**:
- [ ] GCP project with billing enabled
- [ ] Cloud SQL instance running PostgreSQL 15 + PostGIS
- [ ] Database schema deployed (location_nodes, surveillance_events)
- [ ] Terraform configs in version control

### Week 2: Data Ingestion (US)

| Task | Owner | Tech | Priority |
|------|-------|------|----------|
| Build CDC NWSS adapter | Data Eng | Python | P0 |
| Deploy as Cloud Function | Data Eng | Cloud Functions | P0 |
| Set up Cloud Scheduler trigger | Data Eng | Cloud Scheduler | P0 |
| Implement H3 indexing | Backend | h3-py | P0 |
| Create data validation layer | Backend | Pydantic | P1 |

**Deliverables**:
- [ ] CDC adapter fetching and normalizing data
- [ ] Cloud Function deployed and scheduled (Tue/Thu 6am UTC)
- [ ] Data flowing into Cloud SQL with H3 indexes
- [ ] Validation rules catching invalid data

### Week 3: Frontend Foundation

| Task | Owner | Tech | Priority |
|------|-------|------|----------|
| Initialize Next.js 14 project | Frontend | Next.js | P0 |
| Set up Deck.gl + Mapbox GL | Frontend | Deck.gl | P0 |
| Create basic globe component | Frontend | React | P0 |
| Implement location markers | Frontend | Deck.gl ScatterplotLayer | P0 |
| Deploy to Cloud Run | DevOps | Cloud Run | P1 |

**Deliverables**:
- [ ] Next.js project with Deck.gl rendering globe
- [ ] Location markers displaying on globe
- [ ] Deployed and accessible via Cloud Run URL

### Week 4: API Layer

| Task | Owner | Tech | Priority |
|------|-------|------|----------|
| Create FastAPI project structure | Backend | FastAPI | P0 |
| Implement /api/locations endpoint | Backend | FastAPI | P0 |
| Implement /api/locations/{id} endpoint | Backend | FastAPI | P0 |
| Set up pg_tileserv for MVT tiles | Backend | pg_tileserv | P1 |
| Connect frontend to API | Frontend | React Query | P0 |

**Deliverables**:
- [ ] REST API serving location data
- [ ] Tile endpoint serving MVT
- [ ] Frontend displaying real CDC data on globe

---

## Phase 2: Global Expansion + Flights (Weeks 5-8)

**Goal**: Top 30 countries + flight arcs
**Deliverable**: Global coverage with flight vector visualization

### Week 5: European Data Sources

| Task | Owner | Tech | Priority |
|------|-------|------|----------|
| Build UK UKHSA adapter | Data Eng | Python | P0 |
| Build Netherlands RIVM adapter | Data Eng | Python | P0 |
| Build Germany RKI adapter | Data Eng | Python | P1 |
| Build France data.gouv adapter | Data Eng | Python | P1 |
| Add adapters to scheduler | Data Eng | Cloud Scheduler | P0 |

**Deliverables**:
- [ ] 4 European country adapters operational
- [ ] Data ingesting on MWF 8am UTC schedule
- [ ] European locations appearing on globe

### Week 6: APAC + Americas Data Sources

| Task | Owner | Tech | Priority |
|------|-------|------|----------|
| Build Japan NIID adapter | Data Eng | Python | P0 |
| Build Australia adapter | Data Eng | Python | P0 |
| Build Canada adapter | Data Eng | Python | P1 |
| Build Brazil Fiocruz adapter | Data Eng | Python | P1 |
| Create adapter template/framework | Data Eng | Python | P0 |

**Deliverables**:
- [ ] APAC + Americas adapters operational
- [ ] Reusable adapter framework for remaining countries
- [ ] ~20 countries with data

### Week 7: Flight Data Integration

| Task | Owner | Tech | Priority |
|------|-------|------|----------|
| Set up AviationStack integration | Data Eng | Python | P0 |
| Build flight route caching layer | Backend | Redis | P0 |
| Implement passenger estimation | Data Eng | Python | P1 |
| Create vector_arcs table + ingestion | Backend | SQL, Python | P0 |
| Build OpenSky validation adapter | Data Eng | Python | P2 |

**Deliverables**:
- [ ] Flight data ingesting every 6 hours
- [ ] Top 500 routes cached in Redis
- [ ] Passenger estimates calculated

### Week 8: Flight Visualization

| Task | Owner | Tech | Priority |
|------|-------|------|----------|
| Implement Deck.gl ArcLayer | Frontend | Deck.gl | P0 |
| Add arc filtering by risk | Frontend | React | P0 |
| Build time scrubber component | Frontend | React | P0 |
| Implement 30-day history view | Frontend | React Query | P0 |
| Add arc animation (particles) | Frontend | Deck.gl | P2 |

**Deliverables**:
- [ ] Flight arcs rendering on globe
- [ ] Time scrubber navigating 30-day history
- [ ] Arcs filtered by source risk level

---

## Phase 3: Intelligence (Weeks 9-12)

**Goal**: Risk scores + basic forecasting
**Deliverable**: Calculated risk scores, variant data, basic predictions

### Week 9: Nextstrain Integration

| Task | Owner | Tech | Priority |
|------|-------|------|----------|
| Build Nextstrain metadata sync | Data Eng | Python | P0 |
| Implement incremental sync logic | Data Eng | Python | P0 |
| Extract variant/clade data | Data Eng | Python | P0 |
| Map variants to locations | Backend | SQL | P0 |
| Store genomic events | Backend | PostgreSQL | P0 |

**Deliverables**:
- [ ] Nextstrain metadata syncing daily
- [ ] Variant data stored and queryable
- [ ] Locations annotated with dominant variants

### Week 10: Risk Score Engine

| Task | Owner | Tech | Priority |
|------|-------|------|----------|
| Design risk score algorithm | Data Science | Python | P0 |
| Implement risk calculation | Backend | Python, NumPy | P0 |
| Create materialized view for scores | Backend | PostgreSQL | P0 |
| Add hourly refresh schedule | Backend | Cloud Scheduler | P0 |
| Build /api/risk/{id} endpoint | Backend | FastAPI | P0 |

**Risk Score Formula**:
```python
risk_score = (
    0.4 * wastewater_load_normalized +
    0.3 * growth_velocity +
    0.3 * import_pressure
) * 100
```

**Deliverables**:
- [ ] Risk scores calculated hourly
- [ ] API returning risk scores
- [ ] Frontend displaying risk scores in UI

### Week 11: Forecasting + Alerts

| Task | Owner | Tech | Priority |
|------|-------|------|----------|
| Implement 7-day projection | Data Science | Python | P0 |
| Build forecast API endpoint | Backend | FastAPI | P0 |
| Create watchlist feature | Frontend | React, LocalStorage | P0 |
| Implement in-app notifications | Frontend | React | P0 |
| Add forecast to time scrubber | Frontend | React | P1 |

**Deliverables**:
- [ ] Basic 7-day forecast (linear extrapolation)
- [ ] Watchlist with up to 5 locations
- [ ] In-app alerts for >50% changes

### Week 12: Variant Features

| Task | Owner | Tech | Priority |
|------|-------|------|----------|
| Build variant card modal | Frontend | React | P0 |
| Implement variant stats display | Frontend | React | P0 |
| Add variant filter to globe | Frontend | React | P1 |
| Build /api/variants endpoint | Backend | FastAPI | P0 |
| Create variant history chart | Frontend | Chart.js/Recharts | P2 |

**Deliverables**:
- [ ] Variant trading cards with stats
- [ ] Variant filter on globe
- [ ] Dominant variant displayed in dossier

---

## Phase 4: Polish (Weeks 13-16)

**Goal**: Production-ready MVP
**Deliverable**: Polished, tested, secure application

### Week 13: Remaining Countries + Data Quality

| Task | Owner | Tech | Priority |
|------|-------|------|----------|
| Build remaining 20 country adapters | Data Eng | Python | P0 |
| Implement data quality scoring | Backend | Python | P0 |
| Add confidence indicators to UI | Frontend | React | P0 |
| Create data coverage map | Frontend | React | P1 |
| Set up monitoring dashboards | DevOps | Cloud Monitoring | P0 |

**Deliverables**:
- [ ] 50 countries with data
- [ ] Quality scores displayed in UI
- [ ] Monitoring dashboards operational

### Week 14: Error Handling + Degradation

| Task | Owner | Tech | Priority |
|------|-------|------|----------|
| Implement circuit breakers | Backend | pybreaker | P0 |
| Build graceful degradation modes | Frontend | React | P0 |
| Create error state components | Frontend | React | P0 |
| Add retry logic with backoff | Backend | Python | P0 |
| Build status page | Frontend | React | P1 |

**Deliverables**:
- [ ] Circuit breakers on all external calls
- [ ] Graceful degradation for all failure modes
- [ ] Error states for all components
- [ ] Status page showing system health

### Week 15: Performance + Security

| Task | Owner | Tech | Priority |
|------|-------|------|----------|
| Optimize globe rendering (30+ fps) | Frontend | Deck.gl | P0 |
| Implement Redis caching strategy | Backend | Redis | P0 |
| Set up Cloud Armor WAF rules | DevOps | Cloud Armor | P0 |
| Conduct security review (OWASP) | Security | Manual | P0 |
| Run Lighthouse audits | Frontend | Lighthouse | P0 |

**Performance Targets**:
- Globe: 30+ fps with 5k arcs
- API: p95 latency <500ms
- Lighthouse: >70 score

**Deliverables**:
- [ ] Performance targets met
- [ ] Security review passed
- [ ] Lighthouse score >70

### Week 16: Load Testing + Launch Prep

| Task | Owner | Tech | Priority |
|------|-------|------|----------|
| Write k6 load test scripts | QA | k6 | P0 |
| Run load tests (1000 concurrent) | QA | k6 | P0 |
| Fix any performance issues | All | Various | P0 |
| Create runbooks for operations | DevOps | Markdown | P1 |
| Final QA pass | QA | Manual | P0 |

**Load Test Targets**:
- 1000 concurrent users
- 100 RPS sustained
- p95 latency <500ms under load

**Deliverables**:
- [ ] Load tests passing
- [ ] Runbooks documented
- [ ] Final QA sign-off
- [ ] Production deployment complete

---

## Verification Checklist

After implementation, verify the system end-to-end:

### Data Pipeline
- [ ] Trigger CDC NWSS ingestion manually
- [ ] Verify data appears in Cloud SQL with correct H3 indexes
- [ ] Check deduplication works
- [ ] Confirm all 50 countries have data

### API Layer
- [ ] `/api/locations` returns LocationNodes
- [ ] `/api/locations/{id}` returns dossier data
- [ ] `/api/risk/{id}` returns valid 0-100 score
- [ ] Tile endpoint returns valid MVT

### Frontend
- [ ] Globe loads within 5 seconds
- [ ] Clicking location opens dossier panel
- [ ] Time scrubber navigates 30-day history
- [ ] Watchlist persists in LocalStorage
- [ ] Error states display correctly

### Performance
- [ ] Lighthouse score >70 on desktop
- [ ] Globe renders at 30+ fps
- [ ] API p95 latency <500ms
- [ ] Load test passes (1000 concurrent)

### Security
- [ ] OWASP top 10 mitigated
- [ ] Rate limiting working
- [ ] Input validation preventing injection
- [ ] HTTPS enforced

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Data source goes offline | Medium | High | Circuit breakers, cached fallbacks |
| AviationStack API changes | Low | High | Version adapters, monitor for changes |
| Performance issues at scale | Medium | Medium | Load testing, caching strategy |
| Security vulnerability | Low | High | Security review, penetration testing |
| Scope creep | High | Medium | Strict MVP scope, defer features |

---

## Success Criteria

MVP is successful if:

1. **Coverage**: 50 countries with wastewater data visible
2. **Freshness**: Data updated within published schedules
3. **Performance**: Globe renders at 30+ fps, API <500ms p95
4. **Reliability**: 99% uptime over 1 week
5. **Usability**: User can find location, see risk, understand data within 30 seconds
