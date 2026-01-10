# Viral Weather

> "The Waze for Viral Avoidance" - A predictive radar for viral risk.

## Overview

Viral Weather is a platform that provides forward-looking forecasts of viral risk by fusing:
- **Genomic identity** (Nextstrain) - Variant tracking and evolution
- **Environmental load** (Wastewater surveillance) - Real-time viral presence
- **Vector physics** (Flight data) - Transmission pathways

## Documentation

- [PRD Analysis](./docs/PRD_ANALYSIS.md) - Product requirements and recommendations
- [Data Sources](./docs/DATA_SOURCES.md) - Integration guide for all data sources
- [Architecture](./docs/ARCHITECTURE.md) - GCP infrastructure specification
- [Edge Cases](./docs/EDGE_CASES.md) - Edge case catalog and mitigations
- [Implementation Plan](./docs/IMPLEMENTATION_PLAN.md) - 16-week development roadmap

## MVP Scope

| Constraint | Scope |
|------------|-------|
| Platform | Web only (mobile deferred) |
| Cloud | Google Cloud Platform (GCP) |
| Data Budget | ≤$75/month for APIs |
| Geographic | Top 50 countries |
| Timeline | 16 weeks |

## Tech Stack

- **Frontend**: Next.js 14, Deck.gl, Mapbox GL JS
- **Backend**: Python FastAPI, GraphQL
- **Database**: Cloud SQL (PostgreSQL 15 + PostGIS)
- **Cache**: Memorystore (Redis)
- **Infrastructure**: Cloud Run, Cloud Functions, Cloud CDN

## Data Sources

| Source | Type | Cost |
|--------|------|------|
| CDC NWSS | Wastewater (US) | Free |
| UKHSA, RIVM, etc. | Wastewater (International) | Free |
| Nextstrain | Genomic | Free |
| AviationStack | Flight data | $49/mo |

## Getting Started

*Development setup instructions coming in Phase 1*

## License

*TBD*
