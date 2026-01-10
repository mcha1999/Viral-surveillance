# Viral Weather GCP Deployment Guide

Complete step-by-step instructions to deploy Viral Weather to Google Cloud Platform and connect all required APIs/data sources.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [GCP Project Setup](#2-gcp-project-setup)
3. [Enable Required APIs](#3-enable-required-gcp-apis)
4. [External API Accounts](#4-external-api-accounts)
5. [Infrastructure Deployment](#5-infrastructure-deployment)
6. [Database Setup](#6-database-setup)
7. [Application Deployment](#7-application-deployment)
8. [Data Pipeline Setup](#8-data-pipeline-setup)
9. [CDN & Security](#9-cdn--security-setup)
10. [Monitoring & Alerting](#10-monitoring--alerting)
11. [Custom Domain (Optional)](#11-custom-domain-optional)
12. [Go-Live Checklist](#12-go-live-checklist)

---

## 1. Prerequisites

### Required Accounts

| Account | Purpose | Sign Up |
|---------|---------|---------|
| Google Cloud Platform | Cloud infrastructure | https://console.cloud.google.com |
| AviationStack | Flight data API | https://aviationstack.com/signup |
| Mapbox | Map tiles & geocoding | https://account.mapbox.com/auth/signup |
| Socrata (CDC) | US wastewater data | https://data.cdc.gov/signup |
| OpenSky Network | Flight validation | https://opensky-network.org/register |

### Required Tools

Install these on your local machine:

```bash
# 1. Google Cloud CLI
# macOS
brew install google-cloud-sdk

# Linux (Debian/Ubuntu)
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Windows: Download from https://cloud.google.com/sdk/docs/install

# 2. Verify installation
gcloud --version

# 3. Install additional components
gcloud components install cloud-sql-proxy kubectl docker-credential-gcr

# 4. Install Terraform (optional, for IaC)
brew install terraform  # macOS
# or download from https://www.terraform.io/downloads

# 5. Install Node.js 18+ (for frontend)
brew install node  # macOS
# or use nvm: https://github.com/nvm-sh/nvm

# 6. Install Python 3.11+ (for backend)
brew install python@3.11  # macOS
# or use pyenv: https://github.com/pyenv/pyenv
```

---

## 2. GCP Project Setup

### Step 2.1: Create GCP Project

```bash
# Authenticate with Google Cloud
gcloud auth login

# Create a new project (replace with your project ID)
export PROJECT_ID="viral-weather-prod"
gcloud projects create $PROJECT_ID --name="Viral Weather"

# Set as default project
gcloud config set project $PROJECT_ID

# Link billing account (required for paid services)
# List available billing accounts
gcloud billing accounts list

# Link billing (replace BILLING_ACCOUNT_ID with your account ID)
gcloud billing projects link $PROJECT_ID --billing-account=BILLING_ACCOUNT_ID
```

### Step 2.2: Set Default Region

```bash
# Set default region (us-central1 recommended for cost/latency balance)
export REGION="us-central1"
export ZONE="us-central1-a"

gcloud config set compute/region $REGION
gcloud config set compute/zone $ZONE
```

---

## 3. Enable Required GCP APIs

```bash
# Enable all required APIs (run as single command)
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  sqladmin.googleapis.com \
  redis.googleapis.com \
  cloudscheduler.googleapis.com \
  cloudfunctions.googleapis.com \
  pubsub.googleapis.com \
  cloudtasks.googleapis.com \
  storage.googleapis.com \
  compute.googleapis.com \
  servicenetworking.googleapis.com \
  secretmanager.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com \
  cloudresourcemanager.googleapis.com \
  artifactregistry.googleapis.com

# Verify APIs are enabled
gcloud services list --enabled
```

---

## 4. External API Accounts

### 4.1 AviationStack (Flight Data) - $49/month

1. Go to https://aviationstack.com/signup
2. Choose **Basic Plan** ($49/mo for 10,000 requests)
3. After signup, find your API key in the dashboard
4. Save the API key securely

```bash
# Store in Secret Manager
echo -n "YOUR_AVIATIONSTACK_API_KEY" | \
  gcloud secrets create aviationstack-api-key \
  --data-file=- \
  --replication-policy=automatic
```

### 4.2 Mapbox (Maps & Geocoding) - Free Tier

1. Go to https://account.mapbox.com/auth/signup
2. Create account and verify email
3. Go to **Tokens** page: https://account.mapbox.com/access-tokens
4. Copy your **Default public token** (starts with `pk.`)

```bash
# Store in Secret Manager
echo -n "pk.YOUR_MAPBOX_TOKEN" | \
  gcloud secrets create mapbox-token \
  --data-file=- \
  --replication-policy=automatic
```

### 4.3 Socrata App Token (CDC Data) - FREE

1. Go to https://data.cdc.gov/login
2. Create an account or sign in
3. Go to **Developer Settings** → **Create New App Token**
4. Fill in application details
5. Copy your **App Token**

```bash
# Store in Secret Manager
echo -n "YOUR_SOCRATA_APP_TOKEN" | \
  gcloud secrets create socrata-app-token \
  --data-file=- \
  --replication-policy=automatic
```

### 4.4 OpenSky Network (Flight Validation) - FREE

1. Go to https://opensky-network.org/register
2. Create account
3. Username and password are your credentials

```bash
# Store credentials in Secret Manager
echo -n "YOUR_OPENSKY_USERNAME" | \
  gcloud secrets create opensky-username \
  --data-file=- \
  --replication-policy=automatic

echo -n "YOUR_OPENSKY_PASSWORD" | \
  gcloud secrets create opensky-password \
  --data-file=- \
  --replication-policy=automatic
```

### 4.5 Summary of API Costs

| Service | Monthly Cost | Annual Cost |
|---------|-------------|-------------|
| AviationStack Basic | $49 | $588 |
| Mapbox | Free (50k loads) | $0 |
| Socrata/CDC | Free | $0 |
| OpenSky | Free | $0 |
| **Total** | **$49** | **$588** |

---

## 5. Infrastructure Deployment

### 5.1 Create VPC Network

```bash
# Create VPC for private connectivity
gcloud compute networks create viral-weather-vpc \
  --subnet-mode=auto

# Create serverless VPC connector (for Cloud Run → Cloud SQL)
gcloud compute networks vpc-access connectors create viral-weather-connector \
  --region=$REGION \
  --network=viral-weather-vpc \
  --range=10.8.0.0/28 \
  --min-instances=2 \
  --max-instances=3

# Allocate IP range for private services
gcloud compute addresses create google-managed-services-viral-weather \
  --global \
  --purpose=VPC_PEERING \
  --prefix-length=16 \
  --network=viral-weather-vpc

# Create private connection
gcloud services vpc-peerings connect \
  --service=servicenetworking.googleapis.com \
  --ranges=google-managed-services-viral-weather \
  --network=viral-weather-vpc
```

### 5.2 Create Cloud SQL (PostgreSQL + PostGIS)

```bash
# Create PostgreSQL instance
# Option A: Aggressive budget (db-f1-micro ~$10/mo)
gcloud sql instances create viral-weather-db \
  --database-version=POSTGRES_15 \
  --tier=db-f1-micro \
  --region=$REGION \
  --network=viral-weather-vpc \
  --no-assign-ip \
  --storage-type=SSD \
  --storage-size=10GB \
  --storage-auto-increase \
  --backup-start-time=04:00 \
  --enable-point-in-time-recovery

# Option B: Standard budget (db-custom-2-8192 ~$80/mo)
# Uncomment and use this for production workloads:
# gcloud sql instances create viral-weather-db \
#   --database-version=POSTGRES_15 \
#   --cpu=2 \
#   --memory=8GB \
#   --region=$REGION \
#   --network=viral-weather-vpc \
#   --no-assign-ip \
#   --storage-type=SSD \
#   --storage-size=50GB \
#   --storage-auto-increase \
#   --availability-type=REGIONAL \
#   --backup-start-time=04:00 \
#   --enable-point-in-time-recovery

# Set root password
gcloud sql users set-password postgres \
  --instance=viral-weather-db \
  --password="$(openssl rand -base64 32)"

# Create application user
export DB_PASSWORD=$(openssl rand -base64 32)
gcloud sql users create viralweather \
  --instance=viral-weather-db \
  --password="$DB_PASSWORD"

# Store password in Secret Manager
echo -n "$DB_PASSWORD" | \
  gcloud secrets create db-password \
  --data-file=- \
  --replication-policy=automatic

# Create the database
gcloud sql databases create viral_weather \
  --instance=viral-weather-db
```

### 5.3 Create Memorystore (Redis)

```bash
# Create Redis instance (1GB basic tier ~$35/mo)
gcloud redis instances create viral-weather-cache \
  --size=1 \
  --region=$REGION \
  --network=viral-weather-vpc \
  --redis-version=redis_7_0 \
  --tier=basic

# Get Redis IP (save this for later)
gcloud redis instances describe viral-weather-cache \
  --region=$REGION \
  --format="value(host)"
```

### 5.4 Create Cloud Storage Buckets

```bash
# Create data lake bucket (for raw API responses)
gcloud storage buckets create gs://${PROJECT_ID}-data-lake \
  --location=$REGION \
  --uniform-bucket-level-access

# Create static assets bucket (for globe textures, etc.)
gcloud storage buckets create gs://${PROJECT_ID}-static-assets \
  --location=$REGION \
  --uniform-bucket-level-access

# Make static assets publicly readable
gcloud storage buckets add-iam-policy-binding gs://${PROJECT_ID}-static-assets \
  --member=allUsers \
  --role=roles/storage.objectViewer
```

### 5.5 Create Artifact Registry

```bash
# Create Docker repository
gcloud artifacts repositories create viral-weather \
  --repository-format=docker \
  --location=$REGION \
  --description="Viral Weather Docker images"

# Configure Docker to use Artifact Registry
gcloud auth configure-docker ${REGION}-docker.pkg.dev
```

---

## 6. Database Setup

### 6.1 Connect to Database

```bash
# Get Cloud SQL connection name
export SQL_CONNECTION=$(gcloud sql instances describe viral-weather-db \
  --format="value(connectionName)")

# Start Cloud SQL Proxy (in a separate terminal)
cloud-sql-proxy $SQL_CONNECTION &

# Connect with psql
PGPASSWORD=$DB_PASSWORD psql -h 127.0.0.1 -U viralweather -d viral_weather
```

### 6.2 Install PostGIS Extension

Run these commands in psql:

```sql
-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS postgis_topology;
-- Note: H3 extension requires installation from source or use pg_h3

-- Verify PostGIS installation
SELECT PostGIS_Version();
```

### 6.3 Create Database Schema

Run the full schema from `docs/ARCHITECTURE.md`:

```sql
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

-- Risk scores materialized view (refreshed hourly)
CREATE MATERIALIZED VIEW risk_scores AS
SELECT
    ln.location_id,
    ln.name,
    ln.geometry,
    ln.country,
    ln.iso_code,
    COALESCE(AVG(se.normalized_score) * 100, 0) as risk_score,
    COALESCE(AVG(se.velocity), 0) as velocity,
    MAX(se.timestamp) as last_updated,
    array_agg(DISTINCT unnest) FILTER (WHERE unnest IS NOT NULL) as variants
FROM location_nodes ln
LEFT JOIN surveillance_events se ON ln.location_id = se.location_id
    AND se.timestamp > NOW() - INTERVAL '14 days'
LEFT JOIN LATERAL unnest(se.confirmed_variants) ON true
GROUP BY ln.location_id, ln.name, ln.geometry, ln.country, ln.iso_code;

CREATE UNIQUE INDEX idx_risk_location ON risk_scores(location_id);
CREATE INDEX idx_risk_geo ON risk_scores USING GIST(geometry);

-- Create function to refresh materialized view
CREATE OR REPLACE FUNCTION refresh_risk_scores()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY risk_scores;
END;
$$ LANGUAGE plpgsql;
```

### 6.4 Seed Location Data

```sql
-- Insert major global cities as initial location nodes
-- This is a sample; full dataset should be loaded from a CSV

INSERT INTO location_nodes (location_id, h3_index, name, admin1, country, iso_code, granularity_tier, geometry, catchment_population) VALUES
('loc_nyc', '892a10400ffffff', 'New York City', 'New York', 'United States', 'US', 1, ST_SetSRID(ST_MakePoint(-74.006, 40.7128), 4326), 8400000),
('loc_lax', '8929a9620ffffff', 'Los Angeles', 'California', 'United States', 'US', 1, ST_SetSRID(ST_MakePoint(-118.2437, 34.0522), 4326), 4000000),
('loc_chi', '8829a1b2bffffff', 'Chicago', 'Illinois', 'United States', 'US', 1, ST_SetSRID(ST_MakePoint(-87.6298, 41.8781), 4326), 2700000),
('loc_lon', '8839544c9ffffff', 'London', 'England', 'United Kingdom', 'GB', 1, ST_SetSRID(ST_MakePoint(-0.1276, 51.5074), 4326), 9000000),
('loc_par', '8839544cbffffff', 'Paris', 'Île-de-France', 'France', 'FR', 1, ST_SetSRID(ST_MakePoint(2.3522, 48.8566), 4326), 2200000),
('loc_tok', '8844c09a3ffffff', 'Tokyo', 'Tokyo', 'Japan', 'JP', 1, ST_SetSRID(ST_MakePoint(139.6917, 35.6895), 4326), 14000000),
('loc_syd', '8839548cbffffff', 'Sydney', 'New South Wales', 'Australia', 'AU', 1, ST_SetSRID(ST_MakePoint(151.2093, -33.8688), 4326), 5300000),
('loc_sin', '8839500cbffffff', 'Singapore', NULL, 'Singapore', 'SG', 2, ST_SetSRID(ST_MakePoint(103.8198, 1.3521), 4326), 5600000);

-- Verify data
SELECT name, country, ST_AsText(geometry) FROM location_nodes LIMIT 5;
```

---

## 7. Application Deployment

### 7.1 Project Structure

Create the following directory structure in your repository:

```bash
mkdir -p api frontend functions
```

```
viral-weather/
├── api/                    # FastAPI backend
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   └── ...
├── frontend/               # Next.js frontend
│   ├── Dockerfile
│   ├── package.json
│   └── ...
├── functions/              # Cloud Functions (ingestion)
│   ├── wastewater_cdc/
│   ├── nextstrain_sync/
│   └── flight_routes/
├── cloudbuild.yaml
└── docs/
```

### 7.2 API Dockerfile Example

Create `api/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run with Gunicorn
CMD ["gunicorn", "main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "-b", "0.0.0.0:8080"]
```

Create `api/requirements.txt`:

```
fastapi==0.109.0
uvicorn[standard]==0.27.0
gunicorn==21.2.0
sqlalchemy[asyncio]==2.0.25
asyncpg==0.29.0
psycopg2-binary==2.9.9
pydantic==2.5.3
pydantic-settings==2.1.0
redis==5.0.1
strawberry-graphql[fastapi]==0.217.1
httpx==0.26.0
structlog==24.1.0
python-dotenv==1.0.0
pybreaker==1.1.0
h3==3.7.6
pandas==2.2.0
sodapy==2.2.0
```

### 7.3 Deploy API to Cloud Run

```bash
# Get secrets for environment variables
export REDIS_HOST=$(gcloud redis instances describe viral-weather-cache \
  --region=$REGION --format="value(host)")
export SQL_CONNECTION=$(gcloud sql instances describe viral-weather-db \
  --format="value(connectionName)")

# Build and push Docker image
cd api
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/viral-weather/api:latest

# Deploy to Cloud Run
gcloud run deploy viral-weather-api \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/viral-weather/api:latest \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --min-instances=0 \
  --max-instances=10 \
  --memory=512Mi \
  --cpu=1 \
  --set-cloudsql-instances=$SQL_CONNECTION \
  --vpc-connector=viral-weather-connector \
  --set-env-vars="REDIS_HOST=$REDIS_HOST,REDIS_PORT=6379" \
  --set-secrets="DATABASE_PASSWORD=db-password:latest,AVIATIONSTACK_KEY=aviationstack-api-key:latest,MAPBOX_TOKEN=mapbox-token:latest,SOCRATA_TOKEN=socrata-app-token:latest"

# Get the API URL
export API_URL=$(gcloud run services describe viral-weather-api \
  --region=$REGION --format="value(status.url)")
echo "API URL: $API_URL"
```

### 7.4 Deploy Frontend to Cloud Run

Create `frontend/Dockerfile`:

```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:18-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=builder /app/next.config.js ./
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 8080
ENV PORT=8080
CMD ["node", "server.js"]
```

```bash
# Build and deploy frontend
cd frontend
gcloud builds submit --tag ${REGION}-docker.pkg.dev/${PROJECT_ID}/viral-weather/frontend:latest

gcloud run deploy viral-weather-frontend \
  --image=${REGION}-docker.pkg.dev/${PROJECT_ID}/viral-weather/frontend:latest \
  --region=$REGION \
  --platform=managed \
  --allow-unauthenticated \
  --min-instances=0 \
  --max-instances=10 \
  --memory=512Mi \
  --cpu=1 \
  --set-env-vars="NEXT_PUBLIC_API_URL=$API_URL,NEXT_PUBLIC_MAPBOX_TOKEN=your-public-token"

# Get frontend URL
export FRONTEND_URL=$(gcloud run services describe viral-weather-frontend \
  --region=$REGION --format="value(status.url)")
echo "Frontend URL: $FRONTEND_URL"
```

---

## 8. Data Pipeline Setup

### 8.1 Create Pub/Sub Topics

```bash
# Create topics for ingestion pipeline
gcloud pubsub topics create wastewater-ingestion
gcloud pubsub topics create genomic-ingestion
gcloud pubsub topics create flight-ingestion
gcloud pubsub topics create risk-calculation

# Create dead-letter topic for failed messages
gcloud pubsub topics create ingestion-dead-letter
```

### 8.2 Deploy Cloud Functions

Create `functions/wastewater_cdc/main.py`:

```python
import functions_framework
from sodapy import Socrata
import os
import json
from google.cloud import pubsub_v1

@functions_framework.http
def ingest_cdc_wastewater(request):
    """Fetch CDC NWSS wastewater data and publish to Pub/Sub."""
    client = Socrata("data.cdc.gov", os.environ.get("SOCRATA_TOKEN"))

    # Fetch latest data
    results = client.get("g653-rqe2", limit=5000,
                         where="date_start > date_sub(now(), interval 14 day)")

    # Publish to Pub/Sub for processing
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(
        os.environ.get("GCP_PROJECT"),
        "wastewater-ingestion"
    )

    for record in results:
        data = json.dumps(record).encode("utf-8")
        publisher.publish(topic_path, data, source="CDC_NWSS")

    return f"Published {len(results)} wastewater records", 200
```

Create `functions/wastewater_cdc/requirements.txt`:

```
functions-framework==3.*
sodapy==2.2.0
google-cloud-pubsub==2.18.4
```

Deploy the function:

```bash
cd functions/wastewater_cdc

gcloud functions deploy ingest-cdc-wastewater \
  --gen2 \
  --runtime=python311 \
  --region=$REGION \
  --source=. \
  --entry-point=ingest_cdc_wastewater \
  --trigger-http \
  --allow-unauthenticated \
  --memory=256MB \
  --timeout=300s \
  --set-secrets="SOCRATA_TOKEN=socrata-app-token:latest" \
  --set-env-vars="GCP_PROJECT=$PROJECT_ID"
```

### 8.3 Create Cloud Scheduler Jobs

```bash
# CDC Wastewater - Tue/Thu 6am UTC (data release schedule)
gcloud scheduler jobs create http wastewater-cdc-job \
  --location=$REGION \
  --schedule="0 6 * * 2,4" \
  --uri="https://${REGION}-${PROJECT_ID}.cloudfunctions.net/ingest-cdc-wastewater" \
  --http-method=GET \
  --oidc-service-account-email="${PROJECT_ID}@appspot.gserviceaccount.com"

# Nextstrain genomic sync - Daily 4am UTC
gcloud scheduler jobs create http nextstrain-sync-job \
  --location=$REGION \
  --schedule="0 4 * * *" \
  --uri="https://${REGION}-${PROJECT_ID}.cloudfunctions.net/sync-nextstrain" \
  --http-method=GET \
  --oidc-service-account-email="${PROJECT_ID}@appspot.gserviceaccount.com"

# Flight routes - Every 6 hours
gcloud scheduler jobs create http flight-routes-job \
  --location=$REGION \
  --schedule="0 */6 * * *" \
  --uri="https://${REGION}-${PROJECT_ID}.cloudfunctions.net/fetch-flight-routes" \
  --http-method=GET \
  --oidc-service-account-email="${PROJECT_ID}@appspot.gserviceaccount.com"

# Risk score refresh - Hourly
gcloud scheduler jobs create http risk-engine-job \
  --location=$REGION \
  --schedule="0 * * * *" \
  --uri="$API_URL/api/internal/refresh-risk-scores" \
  --http-method=POST \
  --oidc-service-account-email="${PROJECT_ID}@appspot.gserviceaccount.com"

# List all scheduled jobs
gcloud scheduler jobs list --location=$REGION
```

---

## 9. CDN & Security Setup

### 9.1 Enable Cloud CDN

```bash
# Create a load balancer with Cloud CDN for the API
gcloud compute backend-services create viral-weather-backend \
  --global \
  --enable-cdn \
  --cache-mode=CACHE_ALL_STATIC

# Create URL map
gcloud compute url-maps create viral-weather-lb \
  --default-service=viral-weather-backend

# Enable Cloud CDN on Cloud Run (using NEG)
gcloud compute network-endpoint-groups create viral-weather-api-neg \
  --region=$REGION \
  --network-endpoint-type=serverless \
  --cloud-run-service=viral-weather-api

# Add NEG to backend
gcloud compute backend-services add-backend viral-weather-backend \
  --global \
  --network-endpoint-group=viral-weather-api-neg \
  --network-endpoint-group-region=$REGION
```

### 9.2 Configure Cloud Armor (WAF)

```bash
# Create security policy
gcloud compute security-policies create viral-weather-waf \
  --description="WAF for Viral Weather"

# Add rate limiting rule (100 requests/minute per IP)
gcloud compute security-policies rules create 1000 \
  --security-policy=viral-weather-waf \
  --expression="true" \
  --action=rate-based-ban \
  --rate-limit-threshold-count=100 \
  --rate-limit-threshold-interval-sec=60 \
  --ban-duration-sec=300 \
  --conform-action=allow \
  --exceed-action=deny-429 \
  --enforce-on-key=IP

# Block common attack patterns
gcloud compute security-policies rules create 2000 \
  --security-policy=viral-weather-waf \
  --expression="evaluatePreconfiguredExpr('xss-v33-canary')" \
  --action=deny-403

gcloud compute security-policies rules create 2001 \
  --security-policy=viral-weather-waf \
  --expression="evaluatePreconfiguredExpr('sqli-v33-canary')" \
  --action=deny-403

# Apply policy to backend
gcloud compute backend-services update viral-weather-backend \
  --global \
  --security-policy=viral-weather-waf
```

### 9.3 Configure CORS

Add to your FastAPI application:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://viralweather.app",  # Production domain
        "http://localhost:3000",      # Local development
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
```

---

## 10. Monitoring & Alerting

### 10.1 Create Monitoring Dashboard

```bash
# Create dashboard using gcloud (or use Console UI)
cat > dashboard.json << 'EOF'
{
  "displayName": "Viral Weather Monitoring",
  "mosaicLayout": {
    "columns": 12,
    "tiles": [
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "API Request Count",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_count\""
                }
              }
            }]
          }
        }
      },
      {
        "xPos": 6,
        "width": 6,
        "height": 4,
        "widget": {
          "title": "API Latency (p95)",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_latencies\""
                }
              }
            }]
          }
        }
      }
    ]
  }
}
EOF

gcloud monitoring dashboards create --config-from-file=dashboard.json
```

### 10.2 Create Alert Policies

```bash
# High error rate alert
gcloud alpha monitoring policies create \
  --display-name="High API Error Rate" \
  --condition-display-name="Error rate > 5%" \
  --condition-filter='resource.type="cloud_run_revision" AND metric.type="run.googleapis.com/request_count" AND metric.labels.response_code_class="5xx"' \
  --condition-threshold-value=0.05 \
  --condition-threshold-comparison=COMPARISON_GT \
  --condition-threshold-duration=300s \
  --notification-channels="YOUR_NOTIFICATION_CHANNEL_ID"

# Database connection alert
gcloud alpha monitoring policies create \
  --display-name="Database Connection Issues" \
  --condition-display-name="Connection failures" \
  --condition-filter='resource.type="cloudsql_database" AND metric.type="cloudsql.googleapis.com/database/network/connections"' \
  --condition-threshold-value=0 \
  --condition-threshold-comparison=COMPARISON_LT \
  --condition-threshold-duration=60s \
  --notification-channels="YOUR_NOTIFICATION_CHANNEL_ID"
```

### 10.3 Create Log-Based Metrics

```bash
# Track data ingestion events
gcloud logging metrics create ingestion_events \
  --description="Count of data ingestion events by source" \
  --log-filter='resource.type="cloud_function" AND jsonPayload.event_type="ingestion"'

# Track data freshness warnings
gcloud logging metrics create stale_data_warnings \
  --description="Count of stale data warnings" \
  --log-filter='severity>=WARNING AND jsonPayload.warning_type="stale_data"'
```

---

## 11. Custom Domain (Optional)

### 11.1 Map Custom Domain to Cloud Run

```bash
# Verify domain ownership
gcloud domains verify viralweather.app

# Map domain to frontend service
gcloud run domain-mappings create \
  --service=viral-weather-frontend \
  --domain=viralweather.app \
  --region=$REGION

# Map API subdomain
gcloud run domain-mappings create \
  --service=viral-weather-api \
  --domain=api.viralweather.app \
  --region=$REGION

# Get DNS records to configure
gcloud run domain-mappings describe \
  --domain=viralweather.app \
  --region=$REGION
```

### 11.2 Configure DNS

Add these records at your DNS provider:

| Type | Host | Value | TTL |
|------|------|-------|-----|
| A | @ | (provided by GCP) | 300 |
| AAAA | @ | (provided by GCP) | 300 |
| CNAME | www | ghs.googlehosted.com | 300 |
| CNAME | api | ghs.googlehosted.com | 300 |

---

## 12. Go-Live Checklist

### Pre-Launch Verification

```bash
# Run these checks before going live:

# 1. Verify database connectivity
gcloud sql connect viral-weather-db --user=viralweather --database=viral_weather

# 2. Test API endpoints
curl -s "$API_URL/api/health" | jq .
curl -s "$API_URL/api/locations" | jq '.[:2]'

# 3. Verify scheduler jobs are active
gcloud scheduler jobs list --location=$REGION

# 4. Check secret access
gcloud secrets versions access latest --secret=aviationstack-api-key

# 5. Verify Redis connectivity (from Cloud Run logs)
gcloud run services logs read viral-weather-api --limit=50 --region=$REGION

# 6. Run a manual data ingestion test
gcloud scheduler jobs run wastewater-cdc-job --location=$REGION

# 7. Verify data was ingested
curl -s "$API_URL/api/locations" | jq 'length'
```

### Go-Live Checklist

| Step | Task | Status |
|------|------|--------|
| 1 | GCP project created and billing enabled | ☐ |
| 2 | All required APIs enabled | ☐ |
| 3 | VPC network and connectors created | ☐ |
| 4 | Cloud SQL instance running with PostGIS | ☐ |
| 5 | Database schema deployed | ☐ |
| 6 | Location seed data loaded | ☐ |
| 7 | Redis instance running | ☐ |
| 8 | All secrets stored in Secret Manager | ☐ |
| 9 | API deployed to Cloud Run | ☐ |
| 10 | Frontend deployed to Cloud Run | ☐ |
| 11 | Cloud Functions deployed | ☐ |
| 12 | Cloud Scheduler jobs created | ☐ |
| 13 | Initial data ingestion completed | ☐ |
| 14 | Cloud Armor WAF configured | ☐ |
| 15 | Monitoring dashboard created | ☐ |
| 16 | Alert policies configured | ☐ |
| 17 | Custom domain mapped (optional) | ☐ |
| 18 | SSL certificates provisioned | ☐ |
| 19 | End-to-end testing completed | ☐ |
| 20 | Performance testing completed | ☐ |

### Estimated Monthly Costs

| Component | Aggressive | Standard |
|-----------|-----------|----------|
| Cloud SQL | $10 | $80 |
| Memorystore Redis | $35 | $35 |
| Cloud Run (2 services) | $20 | $50 |
| Cloud Functions | $5 | $10 |
| Cloud Storage | $1 | $2 |
| Cloud CDN | $5 | $10 |
| Networking | $10 | $20 |
| AviationStack API | $49 | $49 |
| Monitoring/Logging | $5 | $10 |
| **Total** | **~$140/mo** | **~$266/mo** |

---

## Troubleshooting

### Common Issues

**1. Cloud SQL connection timeout**
```bash
# Verify private IP is configured
gcloud sql instances describe viral-weather-db --format="value(ipAddresses)"

# Check VPC connector status
gcloud compute networks vpc-access connectors describe viral-weather-connector --region=$REGION
```

**2. Cloud Run can't access secrets**
```bash
# Grant Cloud Run service account access to secrets
gcloud secrets add-iam-policy-binding db-password \
  --member="serviceAccount:${PROJECT_ID}@appspot.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

**3. Scheduler jobs failing**
```bash
# Check scheduler job logs
gcloud logging read "resource.type=cloud_scheduler_job" --limit=10

# Verify service account has invoker permission
gcloud run services add-iam-policy-binding viral-weather-api \
  --region=$REGION \
  --member="serviceAccount:${PROJECT_ID}@appspot.gserviceaccount.com" \
  --role="roles/run.invoker"
```

**4. PostGIS extension not available**
```bash
# PostGIS is pre-installed in Cloud SQL PostgreSQL
# Just run: CREATE EXTENSION postgis;
# If error, check database version supports it
```

---

## Next Steps

After completing this deployment:

1. **Implement the application code** following the architecture in `docs/ARCHITECTURE.md`
2. **Build data adapters** for each source in `docs/DATA_SOURCES.md`
3. **Set up CI/CD** with Cloud Build for automated deployments
4. **Configure staging environment** for testing before production
5. **Implement monitoring SLOs** based on requirements

For questions or issues, refer to:
- [GCP Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud SQL for PostgreSQL](https://cloud.google.com/sql/docs/postgres)
- [AviationStack API Docs](https://aviationstack.com/documentation)
- [CDC NWSS Data Documentation](https://data.cdc.gov/Public-Health-Surveillance/NWSS-Public-SARS-CoV-2-Wastewater-Metric-Data/g653-rqe2)
