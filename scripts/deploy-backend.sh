#!/bin/bash
# Deploy Backend to Google Cloud Run
# Usage: ./deploy-backend.sh [PROJECT_ID] [REGION]

set -e

PROJECT_ID="${1:-viral-weather}"
REGION="${2:-us-central1}"
SERVICE_NAME="viral-weather-api"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "=========================================="
echo "Deploying Viral Weather Backend"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "=========================================="

# Build the container
echo ""
echo "[1/4] Building container image..."
cd "$(dirname "$0")/../backend"

gcloud builds submit \
  --project="${PROJECT_ID}" \
  --tag="${IMAGE_NAME}" \
  --timeout=15m \
  .

# Get infrastructure outputs
echo ""
echo "[2/4] Fetching infrastructure configuration..."
cd "../infrastructure/terraform"

DB_CONNECTION=$(terraform output -raw db_connection_name 2>/dev/null || echo "")
REDIS_HOST=$(terraform output -raw redis_host 2>/dev/null || echo "")
VPC_CONNECTOR=$(terraform output -raw vpc_connector 2>/dev/null || echo "")
SERVICE_ACCOUNT=$(terraform output -raw cloud_run_sa_email 2>/dev/null || echo "")

if [ -z "$DB_CONNECTION" ]; then
  echo "Warning: Could not get Terraform outputs. Using defaults."
  DB_CONNECTION="${PROJECT_ID}:${REGION}:viral-weather-db"
  REDIS_HOST="10.0.0.1"
  VPC_CONNECTOR="viral-weather-connector"
fi

# Deploy to Cloud Run
echo ""
echo "[3/4] Deploying to Cloud Run..."

gcloud run deploy "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --image="${IMAGE_NAME}" \
  --platform=managed \
  --allow-unauthenticated \
  --memory=1Gi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=10 \
  --timeout=60s \
  --concurrency=80 \
  --vpc-connector="${VPC_CONNECTOR}" \
  --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID}" \
  --set-env-vars="ENVIRONMENT=production" \
  --set-env-vars="REDIS_HOST=${REDIS_HOST}" \
  --set-env-vars="DB_CONNECTION_NAME=${DB_CONNECTION}" \
  --set-secrets="DB_PASSWORD=viral-weather-db-password:latest" \
  --set-secrets="AVIATIONSTACK_API_KEY=viral-weather-aviationstack-key:latest" \
  --service-account="${SERVICE_ACCOUNT}"

# Get service URL
echo ""
echo "[4/4] Getting service URL..."
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --format='value(status.url)')

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "Service URL: ${SERVICE_URL}"
echo ""
echo "Test the API:"
echo "  curl ${SERVICE_URL}/health"
echo "  curl ${SERVICE_URL}/api/locations"
echo "=========================================="
