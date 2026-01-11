#!/bin/bash
#
# Viral Surveillance - Cloud Functions Deployment Script
#
# This script packages and deploys the Cloud Functions with all dependencies.
#
# Usage:
#   ./deploy.sh                    # Deploy all functions
#   ./deploy.sh ingest_all_sources # Deploy specific function
#   ./deploy.sh --dry-run          # Show what would be deployed
#

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-viral-weather-prod}"
REGION="${GCP_REGION:-us-central1}"
RUNTIME="python311"
MEMORY="512MB"
TIMEOUT="540s"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOY_DIR="$PROJECT_ROOT/.deploy"

echo -e "${GREEN}=== Viral Surveillance Cloud Functions Deployment ===${NC}"
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Parse arguments
DRY_RUN=false
FUNCTION_NAME=""

for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            ;;
        *)
            FUNCTION_NAME="$arg"
            ;;
    esac
done

# Create deployment package
echo -e "${YELLOW}Creating deployment package...${NC}"

# Clean and create deploy directory
rm -rf "$DEPLOY_DIR"
mkdir -p "$DEPLOY_DIR"

# Copy functions
cp "$PROJECT_ROOT/functions/main.py" "$DEPLOY_DIR/"
cp "$PROJECT_ROOT/functions/requirements.txt" "$DEPLOY_DIR/"

# Copy adapters
mkdir -p "$DEPLOY_DIR/adapters"
cp "$PROJECT_ROOT/data-ingestion/adapters/"*.py "$DEPLOY_DIR/adapters/"

# Copy persistence layer
cp "$PROJECT_ROOT/data-ingestion/persistence.py" "$DEPLOY_DIR/"
cp "$PROJECT_ROOT/data-ingestion/ingest.py" "$DEPLOY_DIR/"

# Update imports in main.py to use local paths instead of /workspace
sed -i.bak "s|sys.path.insert(0, '/workspace/data-ingestion')|# Local imports (packaged with deployment)|g" "$DEPLOY_DIR/main.py"
sed -i.bak "s|from adapters\.|from adapters.|g" "$DEPLOY_DIR/main.py"
sed -i.bak "s|from persistence import|from persistence import|g" "$DEPLOY_DIR/main.py"
rm -f "$DEPLOY_DIR/main.py.bak"

# Create __init__.py for adapters package
touch "$DEPLOY_DIR/adapters/__init__.py"

# Copy the full adapters __init__.py
cp "$PROJECT_ROOT/data-ingestion/adapters/__init__.py" "$DEPLOY_DIR/adapters/"

echo -e "${GREEN}Deployment package created at: $DEPLOY_DIR${NC}"
echo ""
echo "Contents:"
ls -la "$DEPLOY_DIR"
echo ""
echo "Adapters:"
ls -la "$DEPLOY_DIR/adapters/"
echo ""

# List of functions to deploy
FUNCTIONS=(
    "ingest_cdc_nwss"
    "ingest_european_sources"
    "ingest_apac_sources"
    "ingest_flight_data"
    "ingest_genomic_data"
    "calculate_risk_scores"
    "data_quality_check"
    "ingest_all_sources"
)

if [ "$DRY_RUN" = true ]; then
    echo -e "${YELLOW}DRY RUN - Would deploy the following functions:${NC}"
    for fn in "${FUNCTIONS[@]}"; do
        echo "  - $fn"
    done
    echo ""
    echo "To deploy for real, run without --dry-run"
    exit 0
fi

# Deploy function(s)
deploy_function() {
    local fn_name=$1
    echo -e "${YELLOW}Deploying $fn_name...${NC}"

    gcloud functions deploy "$fn_name" \
        --gen2 \
        --runtime "$RUNTIME" \
        --region "$REGION" \
        --source "$DEPLOY_DIR" \
        --entry-point "$fn_name" \
        --trigger-http \
        --memory "$MEMORY" \
        --timeout "$TIMEOUT" \
        --set-env-vars "GCP_PROJECT_ID=$PROJECT_ID"

    echo -e "${GREEN}✓ $fn_name deployed${NC}"
}

if [ -n "$FUNCTION_NAME" ]; then
    # Deploy single function
    deploy_function "$FUNCTION_NAME"
else
    # Deploy all functions
    for fn in "${FUNCTIONS[@]}"; do
        deploy_function "$fn"
    done
fi

echo ""
echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo ""
echo "To trigger ingestion:"
echo "  gcloud functions call ingest_all_sources --region $REGION"
echo ""
echo "To view logs:"
echo "  gcloud functions logs read ingest_all_sources --region $REGION"
echo ""
echo -e "${YELLOW}IMPORTANT: Set DATABASE_URL secret:${NC}"
echo "  gcloud secrets create database-url --data-file=- <<< 'postgresql://user:pass@host:5432/db'"
echo "  gcloud functions deploy ingest_all_sources --update-secrets DATABASE_URL=database-url:latest"
