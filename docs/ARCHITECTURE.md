# GCP Architecture Specification

## Overview

The Viral Weather platform uses a serverless-first architecture on Google Cloud Platform (GCP), optimized for cost efficiency and scalability.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        CDN LAYER                            │
│                    (Cloud CDN + Cloud Armor)                │
│  - Static assets (globe textures, variant avatars)          │
│  - Cached API responses (tile MVTs)                         │
│  - DDoS protection, rate limiting (100 req/min per IP)      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     APPLICATION LAYER                       │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Web App (Cloud Run)                     │   │
│  │                   Next.js 14                         │   │
│  │                                                      │   │
│  │  - Deck.gl + Mapbox GL JS (globe rendering)         │   │
│  │  - React Query (data fetching + caching)            │   │
│  │  - LocalStorage (user preferences)                  │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                        API LAYER                            │
│                     (Cloud Run + API Gateway)               │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Risk API    │  │ Tile Server  │  │  Search API  │      │
│  │  (FastAPI)   │  │ (pg_tileserv)│  │  (FastAPI)   │      │
│  │              │  │              │  │              │      │
│  │ - GraphQL    │  │ - MVT tiles  │  │ - Location   │      │
│  │ - REST       │  │ - GeoJSON    │  │   autocomplete│     │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       DATA LAYER                            │
│                                                             │
│  ┌───────────────────┐  ┌───────────────────┐              │
│  │   Cloud SQL       │  │   Memorystore     │              │
│  │   (PostgreSQL 15  │  │   (Redis)         │              │
│  │    + PostGIS 3.4) │  │                   │              │
│  │                   │  │ - Tile cache      │              │
│  │ - LocationNodes   │  │ - API cache       │              │
│  │ - SurveillanceEvt │  │ - Rate limits     │              │
│  │ - VectorArcs      │  │                   │              │
│  └───────────────────┘  └───────────────────┘              │
│                                                             │
│  ┌───────────────────┐  ┌───────────────────┐              │
│  │ Cloud Storage     │  │   BigQuery        │              │
│  │                   │  │   (Optional)      │              │
│  │ - Raw data lake   │  │                   │              │
│  │ - Nextstrain dump │  │ - Analytics       │              │
│  │ - Static assets   │  │ - Historical      │              │
│  └───────────────────┘  └───────────────────┘              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   ORCHESTRATION LAYER                       │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │Cloud Scheduler│  │ Cloud Tasks │  │ Pub/Sub      │      │
│  │              │  │              │  │              │      │
│  │ - Cron jobs  │  │ - Async work │  │ - Event bus  │      │
│  │ - Ingestion  │  │ - Retries    │  │ - Alerts     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

| Component | Technology | Rationale |
|-----------|------------|-----------|
| **Frontend** | Next.js 14 | SSR for SEO, great DX, Vercel-compatible |
| **Globe Rendering** | Deck.gl + Mapbox GL JS | Best WebGL performance, open ecosystem |
| **API Framework** | Python FastAPI | Rapid development, async support, OpenAPI |
| **GraphQL** | Strawberry GraphQL | Type-safe, integrates with FastAPI |
| **Tile Server** | pg_tileserv | Direct PostGIS → MVT, minimal config |
| **Ingestion** | Cloud Functions (Python) | Serverless, pay-per-use |
| **Scheduler** | Cloud Scheduler | Managed cron, no infrastructure |
| **Primary DB** | Cloud SQL PostgreSQL 15 + PostGIS 3.4 | Managed, geospatial queries |
| **Spatial Index** | H3 (Uber) | Uniform hexagonal grid, efficient joins |
| **Cache** | Memorystore Redis | Managed, low latency |
| **Object Storage** | Cloud Storage | Data lake, static assets |
| **CDN** | Cloud CDN | Global edge, GCS integration |
| **Security** | Cloud Armor | WAF, DDoS protection, rate limiting |
| **CI/CD** | Cloud Build + GitHub | Native GCP integration |
| **Monitoring** | Cloud Monitoring + Logging | Unified observability |

---

## Data Model

### LocationNode (Geographic Anchor)
```json
{
  "location_id": "loc_nyc_01",
  "h3_index": "892a10400ffffff",
  "hierarchy": {
    "city": "New York",
    "admin1": "New York State",
    "country": "USA",
    "iso_code": "US"
  },
  "granularity_tier": 1,
  "geometry": {
    "type": "Point",
    "coordinates": [-74.006, 40.7128]
  },
  "catchment_population": 8400000
}
```

### SurveillanceEvent (Signal)
```json
{
  "event_id": "evt_ww_29384",
  "location_id": "loc_nyc_01",
  "timestamp": "2026-01-10T00:00:00Z",
  "data_source": "CDC_NWSS",
  "signal_type": "wastewater",
  "metrics": {
    "raw_load": 54000.0,
    "normalized_score": 0.85,
    "velocity": 0.12
  },
  "genomic_inference": {
    "confirmed_variants": ["BA.2.86"],
    "suspected_variants": ["JN.1"]
  }
}
```

### VectorArc (Flight Connection)
```json
{
  "arc_id": "arc_lhr_jfk_20260110",
  "origin_location_id": "loc_lon_01",
  "dest_location_id": "loc_nyc_01",
  "date": "2026-01-10",
  "volume": {
    "pax_est": 2400,
    "flight_count": 8
  },
  "risk_payload": {
    "export_risk_score": 0.9,
    "primary_variant_cargo": "BA.2.86"
  }
}
```

---

## Database Schema (PostgreSQL + PostGIS)

```sql
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS h3;

-- Location nodes
CREATE TABLE location_nodes (
    location_id VARCHAR(50) PRIMARY KEY,
    h3_index VARCHAR(15) NOT NULL,
    name VARCHAR(255) NOT NULL,
    admin1 VARCHAR(255),
    country VARCHAR(100) NOT NULL,
    iso_code CHAR(2) NOT NULL,
    granularity_tier SMALLINT NOT NULL CHECK (granularity_tier BETWEEN 1 AND 3),
    geometry GEOMETRY(Point, 4326) NOT NULL,
    catchment_population INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_location_h3 ON location_nodes(h3_index);
CREATE INDEX idx_location_geo ON location_nodes USING GIST(geometry);
CREATE INDEX idx_location_country ON location_nodes(iso_code);

-- Surveillance events
CREATE TABLE surveillance_events (
    event_id VARCHAR(50) PRIMARY KEY,
    location_id VARCHAR(50) REFERENCES location_nodes(location_id),
    timestamp TIMESTAMPTZ NOT NULL,
    data_source VARCHAR(50) NOT NULL,
    signal_type VARCHAR(20) NOT NULL CHECK (signal_type IN ('wastewater', 'genomic', 'flight')),
    raw_load FLOAT,
    normalized_score FLOAT CHECK (normalized_score BETWEEN 0 AND 1),
    velocity FLOAT,
    confirmed_variants TEXT[],
    suspected_variants TEXT[],
    quality_score FLOAT CHECK (quality_score BETWEEN 0 AND 1),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_event_location ON surveillance_events(location_id);
CREATE INDEX idx_event_timestamp ON surveillance_events(timestamp DESC);
CREATE INDEX idx_event_source ON surveillance_events(data_source);

-- Vector arcs (flights)
CREATE TABLE vector_arcs (
    arc_id VARCHAR(100) PRIMARY KEY,
    origin_location_id VARCHAR(50) REFERENCES location_nodes(location_id),
    dest_location_id VARCHAR(50) REFERENCES location_nodes(location_id),
    date DATE NOT NULL,
    pax_estimate INTEGER,
    flight_count INTEGER,
    export_risk_score FLOAT CHECK (export_risk_score BETWEEN 0 AND 1),
    primary_variant VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_arc_origin ON vector_arcs(origin_location_id);
CREATE INDEX idx_arc_dest ON vector_arcs(dest_location_id);
CREATE INDEX idx_arc_date ON vector_arcs(date DESC);

-- Risk scores (materialized view, refreshed hourly)
CREATE MATERIALIZED VIEW risk_scores AS
SELECT
    ln.location_id,
    ln.name,
    ln.geometry,
    COALESCE(AVG(se.normalized_score) * 100, 0) as risk_score,
    MAX(se.timestamp) as last_updated,
    ARRAY_AGG(DISTINCT unnest(se.confirmed_variants)) as variants
FROM location_nodes ln
LEFT JOIN surveillance_events se ON ln.location_id = se.location_id
    AND se.timestamp > NOW() - INTERVAL '14 days'
GROUP BY ln.location_id, ln.name, ln.geometry;

CREATE UNIQUE INDEX idx_risk_location ON risk_scores(location_id);
```

---

## API Endpoints

### REST API
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/locations` | List all locations with current risk |
| GET | `/api/locations/{id}` | Get location details + dossier |
| GET | `/api/locations/{id}/history` | Time series data |
| GET | `/api/arcs` | Flight arcs (filterable by origin/dest) |
| GET | `/api/variants` | List known variants with stats |
| GET | `/api/search?q={query}` | Location autocomplete |

### GraphQL API
```graphql
type Query {
  location(id: ID!): Location
  locations(filter: LocationFilter): [Location!]!
  arcs(origin: ID, dest: ID, date: Date): [Arc!]!
  riskForecast(locationId: ID!, days: Int!): [RiskPoint!]!
}

type Location {
  id: ID!
  name: String!
  country: String!
  riskScore: Float!
  lastUpdated: DateTime!
  variants: [String!]!
  incomingArcs: [Arc!]!
  outgoingArcs: [Arc!]!
}
```

### Tile Endpoints (pg_tileserv)
| Endpoint | Description |
|----------|-------------|
| `/tiles/risk_scores/{z}/{x}/{y}.mvt` | Risk heatmap tiles |
| `/tiles/location_nodes/{z}/{x}/{y}.mvt` | Location markers |

---

## Cost Estimates

### Aggressive MVP Budget (~$150/mo)
```
- Cloud SQL (db-f1-micro + PostGIS): $10
- Memorystore (1GB basic): $35
- Cloud Run (scale to zero): $20
- Cloud Functions (ingestion): $5
- Cloud Storage (50GB): $1
- Cloud CDN (100GB egress): $5
- Cloud Scheduler: $1
- Networking: $10
- AviationStack: $49
- Buffer: $14
────────────────────────────
Total: ~$150/month
```

### Standard MVP Budget (~$250/mo)
```
- Cloud SQL (db-custom-2-8192): $80
- Memorystore Redis (1GB): $35
- Cloud Run (2 services): $50
- Cloud Functions: $10
- Cloud Storage: $1
- Cloud CDN: $8
- Cloud Scheduler: $1
- Networking: $15
- AviationStack: $49
────────────────────────────
Total: ~$250/month
```

---

## Cost Optimization Strategies

1. **Cloud Run min instances = 0**: Scale to zero during off-peak
2. **Aggressive caching**:
   - Tiles: 5-min TTL in Redis
   - Risk scores: 1-hour TTL
   - Location data: 24-hour TTL
3. **Cloud SQL smallest tier**: Start with db-f1-micro, scale as needed
4. **Preemptible for batch**: Use spot instances for ingestion jobs
5. **CDN everything**: Static assets + API responses

---

## Deployment

### Cloud Run Service Configuration
```yaml
# cloudbuild.yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/viral-weather-api', './api']

  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'viral-weather-api'
      - '--image=gcr.io/$PROJECT_ID/viral-weather-api'
      - '--region=us-central1'
      - '--platform=managed'
      - '--allow-unauthenticated'
      - '--min-instances=0'
      - '--max-instances=10'
      - '--memory=512Mi'
      - '--cpu=1'
```

### Environment Variables
```bash
# .env.production
DATABASE_URL=postgresql://user:pass@/viral_weather?host=/cloudsql/project:region:instance
REDIS_URL=redis://10.0.0.1:6379
AVIATIONSTACK_KEY=your_key_here
MAPBOX_TOKEN=your_token_here
NEXTSTRAIN_CACHE_DIR=/tmp/nextstrain
```

---

## Observability

### Cloud Monitoring Dashboards
- Request latency (p50, p95, p99)
- Error rate by endpoint
- Data freshness per source
- Cache hit rate
- Database connections

### Alerting Policies
| Severity | Condition | Action |
|----------|-----------|--------|
| P0 | API error rate >10% for 5min | PagerDuty |
| P0 | Database down | PagerDuty |
| P1 | Data source stale >24h | Slack |
| P1 | Latency p95 >2s | Slack |
| P2 | Cache hit rate <50% | Email |

### Logging
```python
import structlog

logger = structlog.get_logger()

logger.info(
    "surveillance_event_ingested",
    source="CDC_NWSS",
    location_id="loc_nyc_01",
    event_count=150,
    duration_ms=1234
)
```
