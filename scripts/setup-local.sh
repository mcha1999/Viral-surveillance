#!/bin/bash
# Local development setup script for Viral Weather

set -e

echo "🦠 Setting up Viral Weather local development environment..."

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "❌ Docker is required but not installed."; exit 1; }
command -v docker-compose >/dev/null 2>&1 || command -v docker compose >/dev/null 2>&1 || { echo "❌ Docker Compose is required but not installed."; exit 1; }

# Create .env files from examples if they don't exist
if [ ! -f backend/.env ]; then
    cp backend/.env.example backend/.env
    echo "📝 Created backend/.env from example"
fi

if [ ! -f frontend/.env.local ]; then
    cp frontend/.env.example frontend/.env.local
    echo "📝 Created frontend/.env.local from example"
fi

# Start infrastructure
echo "🚀 Starting PostgreSQL and Redis..."
docker compose up -d postgres redis

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 5

# Check if database schema was applied
echo "🗄️ Verifying database schema..."
docker compose exec -T postgres psql -U viral_weather_app -d viral_weather -c "SELECT 1 FROM location_nodes LIMIT 1" 2>/dev/null || {
    echo "📊 Applying database schema..."
    docker compose exec -T postgres psql -U viral_weather_app -d viral_weather -f /docker-entrypoint-initdb.d/01-schema.sql
}

echo ""
echo "✅ Local development environment is ready!"
echo ""
echo "Next steps:"
echo "  1. Backend: cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload"
echo "  2. Frontend: cd frontend && npm install && npm run dev"
echo ""
echo "Services:"
echo "  - PostgreSQL: localhost:5432"
echo "  - Redis: localhost:6379"
echo "  - Backend API: http://localhost:8000"
echo "  - Frontend: http://localhost:3000"
echo ""
echo "Don't forget to:"
echo "  - Set your MAPBOX_TOKEN in frontend/.env.local"
echo "  - Set your AVIATIONSTACK_API_KEY in backend/.env (optional for MVP)"
