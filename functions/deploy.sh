#!/bin/bash
# Deploy Cloud Functions for Viral Weather data ingestion
# Usage: ./deploy.sh [PROJECT_ID] [REGION]

set -e

PROJECT_ID="${1:-viral-weather}"
REGION="${2:-us-central1}"

echo "Deploying Cloud Functions to $PROJECT_ID in $REGION"

# Deploy CDC NWSS ingestion function
gcloud functions deploy ingest-cdc-nwss \
  --gen2 \
  --runtime=python311 \
  --region=$REGION \
  --source=. \
  --entry-point=ingest_cdc_nwss \
  --trigger-http \
  --allow-unauthenticated \
  --memory=512MB \
  --timeout=300s \
  --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID,DATA_BUCKET=${PROJECT_ID}-data,PUBSUB_TOPIC=data-ingestion-events"

# Deploy European sources ingestion function
gcloud functions deploy ingest-european-sources \
  --gen2 \
  --runtime=python311 \
  --region=$REGION \
  --source=. \
  --entry-point=ingest_european_sources \
  --trigger-http \
  --allow-unauthenticated \
  --memory=1GB \
  --timeout=540s \
  --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID,DATA_BUCKET=${PROJECT_ID}-data,PUBSUB_TOPIC=data-ingestion-events"

# Deploy APAC sources ingestion function
gcloud functions deploy ingest-apac-sources \
  --gen2 \
  --runtime=python311 \
  --region=$REGION \
  --source=. \
  --entry-point=ingest_apac_sources \
  --trigger-http \
  --allow-unauthenticated \
  --memory=512MB \
  --timeout=300s \
  --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID,DATA_BUCKET=${PROJECT_ID}-data,PUBSUB_TOPIC=data-ingestion-events"

# Deploy flight data ingestion function
gcloud functions deploy ingest-flight-data \
  --gen2 \
  --runtime=python311 \
  --region=$REGION \
  --source=. \
  --entry-point=ingest_flight_data \
  --trigger-http \
  --allow-unauthenticated \
  --memory=256MB \
  --timeout=120s \
  --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID,DATA_BUCKET=${PROJECT_ID}-data,PUBSUB_TOPIC=data-ingestion-events"

# Deploy risk score calculation function
gcloud functions deploy calculate-risk-scores \
  --gen2 \
  --runtime=python311 \
  --region=$REGION \
  --source=. \
  --entry-point=calculate_risk_scores \
  --trigger-http \
  --allow-unauthenticated \
  --memory=512MB \
  --timeout=180s \
  --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID,DATA_BUCKET=${PROJECT_ID}-data,PUBSUB_TOPIC=data-ingestion-events"

# Deploy data quality check function
gcloud functions deploy data-quality-check \
  --gen2 \
  --runtime=python311 \
  --region=$REGION \
  --source=. \
  --entry-point=data_quality_check \
  --trigger-http \
  --allow-unauthenticated \
  --memory=256MB \
  --timeout=60s \
  --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID,DATA_BUCKET=${PROJECT_ID}-data,PUBSUB_TOPIC=data-ingestion-events"

# Deploy Pub/Sub triggered function for event processing
gcloud functions deploy process-ingestion-event \
  --gen2 \
  --runtime=python311 \
  --region=$REGION \
  --source=. \
  --entry-point=process_ingestion_event \
  --trigger-topic=data-ingestion-events \
  --memory=256MB \
  --timeout=60s \
  --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID"

echo ""
echo "Functions deployed successfully!"
echo ""
echo "Next steps:"
echo "1. Create Cloud Scheduler jobs using scheduler.yaml"
echo "2. Store AviationStack API key in Secret Manager:"
echo "   gcloud secrets create aviationstack-api-key --data-file=- <<< 'YOUR_API_KEY'"
echo "3. Create Pub/Sub topic:"
echo "   gcloud pubsub topics create data-ingestion-events"
echo "4. Create GCS bucket:"
echo "   gsutil mb gs://${PROJECT_ID}-data"
