#!/bin/bash
# Starts PostgreSQL and Redis for local development.
# Reads database credentials from .env file.

set -e

cd "$(dirname "$0")/.."

# Load .env file if it exists
if [ -f .env ]; then
    export $(grep -v '^#' .env | grep -v '^\s*$' | xargs)
fi

# Defaults
POSTGRES_DB="${POSTGRES_DB:-tracker_AMBAC}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres}"

echo -e "\nStarting dev databases..."

# Start postgres with pgvector
if docker ps -q -f name=partstracker-postgres | grep -q .; then
    echo "PostgreSQL already running"
else
    # Remove stopped container if exists
    docker rm partstracker-postgres 2>/dev/null || true
    docker run -d \
        --name partstracker-postgres \
        -p 5432:5432 \
        -e POSTGRES_DB="$POSTGRES_DB" \
        -e POSTGRES_USER="$POSTGRES_USER" \
        -e POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
        -v partstracker_pgdata:/var/lib/postgresql/data \
        ankane/pgvector:v0.5.1
    echo "Started PostgreSQL"
fi

# Start redis
if docker ps -q -f name=partstracker-redis | grep -q .; then
    echo "Redis already running"
else
    docker rm partstracker-redis 2>/dev/null || true
    docker run -d \
        --name partstracker-redis \
        -p 6379:6379 \
        redis:7-alpine
    echo "Started Redis"
fi

# Wait for postgres to be ready
echo "Waiting for PostgreSQL..."
for i in {1..15}; do
    docker exec partstracker-postgres pg_isready -U "$POSTGRES_USER" &>/dev/null && break
    sleep 2
done

# Wait for database to be created
for i in {1..10}; do
    docker exec partstracker-postgres psql -U "$POSTGRES_USER" -lqt 2>/dev/null | grep -q "$POSTGRES_DB" && break
    sleep 1
done

# Create extensions
docker exec partstracker-postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null
docker exec partstracker-postgres psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c 'CREATE EXTENSION IF NOT EXISTS "uuid-ossp";' 2>/dev/null

echo -e "\nReady:"
echo "  PostgreSQL: localhost:5432 (db: $POSTGRES_DB, user: $POSTGRES_USER)"
echo "  Redis:      localhost:6379"
echo -e "\nNext: cd PartsTracker && python manage.py migrate && python manage.py runserver\n"
