#!/bin/bash
# Deploy Frontend to Google Cloud Run
# Usage: ./deploy-frontend.sh [PROJECT_ID] [REGION] [API_URL]

set -e

PROJECT_ID="${1:-viral-weather}"
REGION="${2:-us-central1}"
API_URL="${3:-}"
SERVICE_NAME="viral-weather-web"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "=========================================="
echo "Deploying Viral Weather Frontend"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "=========================================="

# Get API URL if not provided
if [ -z "$API_URL" ]; then
  echo "Fetching backend API URL..."
  API_URL=$(gcloud run services describe viral-weather-api \
    --project="${PROJECT_ID}" \
    --region="${REGION}" \
    --format='value(status.url)' 2>/dev/null || echo "")

  if [ -z "$API_URL" ]; then
    echo "Warning: Could not get API URL. Please provide it as argument."
    exit 1
  fi
fi

echo "API URL: ${API_URL}"

# Build the container
echo ""
echo "[1/3] Building container image..."
cd "$(dirname "$0")/../frontend"

# Create production Dockerfile if not exists
cat > Dockerfile.prod << 'EOF'
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy source and build
COPY . .

ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_MAPBOX_TOKEN

ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_MAPBOX_TOKEN=$NEXT_PUBLIC_MAPBOX_TOKEN

RUN npm run build

# Production image
FROM node:20-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

# Copy built app
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
EOF

# Get Mapbox token from Secret Manager
MAPBOX_TOKEN=$(gcloud secrets versions access latest \
  --secret="${PROJECT_ID}-mapbox-token" \
  --project="${PROJECT_ID}" 2>/dev/null || echo "")

gcloud builds submit \
  --project="${PROJECT_ID}" \
  --tag="${IMAGE_NAME}" \
  --timeout=20m \
  --build-arg="NEXT_PUBLIC_API_URL=${API_URL}" \
  --build-arg="NEXT_PUBLIC_MAPBOX_TOKEN=${MAPBOX_TOKEN}" \
  -f Dockerfile.prod \
  .

# Deploy to Cloud Run
echo ""
echo "[2/3] Deploying to Cloud Run..."

gcloud run deploy "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --image="${IMAGE_NAME}" \
  --platform=managed \
  --allow-unauthenticated \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=5 \
  --timeout=30s \
  --concurrency=100

# Get service URL
echo ""
echo "[3/3] Getting service URL..."
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --format='value(status.url)')

echo ""
echo "=========================================="
echo "Frontend Deployment Complete!"
echo "Web URL: ${SERVICE_URL}"
echo ""
echo "The Viral Weather app is now live at:"
echo "  ${SERVICE_URL}"
echo "=========================================="

# Clean up temp Dockerfile
rm -f Dockerfile.prod
