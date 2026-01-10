#!/bin/bash
# Full Deployment Script for Viral Weather
# Deploys infrastructure, backend, frontend, and functions
# Usage: ./deploy-all.sh [PROJECT_ID] [REGION]

set -e

PROJECT_ID="${1:-viral-weather}"
REGION="${2:-us-central1}"
SCRIPT_DIR="$(dirname "$0")"

echo "╔════════════════════════════════════════════════════════════╗"
echo "║           VIRAL WEATHER - FULL DEPLOYMENT                  ║"
echo "╠════════════════════════════════════════════════════════════╣"
echo "║  Project: ${PROJECT_ID}"
echo "║  Region:  ${REGION}"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Pre-flight checks
echo "Running pre-flight checks..."
echo ""

# Check gcloud
if ! command -v gcloud &> /dev/null; then
  echo "Error: gcloud CLI not found. Please install Google Cloud SDK."
  exit 1
fi

# Check terraform
if ! command -v terraform &> /dev/null; then
  echo "Error: terraform not found. Please install Terraform."
  exit 1
fi

# Check authentication
ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>/dev/null)
if [ -z "$ACCOUNT" ]; then
  echo "Error: Not authenticated with gcloud. Run: gcloud auth login"
  exit 1
fi
echo "  Authenticated as: ${ACCOUNT}"

# Check project
gcloud projects describe "${PROJECT_ID}" &>/dev/null || {
  echo "Error: Project ${PROJECT_ID} not found or no access."
  exit 1
}
echo "  Project exists: ${PROJECT_ID}"
echo ""

# Step 1: Deploy Infrastructure
echo "────────────────────────────────────────────────────────────"
echo "STEP 1: Deploying Infrastructure (Terraform)"
echo "────────────────────────────────────────────────────────────"

cd "${SCRIPT_DIR}/../infrastructure/terraform"

# Initialize Terraform
terraform init -upgrade

# Create terraform.tfvars if not exists
if [ ! -f terraform.tfvars ]; then
  echo "Creating terraform.tfvars..."
  cat > terraform.tfvars << EOF
project_id  = "${PROJECT_ID}"
region      = "${REGION}"
environment = "production"
app_name    = "viral-weather"
db_tier     = "db-f1-micro"
db_name     = "viralweather"
db_user     = "viralweather"
db_password = "$(openssl rand -base64 24)"
EOF
fi

# Plan and apply
terraform plan -out=tfplan
terraform apply tfplan

# Capture outputs
DB_CONNECTION=$(terraform output -raw db_connection_name)
REDIS_HOST=$(terraform output -raw redis_host)
DATA_BUCKET=$(terraform output -raw data_bucket)

echo ""
echo "Infrastructure deployed!"
echo "  Database: ${DB_CONNECTION}"
echo "  Redis: ${REDIS_HOST}"
echo "  Data Bucket: ${DATA_BUCKET}"
echo ""

# Step 2: Initialize Database
echo "────────────────────────────────────────────────────────────"
echo "STEP 2: Initializing Database Schema"
echo "────────────────────────────────────────────────────────────"

# This would typically use Cloud SQL proxy or run a migration job
echo "Database schema will be initialized on first backend deployment."
echo ""

# Step 3: Deploy Backend
echo "────────────────────────────────────────────────────────────"
echo "STEP 3: Deploying Backend API"
echo "────────────────────────────────────────────────────────────"

cd "${SCRIPT_DIR}"
chmod +x deploy-backend.sh
./deploy-backend.sh "${PROJECT_ID}" "${REGION}"

API_URL=$(gcloud run services describe viral-weather-api \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --format='value(status.url)')

echo ""
echo "Backend deployed at: ${API_URL}"
echo ""

# Step 4: Deploy Cloud Functions
echo "────────────────────────────────────────────────────────────"
echo "STEP 4: Deploying Cloud Functions (Data Ingestion)"
echo "────────────────────────────────────────────────────────────"

cd "${SCRIPT_DIR}/../functions"
chmod +x deploy.sh
./deploy.sh "${PROJECT_ID}" "${REGION}"

echo ""

# Step 5: Deploy Frontend
echo "────────────────────────────────────────────────────────────"
echo "STEP 5: Deploying Frontend"
echo "────────────────────────────────────────────────────────────"

cd "${SCRIPT_DIR}"
chmod +x deploy-frontend.sh
./deploy-frontend.sh "${PROJECT_ID}" "${REGION}" "${API_URL}"

WEB_URL=$(gcloud run services describe viral-weather-web \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --format='value(status.url)')

echo ""

# Step 6: Setup Cloud Scheduler
echo "────────────────────────────────────────────────────────────"
echo "STEP 6: Configuring Cloud Scheduler Jobs"
echo "────────────────────────────────────────────────────────────"

# Get function URLs
FUNCTION_BASE="https://${REGION}-${PROJECT_ID}.cloudfunctions.net"

# Create scheduler jobs
gcloud scheduler jobs create http ingest-cdc-nwss \
  --project="${PROJECT_ID}" \
  --location="${REGION}" \
  --schedule="0 6 * * 2,4" \
  --time-zone="UTC" \
  --uri="${FUNCTION_BASE}/ingest-cdc-nwss" \
  --http-method=POST \
  --attempt-deadline="300s" 2>/dev/null || echo "Job exists"

gcloud scheduler jobs create http ingest-european \
  --project="${PROJECT_ID}" \
  --location="${REGION}" \
  --schedule="0 8 * * 1,3,5" \
  --time-zone="UTC" \
  --uri="${FUNCTION_BASE}/ingest-european-sources" \
  --http-method=POST \
  --attempt-deadline="600s" 2>/dev/null || echo "Job exists"

gcloud scheduler jobs create http ingest-apac \
  --project="${PROJECT_ID}" \
  --location="${REGION}" \
  --schedule="0 2 * * 2,5" \
  --time-zone="UTC" \
  --uri="${FUNCTION_BASE}/ingest-apac-sources" \
  --http-method=POST \
  --attempt-deadline="300s" 2>/dev/null || echo "Job exists"

gcloud scheduler jobs create http ingest-flights \
  --project="${PROJECT_ID}" \
  --location="${REGION}" \
  --schedule="0 */6 * * *" \
  --time-zone="UTC" \
  --uri="${FUNCTION_BASE}/ingest-flight-data" \
  --http-method=POST \
  --attempt-deadline="120s" 2>/dev/null || echo "Job exists"

gcloud scheduler jobs create http calculate-risk \
  --project="${PROJECT_ID}" \
  --location="${REGION}" \
  --schedule="0 * * * *" \
  --time-zone="UTC" \
  --uri="${FUNCTION_BASE}/calculate-risk-scores" \
  --http-method=POST \
  --attempt-deadline="180s" 2>/dev/null || echo "Job exists"

echo "Scheduler jobs configured."
echo ""

# Done!
echo "╔════════════════════════════════════════════════════════════╗"
echo "║               DEPLOYMENT COMPLETE!                         ║"
echo "╠════════════════════════════════════════════════════════════╣"
echo "║                                                            ║"
echo "║  Web Application:                                          ║"
echo "║    ${WEB_URL}"
echo "║                                                            ║"
echo "║  API Endpoint:                                             ║"
echo "║    ${API_URL}"
echo "║                                                            ║"
echo "║  Next Steps:                                               ║"
echo "║  1. Add Mapbox token to Secret Manager                     ║"
echo "║  2. Add AviationStack API key to Secret Manager            ║"
echo "║  3. Trigger initial data ingestion                         ║"
echo "║                                                            ║"
echo "╚════════════════════════════════════════════════════════════╝"
