#!/bin/bash
# Setup pgvector extension on PostgreSQL

set -e

RESOURCE_GROUP="PartsTracker"
POSTGRES_SERVER="parts-tracker-django-server"
POSTGRES_DB="parts-tracker-django-database"
POSTGRES_USER="kdezfhzdbd"

echo "Setting up pgvector extension on PostgreSQL..."
echo ""

# Step 1: Enable pgvector at server level
echo "1. Enabling pgvector extension at server level..."
az postgres flexible-server parameter set \
    --resource-group "$RESOURCE_GROUP" \
    --server-name "$POSTGRES_SERVER" \
    --name azure.extensions \
    --value "VECTOR" \
    --output none

echo "   ✓ Extension enabled at server level"
echo ""

# Step 2: Install in database
echo "2. Installing pgvector extension in database..."
echo "   You need to provide the PostgreSQL admin password"
echo ""

POSTGRES_HOST="${POSTGRES_SERVER}.postgres.database.azure.com"

read -sp "PostgreSQL password: " POSTGRES_PASSWORD
echo ""

PGPASSWORD="$POSTGRES_PASSWORD" psql \
    -h "$POSTGRES_HOST" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    -c "CREATE EXTENSION IF NOT EXISTS vector;" \
    && echo "   ✓ pgvector extension installed successfully!" \
    || echo "   ❌ Failed to install extension. Make sure psql is installed and credentials are correct."

echo ""
echo "Done! You can verify by running:"
echo "  psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c '\\dx'"
