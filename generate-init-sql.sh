#!/bin/bash

# Generate init.sql from template using environment variables
# Usage: ./generate-init-sql.sh

set -e

# Set defaults for environment variables if not set
export POSTGRES_DB=${POSTGRES_DB:-"tracker_AMBAC"}
export POSTGRES_READONLY_USER=${POSTGRES_READONLY_USER:-"readonly_user"}
export POSTGRES_READONLY_PASSWORD=${POSTGRES_READONLY_PASSWORD:-"readonly_pw"}

echo "Generating init.sql from template..."
echo "Using database: $POSTGRES_DB"
echo "Using readonly user: $POSTGRES_READONLY_USER"

# Check if template exists
if [ ! -f "init.sql.template" ]; then
    echo "Error: init.sql.template not found!"
    exit 1
fi

# Generate init.sql from template
envsubst < init.sql.template > init.sql

echo "Successfully generated init.sql"
echo ""
echo "Environment variables used:"
echo "  POSTGRES_DB=$POSTGRES_DB"  
echo "  POSTGRES_READONLY_USER=$POSTGRES_READONLY_USER"
echo "  POSTGRES_READONLY_PASSWORD=***"